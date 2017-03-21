#!/usr/bin/env python
# Copyright 2016 Google Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Parsing a state transition spec."""

# pylint: disable=g-doc-args
# pylint: disable=g-docstring-missing-newline
# pylint: disable=g-docstring-quotes
# pylint: disable=g-no-space-after-docstring-summary
# pylint: disable=g-short-docstring-punctuation
# pylint: disable=g-short-docstring-space
# pylint: disable=invalid-name
# pylint: disable=unused-variable

import logging
import ply.lex  # pylint: disable=g-bad-import-order
import ply.yacc  # pylint: disable=g-bad-import-order
import pprint
import sys

import stl.base
import stl.event
import stl.message
import stl.module
import stl.qualifier
import stl.state


class StlSyntaxError(SyntaxError):
  """Error for incorrect STL syntax."""


###################################################
# Lexer

reserved = {
    'bool': 'BOOL',
    'const': 'CONST',
    'encode': 'ENCODE',
    'error_states': 'ERROR_STATES',
    'event': 'EVENT',
    'events': 'EVENTS',
    'external': 'EXTERNAL',
    'int': 'INT',
    'message': 'MESSAGE',
    'module': 'MODULE',
    'optional': 'OPTIONAL',
    'post_states': 'POST_STATES',
    'pre_states': 'PRE_STATES',
    'qualifier': 'QUALIFIER',
    'repeated': 'REPEATED',
    'required': 'REQUIRED',
    'role': 'ROLE',
    'state': 'STATE',
    'string': 'STRING',
    'transition': 'TRANSITION',
}

literals = ':;{}()[]=,.&'

tokens = [
    'ARROW',  # ->
    'BOOLEAN',
    'NAME',
    'NULL',
    'NUMBER',
    'STRING_LITERAL',
] + list(reserved.values())


def _GetLexer(filename):
  """Returns a lexer for STL."""

  t_ARROW = r'->'

  def t_BOOLEAN(t):
    r'(true|false)'
    t.value = (t.value == 'true')
    return t

  def t_NULL(t):
    r'null'
    t.value = None
    return t

  def t_NAME(t):
    r'[a-zA-Z_]\w*'
    t.type = reserved.get(t.value, 'NAME')  # reserved?
    return t

  def t_NUMBER(t):
    r'-?\d+'
    t.value = int(t.value)
    return t

  def t_STRING_LITERAL(t):
    r'"([^\\"]|\\"|\\\\)*"'
    t.value = t.value[1:-1].replace('\\"', '"').replace('\\\\', '\\')
    return t

  def t_COMMENT(t):
    r'//.*'
    del t  # unused argument

  # Define a rule so we can track line numbers
  def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

  # A string containing ignored characters (spaces and tabs)
  t_ignore = ' \t'

  # Error handling rule
  def t_error(t):
    logging.error('[%s:%d] Illegal character: %s', filename, t.lexer.lineno,
                  t.value[0])
    t.lexer.skip(1)

  return ply.lex.lex()


def _DebugLexer(lexer, data):
  lexer.input(data)
  tok = lexer.token()
  while tok:
    logging.debug(tok)
    tok = lexer.token()


###################################################
# Parser


def _GetParser(filename, global_env):
  """Return a parser for STL."""
  local_env = {'_curr_module': None}

  def p_module(p):
    """module : module_def defs"""
    del p  # unused argument

  def p_module_def(p):
    """module_def : MODULE NAME ';' """
    if p[2] in global_env['modules']:
      local_env['_curr_module'] = global_env['modules'][p[2]]
    else:
      local_env['_curr_module'] = stl.module.Module(p[2])
      global_env['modules'][p[2]] = local_env['_curr_module']

  def p_defs(p):
    """defs : defs def
            | def"""
    del p  # unused argument

  def p_def(p):
    """def : const_def
           | role_def
           | state_def
           | message_def
           | qualifier_def
           | event_def
           | transition_def"""
    del p  # unused argument

  def p_const_def(p):
    """const_def : CONST type NAME ';'
                 | CONST type NAME '=' value ';' """
    if local_env['_curr_module'].HasDefinition(p[3]):
      logging.error('[%s:%d] Duplicated const: %s', filename, p.lineno(3), p[3])
      return
    # TODO(byungchul): Type checking
    if len(p) == 5:
      local_env['_curr_module'].consts[p[3]] = stl.base.Const(p[3], p[2])
    else:
      local_env['_curr_module'].consts[p[3]] = stl.base.Const(p[3], p[2], p[5])

  def p_role_def(p):
    """role_def : ROLE NAME '{' '}'
                | ROLE NAME '{' role_fields '}' """
    if local_env['_curr_module'].HasDefinition(p[2]):
      logging.error('[%s:%d] Duplicated role: %s', filename, p.lineno(2), p[2])
      return
    role = stl.base.Role(p[2])
    if len(p) >= 6:
      for f in p[4]:
        role.fields[f.name] = f
    local_env['_curr_module'].roles[role.name] = role

  def p_role_fields(p):
    """role_fields : role_fields role_field
                   | role_field"""
    if len(p) == 2:  # first def
      p[0] = [p[1]]
      return
    assert isinstance(p[1], list)
    for f in p[1]:
      if f.name == p[2].name:
        logging.error('[%s:%d] Duplicated field: %s', filename,
                      p.lineno(2), p[2])
        return
    p[1].append(p[2])
    p[0] = p[1]

  def p_role_field(p):
    """role_field : type NAME ';' """
    p[0] = stl.base.Field(p[2], p[1])
    p.set_lineno(0, p.lineno(2))

  def p_state_def(p):
    """state_def : STATE NAME params '{' names '}'
                 | STATE NAME params '{' names ',' '}' """
    if local_env['_curr_module'].HasDefinition(p[2]):
      logging.error('[%s:%d] Duplicated state: %s', filename, p.lineno(2), p[2])
      return
    state_ = stl.state.State(p[2])
    state_.params = p[3]
    state_.values = p[5]
    local_env['_curr_module'].states[state_.name] = state_

  def p_names(p):
    """names : names ',' NAME
             | NAME"""
    if len(p) == 2:  # first state value
      p[0] = [p[1]]
      return
    assert isinstance(p[1], list)
    for n in p[1]:
      if n == p[3]:
        logging.error('[%s:%d] Duplicated state value: %s', filename,
                      p.lineno(3), p[3])
        return
    p[1].append(p[3])
    p[0] = p[1]

  def p_message_def(p):
    """message_def : message_or_array NAME '{' encode_decl message_body_or_external '}'"""  # pylint: disable=line-too-long
    if local_env['_curr_module'].HasDefinition(p[2]):
      logging.error('[%s:%d] Duplicated message: %s', filename,
                    p.lineno(2), p[2])
      return
    encode_name = p[4]
    if isinstance(p[5], tuple):  # message_body
      msg = stl.message.Message(p[2], encode_name, p[1])
      msg.fields, msg.messages = p[5]
    else:  # EXTERNAL STRING_LITERAL ';'
      try:
        msg = stl.message.MessageFromExternal(p[2], encode_name, p[1], p[5])
      except Exception as e:
        logging.exception('Could not import message: %s', p[5])
        global_env['error'] = True
        raise e
    local_env['_curr_module'].messages[msg.name] = msg

  def p_message_or_array(p):
    """message_or_array : MESSAGE
                        | MESSAGE '[' ']' """
    p[0] = (len(p) == 4)  # True if it's a message array.

  def p_encode_decl(p):
    """encode_decl : ENCODE STRING_LITERAL ';' """
    p[0] = p[2]

  def p_message_body_or_external(p):
    """message_body_or_external : message_body
                                | EXTERNAL STRING_LITERAL ';' """
    if len(p) == 2:  # message_body
      p[0] = p[1]
    else:  # EXTERNAL STRING_LITERAL ';'
      p[0] = p[2]

  def p_message_body(p):
    """message_body : message_body message_field
                    | message_body sub_message
                    | message_field
                    | sub_message"""
    if len(p) == 2:
      p[0] = ([], {})
      index = 1
    else:
      p[0] = p[1]
      index = 2
    if isinstance(p[index], stl.base.Field):
      for f in p[0][0]:
        if f.name == p[index].name:
          logging.error('[%s:%d] Duplicated field: %s', filename,
                        p.lineno(index), p[index].name)
          return
      p[0][0].append(p[index])
    else:
      if p[index].name in p[0][1]:
        logging.error('[%s:%d] Duplicated message: %s', filename,
                      p.lineno(index), p[index].name)
        return
      p[0][1][p[index].name] = p[index]

  def p_message_field(p):
    """message_field : field_rule type NAME ';'
                     | field_rule type NAME ':' field_property_list ';' """
    p[0] = stl.base.Field(p[3], p[2], p[1] == 'optional', p[1] == 'repeated')
    if len(p) == 7:
      p[0].encoding_props = p[5]
    p.set_lineno(0, p.lineno(3))

  def p_field_rule(p):
    """field_rule : REQUIRED
                  | OPTIONAL
                  | REPEATED"""
    p[0] = p[1]

  def p_field_property_list(p):
    """field_property_list : field_property_list ',' field_property
                           | field_property """
    if len(p) == 2:  # first key-value pair
      key, val = p[1]
      p[0] = {key: val}
      return
    assert isinstance(p[1], dict)
    key, val = p[3]
    if key in p[1]:
      logging.error('[%s:%d] Duplicated key: %s', filename, p.lineno(3), key)
      return
    p[1][key] = val
    p[0] = p[1]

  def p_field_property(p):
    """field_property : STRING_LITERAL '=' constant """
    p[0] = (p[1], p[3].value)

  def p_sub_message(p):
    """sub_message : MESSAGE NAME '{' message_body '}' """
    msg = stl.message.Message(p[2], None, False)
    msg.fields, msg.messages = p[4]
    p[0] = msg
    p.set_lineno(0, p.lineno(2))

  def p_qualifier_def(p):
    """qualifier_def : QUALIFIER type NAME params '=' EXTERNAL STRING_LITERAL ';'"""  # pylint: disable=line-too-long
    try:
      qual = stl.qualifier.QualifierFromExternal(p[3], p[2], p[7])
    except Exception as e:
      logging.exception('Could not import qualifier: %s', p[7])
      global_env['error'] = True
      raise e
    qual.params = p[4]
    local_env['_curr_module'].qualifiers[qual.name] = qual

  def p_event_def(p):
    """event_def : EVENT NAME params ';'
                 | EVENT NAME params '=' EXTERNAL STRING_LITERAL ';'
                 | EVENT NAME params '=' NAME param_values ';' """
    if len(p) == 8 and stl.base.IsString(p[6]):
      # NAME params = EXTERNAL STRING_LITERAL ;
      try:
        evt = stl.event.EventFromExternal(p[2], p[6])
      except Exception as e:
        logging.exception('Could not import event: %s', p[6])
        global_env['error'] = True
        raise e
    elif len(p) == 8 and isinstance(p[6], list):
      # NAME params = NAME param_values ;
      evt = stl.event.Event(p[2])
      evt.expand = stl.base.Expand(p[5])
      evt.expand.values = p[6]
    else:
      # NAME params ;
      assert len(p) == 5
      evt = stl.event.Event(p[2])

    evt.params = p[3]
    local_env['_curr_module'].events[evt.name] = evt

  def p_transition_def(p):
    """transition_def : TRANSITION NAME params '{' transition_body '}'
                      | TRANSITION NAME params '=' NAME param_values ';' """
    trans = stl.state.Transition(p[2])
    trans.params = p[3]
    if len(p) == 8:  # expand
      trans.expand = stl.base.Expand(p[5])
      trans.expand.values = p[6]
    else:
      (trans.local_vars, trans.pre_states, trans.events, trans.post_states,
       trans.error_states) = p[5]
    local_env['_curr_module'].transitions[trans.name] = trans

  def p_transition_body(p):
    """transition_body : local_vars pre_states events post_states error_states"""  # pylint: disable=line-too-long
    p[0] = (p[1], p[2], p[3], p[4], p[5])

  def p_local_vars(p):
    """local_vars : local_vars local_var
                  | empty"""
    if len(p) == 2:  # empty
      p[0] = []
      return
    assert isinstance(p[1], list)
    for f in p[1]:
      if f.name == p[2].name:
        logging.error('[%s:%d] Duplicated local var: %s', filename,
                      p.lineno(2), p[2].name)
    p[1].append(p[2])
    p[0] = p[1]

  def p_local_var(p):
    """local_var : type NAME ';' """
    p[0] = stl.base.LocalVar(p[2], p[1])

  def p_pre_states(p):
    """pre_states : PRE_STATES '=' '[' pre_state_values ']' """
    p[0] = p[4]

  def p_post_states(p):
    """post_states : POST_STATES '=' '[' state_values ']'
                   | POST_STATES '=' '[' ']' """
    if len(p) == 6:
      p[0] = p[4]
    else:
      p[0] = []

  def p_error_states(p):
    """error_states : ERROR_STATES '=' '[' state_values ']'
                    | ERROR_STATES '=' '[' ']'
                    | empty"""
    if len(p) == 6:
      p[0] = p[4]
    else:
      p[0] = []

  def p_pre_state_values(p):
    """pre_state_values : pre_state_values ',' pre_state_value
                        | pre_state_value"""
    if len(p) == 2:  # first state_value
      p[0] = [p[1]]
      return
    assert isinstance(p[1], list)
    for s in p[1]:
      if str(s) == str(p[3]):
        logging.error('[%s:%d] Duplicated state: %s', filename,
                      p.lineno(3), p[3])
        return
    p[1].append(p[3])
    p[0] = p[1]

  def p_pre_state_value(p):
    """pre_state_value : NAME param_values '.' pre_state_value_options"""
    assert isinstance(p[4], list)
    p[0] = [stl.state.StateValueInTransition(p[1], s) for s in p[4]]
    for s in p[0]:
      s.param_values = p[2]

  def p_pre_state_value_options(p):
    """pre_state_value_options : NAME
                               | '{' names '}' """
    if len(p) == 2:  # Only a single pre_state value
      p[0] = [p[1]]
      return
    assert isinstance(p[2], list)
    p[0] = p[2]

  def p_state_values(p):
    """state_values : state_values ',' state_value
                    | state_value"""
    if len(p) == 2:  # first state_value
      p[0] = [p[1]]
      return
    assert isinstance(p[1], list)
    for s in p[1]:
      if str(s) == str(p[3]):
        logging.error('[%s:%d] Duplicated state: %s', filename,
                      p.lineno(3), p[3])
        return
    p[1].append(p[3])
    p[0] = p[1]

  def p_state_value(p):
    """state_value : NAME param_values '.' NAME"""
    p[0] = stl.state.StateValueInTransition(p[1], p[4])
    p[0].param_values = p[2]

  def p_events(p):
    """events : EVENTS '{' role_events '}' """
    p[0] = p[3]

  def p_role_events(p):
    """role_events : role_events role_event
                   | role_event"""
    if len(p) == 2:  # first role_event
      p[0] = [p[1]]
      return
    assert isinstance(p[1], list)
    p[1].append(p[2])
    p[0] = p[1]

  def p_role_event(p):
    """role_event : NAME ARROW NAME param_values ARROW NAME ';' """
    p[0] = stl.event.EventInTransition(p[3], p[1], p[6])
    p[0].param_values = p[4]

  def p_params(p):
    """params : empty
              | '(' ')'
              | '(' params_without_paren ')' """
    if len(p) == 4:
      p[0] = p[2]
    else:
      p[0] = []

  def p_params_without_paren(p):
    """params_without_paren : params_without_paren ',' param
                            | param"""
    if len(p) == 2:  # first param
      p[0] = [p[1]]
      return
    assert isinstance(p[1], list)
    for f in p[1]:
      if f.name == p[3].name:
        logging.error('[%s:%d] Duplicated param: %s', filename,
                      p.lineno(3), p[3])
        return
    p[1].append(p[3])
    p[0] = p[1]

  def p_param(p):
    """param : type_or_role NAME
             | type_or_role '&' NAME"""
    if len(p) == 3:
      p[0] = stl.base.Param(p[2], p[1])
    else:
      p[0] = stl.base.Param(p[3], p[1])  # TODO(byungchul): Handle out param (&)

  def p_param_values(p):
    """param_values : empty
                    | '(' ')'
                    | '(' param_values_without_paren ')' """
    if len(p) == 4:
      p[0] = p[2]
    else:
      p[0] = []

  def p_param_values_without_paren(p):
    """param_values_without_paren : param_values_without_paren ',' param_value
                                  | param_value"""
    if len(p) == 2:  # first param_value
      p[0] = [p[1]]
      return
    assert isinstance(p[1], list)
    p[1].append(p[3])
    p[0] = p[1]

  def p_param_value(p):
    """param_value : value
                   | message_value
                   | message_array"""

    p[0] = p[1]

  def p_value(p):
    """value : constant
             | reference_maybe_with_ampersand"""
    p[0] = p[1]

  def p_constant(p):
    """constant : BOOLEAN
                | NULL
                | NUMBER
                | STRING_LITERAL"""
    p[0] = stl.base.Value(p[1])

  def p_reference_maybe_with_ampersand(p):
    """reference_maybe_with_ampersand : reference
                                      | '&' reference"""
    if len(p) == 2:
      p[0] = stl.base.Value('$' + p[1])  # FuncGetField()
    else:
      p[0] = stl.base.Value('&' + p[2])  # FuncSet

  def p_reference(p):
    """reference : NAME
                 | reference '.' NAME"""
    # TODO(byungchul): Support other module's names.
    # TODO(byungchul): Build FuncGetField or FuncSet here.
    if len(p) == 2:
      p[0] = p[1]
    else:
      p[0] = p[1] + '.' + p[3]

  def p_message_array(p):
    """message_array : NAME array """
    assert isinstance(p[2].value, list)
    p[0] = stl.base.Expand(p[1])
    p[0].values = [p[2]]

  def p_message_value(p):
    """message_value : NAME '{' field_values '}' """
    p[0] = stl.base.Expand(p[1])
    p[0].values = p[3]

  def p_field_values(p):
    """field_values : field_values field_value
                    | empty"""
    if len(p) == 2:  # empty
      p[0] = []
      return
    assert isinstance(p[1], list)
    for f in p[1]:
      if f.name == p[2].name:
        logging.error('[%s:%d] Cannot set field again: %s', filename,
                      p.lineno(2), p[2].name)
    p[1].append(p[2])
    p[0] = p[1]

  def p_field_value(p):
    """field_value : NAME '=' rvalue"""
    assert isinstance(p[3], stl.base.Value)
    p[0] = p[3]
    p[0].name = p[1]
    p.set_lineno(0, p.lineno(1))

  def p_rvalue(p):
    """rvalue : value ';'
              | qualifier_value ';'
              | array ';'
              | struct ';'
              | message_array_value ';'
              | array
              | struct
              | message_array_value"""
    p[0] = p[1]

  def p_array(p):
    """array : '[' ']'
             | '[' array_elements ']'
             | '[' array_elements ',' ']' """
    if len(p) == 3:
      p[0] = stl.base.Value([])
    else:
      p[0] = stl.base.Value(p[2])

  def p_array_elements(p):
    """array_elements : array_elements ',' array_element
                      | array_element"""
    if len(p) == 2:  # first element
      p[0] = [p[1]]
      return
    assert isinstance(p[1], list)
    p[1].append(p[3])
    p[0] = p[1]

  def p_array_element(p):
    """array_element : value
                     | array
                     | struct"""
    p[0] = p[1]

  def p_struct(p):
    """struct : '{' field_values '}' """
    p[0] = stl.base.Value(p[2])

  def p_message_array_value(p):
    """message_array_value : message_array
                           | message_value"""
    p[0] = stl.base.Value(p[1])

  def p_qualifier_value(p):
    """qualifier_value : NAME param_values ARROW reference
                       | NAME param_values"""
    qual = local_env['_curr_module'].qualifiers[p[1]]
    assert qual
    if len(p) == 5:
      p[0] = stl.base.QualifierValue(qual, p[2], stl.base.Value('&' + p[4]))
    else:
      p[0] = stl.base.QualifierValue(qual, p[2])

  def p_type(p):
    """type : BOOL
            | INT
            | NAME
            | STRING"""
    p[0] = p[1]

  def p_type_or_role(p):
    """type_or_role : type
                    | ROLE"""
    p[0] = p[1]

  def p_empty(p):
    """empty : """
    p[0] = None

  def p_error(p):
    global_env['error'] = True
    if p is None:
      raise StlSyntaxError(
          '[{}] Syntax error: '
          'Reached end of file unexpectantly.'.format(filename))
    else:
      raise StlSyntaxError('[{}:{}] Syntax error at: {}'.format(
          filename, p.lexer.lineno, p.value))

  return ply.yacc.yacc()


def Parse(filename, global_env):
  """Parse a state transition spec of |filename| and fill |module_dict|.

  Args:
    filename: A state transition spec file.
    global_env: Dictionary to store global STL state. It has one field:
      global_env['modules']: Dictionary of stl.module.Module by name.
  """
  data = open(filename).read()
  lexer = _GetLexer(filename)
  parser = _GetParser(filename, global_env)

  parser.parse(data, lexer=lexer)


def _DebugParser(stl_filename):
  global_env = {'modules': {}}
  Parse(stl_filename, global_env)
  return global_env


def main():
  logging.basicConfig(level=logging.DEBUG)
  filename = sys.argv[1] if len(sys.argv) == 2 else 'model2/cast_v2.stl'
  pprint.pprint(_DebugParser(filename), indent=2)


if __name__ == '__main__':
  main()
