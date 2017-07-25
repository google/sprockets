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
import ply.yacc  # pylint: disable=g-bad-import-order
import pprint
import sys

import stl.base
import stl.error_formatter
import stl.error_handler
import stl.event
import stl.lexer
import stl.message
import stl.module
import stl.qualifier
import stl.state


class StlSyntaxError(SyntaxError):
  """Error for incorrect STL syntax."""


class StlParser(object):
  """A parser for Sprockets STL files."""

  tokens = stl.lexer.StlLexer.tokens

  def __init__(self, filename=None, global_env=None, error_formatter=None):
    """Creates an StlParser with an StlLexer.

    Args:
      filename: The string to use in debug output. The parser does not attempt
          to read from |filename|. To pass data to parse, use StlParser.parse
      global_env: The global environment dict to be updated during parsing.
    """
    self._filename = filename
    self._global_env = global_env
    self._local_env = {'_curr_module': None}
    self.lexer = stl.lexer.StlLexer(self._filename)
    self.parser = ply.yacc.yacc(module=self)
    error_formatter = error_formatter or stl.error_formatter.PrettyErrorFormatter()
    self.error_handler = stl.error_handler.ParserErrorHandler(error_formatter)

  def parse(self, data):
    """Parses the |data| string and returns an updated global_env."""
    self.parser.parse(data, lexer=self.lexer.lexer)
    return self._global_env

  def p_module(self, p):
    """module : module_def defs"""
    del p  # unused argument

  def p_module_def(self, p):
    """module_def : MODULE NAME ';' """
    if p[2] in self._global_env['modules']:
      self._local_env['_curr_module'] = self._global_env['modules'][p[2]]
    else:
      self._local_env['_curr_module'] = stl.module.Module(p[2])
      self._global_env['modules'][p[2]] = self._local_env['_curr_module']

  def p_defs(self, p):
    """defs : defs def
            | def"""
    del p  # unused argument

  def p_def(self, p):
    """def : const_def
           | role_def
           | state_def
           | message_def
           | qualifier_def
           | event_def
           | transition_def"""
    del p  # unused argument

  def p_const_def(self, p):
    """const_def : CONST type NAME ';'
                 | CONST type NAME '=' value ';' """
    if self._local_env['_curr_module'].HasDefinition(p[3]):
      logging.error('[%s:%d] Duplicated const: %s', self._filename,
                    p.lineno(3), p[3])
      return
    # TODO(byungchul): Type checking
    if len(p) == 5:
      self._local_env['_curr_module'].consts[p[3]] = stl.base.Const(p[3], p[2])
    else:
      self._local_env['_curr_module'].consts[p[3]] = stl.base.Const(
          p[3], p[2], p[5])

  def p_role_def(self, p):
    """role_def : ROLE NAME '{' '}'
                | ROLE NAME '{' role_fields '}' """
    if self._local_env['_curr_module'].HasDefinition(p[2]):
      logging.error('[%s:%d] Duplicated role: %s', self._filename,
                    p.lineno(2), p[2])
      return
    role = stl.base.Role(p[2])
    if len(p) >= 6:
      for f in p[4]:
        role.fields[f.name] = f
    self._local_env['_curr_module'].roles[role.name] = role

  def p_role_fields(self, p):
    """role_fields : role_fields role_field
                   | role_field"""
    if len(p) == 2:  # first def
      p[0] = [p[1]]
      return
    assert isinstance(p[1], list)
    for f in p[1]:
      if f.name == p[2].name:
        logging.error('[%s:%d] Duplicated field: %s', self._filename,
                      p.lineno(2), p[2])
        return
    p[1].append(p[2])
    p[0] = p[1]

  def p_role_field(self, p):
    """role_field : type NAME ';' """
    p[0] = stl.base.Field(p[2], p[1])
    p.set_lineno(0, p.lineno(2))

  def p_state_def(self, p):
    """state_def : STATE NAME params '{' names '}'
                 | STATE NAME params '{' names ',' '}' """
    if self._local_env['_curr_module'].HasDefinition(p[2]):
      logging.error('[%s:%d] Duplicated state: %s', self._filename,
                    p.lineno(2), p[2])
      return
    state_ = stl.state.State(p[2])
    state_.params = p[3]
    state_.values = p[5]
    self._local_env['_curr_module'].states[state_.name] = state_

  def p_names(self, p):
    """names : names ',' NAME
             | NAME"""
    if len(p) == 2:  # first state value
      p[0] = [p[1]]
      return
    assert isinstance(p[1], list)
    for n in p[1]:
      if n == p[3]:
        logging.error('[%s:%d] Duplicated state value: %s', self._filename,
                      p.lineno(3), p[3])
        return
    p[1].append(p[3])
    p[0] = p[1]

  def p_message_def(self, p):
    """message_def : message_or_array NAME '{' encode_decl message_body_or_external '}'"""  # pylint: disable=line-too-long
    if self._local_env['_curr_module'].HasDefinition(p[2]):
      logging.error('[%s:%d] Duplicated message: %s', self._filename,
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
        self._global_env['error'] = True
        raise e
    self._local_env['_curr_module'].messages[msg.name] = msg

  def p_message_or_array(self, p):
    """message_or_array : MESSAGE
                        | MESSAGE '[' ']' """
    p[0] = (len(p) == 4)  # True if it's a message array.

  def p_encode_decl(self, p):
    """encode_decl : ENCODE STRING_LITERAL ';' """
    p[0] = p[2]

  def p_message_body_or_external(self, p):
    """message_body_or_external : message_body
                                | EXTERNAL STRING_LITERAL ';' """
    if len(p) == 2:  # message_body
      p[0] = p[1]
    else:  # EXTERNAL STRING_LITERAL ';'
      p[0] = p[2]

  def p_message_body(self, p):
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
          logging.error('[%s:%d] Duplicated field: %s', self._filename,
                        p.lineno(index), p[index].name)
          return
      p[0][0].append(p[index])
    else:
      if p[index].name in p[0][1]:
        logging.error('[%s:%d] Duplicated message: %s', self._filename,
                      p.lineno(index), p[index].name)
        return
      p[0][1][p[index].name] = p[index]

  def p_message_field(self, p):
    """message_field : field_rule type NAME ';'
                     | field_rule type NAME ':' field_property_list ';' """
    p[0] = stl.base.Field(p[3], p[2], p[1] == 'optional', p[1] == 'repeated')
    if len(p) == 7:
      p[0].encoding_props = p[5]
    p.set_lineno(0, p.lineno(3))

  def p_field_rule(self, p):
    """field_rule : REQUIRED
                  | OPTIONAL
                  | REPEATED"""
    p[0] = p[1]

  def p_field_property_list(self, p):
    """field_property_list : field_property_list ',' field_property
                           | field_property """
    if len(p) == 2:  # first key-value pair
      key, val = p[1]
      p[0] = {key: val}
      return
    assert isinstance(p[1], dict)
    key, val = p[3]
    if key in p[1]:
      logging.error('[%s:%d] Duplicated key: %s', self._filename,
                    p.lineno(3), key)
      return
    p[1][key] = val
    p[0] = p[1]

  def p_field_property(self, p):
    """field_property : STRING_LITERAL '=' constant """
    p[0] = (p[1], p[3].value)

  def p_sub_message(self, p):
    """sub_message : MESSAGE NAME '{' message_body '}' """
    msg = stl.message.Message(p[2], None, False)
    msg.fields, msg.messages = p[4]
    p[0] = msg
    p.set_lineno(0, p.lineno(2))

  def p_qualifier_def(self, p):
    """qualifier_def : QUALIFIER type NAME params '=' EXTERNAL STRING_LITERAL ';'"""  # pylint: disable=line-too-long
    try:
      qual = stl.qualifier.QualifierFromExternal(p[3], p[2], p[7])
    except Exception as e:
      logging.exception('Could not import qualifier: %s', p[7])
      self._global_env['error'] = True
      raise e
    qual.params = p[4]
    self._local_env['_curr_module'].qualifiers[qual.name] = qual

  def p_event_def(self, p):
    """event_def : EVENT NAME params ';'
                 | EVENT NAME params '=' EXTERNAL STRING_LITERAL ';'
                 | EVENT NAME params '=' NAME param_values ';' """
    if len(p) == 8 and stl.base.IsString(p[6]):
      #NAME params = EXTERNAL STRING_LITERAL;
      try:
        evt = stl.event.EventFromExternal(p[2], p[6])
      except Exception as e:
        logging.exception('Could not import event: %s', p[6])
        self._global_env['error'] = True
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
    self._local_env['_curr_module'].events[evt.name] = evt

  def p_transition_def(self, p):
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
    self._local_env['_curr_module'].transitions[trans.name] = trans

  def p_transition_body(self, p):
    """transition_body : local_vars pre_states events post_states error_states"""  # pylint: disable=line-too-long
    p[0] = (p[1], p[2], p[3], p[4], p[5])

  def p_local_vars(self, p):
    """local_vars : local_vars local_var
                  | empty"""
    if len(p) == 2:  # empty
      p[0] = []
      return
    assert isinstance(p[1], list)
    for f in p[1]:
      if f.name == p[2].name:
        logging.error('[%s:%d] Duplicated local var: %s', self._filename,
                      p.lineno(2), p[2].name)
    p[1].append(p[2])
    p[0] = p[1]

  def p_local_var(self, p):
    """local_var : type NAME ';' """
    p[0] = stl.base.LocalVar(p[2], p[1])

  def p_pre_states(self, p):
    """pre_states : PRE_STATES '=' '[' pre_state_values ']' """
    p[0] = p[4]

  def p_post_states(self, p):
    """post_states : POST_STATES '=' '[' state_values ']'
                   | POST_STATES '=' '[' ']' """
    if len(p) == 6:
      p[0] = p[4]
    else:
      p[0] = []

  def p_error_states(self, p):
    """error_states : ERROR_STATES '=' '[' state_values ']'
                    | ERROR_STATES '=' '[' ']'
                    | empty"""
    if len(p) == 6:
      p[0] = p[4]
    else:
      p[0] = []

  def p_pre_state_values(self, p):
    """pre_state_values : pre_state_values ',' pre_state_value
                        | pre_state_value"""
    if len(p) == 2:  # first state_value
      p[0] = [p[1]]
      return
    assert isinstance(p[1], list)
    for s in p[1]:
      if str(s) == str(p[3]):
        logging.error('[%s:%d] Duplicated state: %s', self._filename,
                      p.lineno(3), p[3])
        return
    p[1].append(p[3])
    p[0] = p[1]

  def p_pre_state_value(self, p):
    """pre_state_value : NAME param_values '.' pre_state_value_options"""
    assert isinstance(p[4], list)
    p[0] = [stl.state.StateValueInTransition(p[1], s) for s in p[4]]
    for s in p[0]:
      s.param_values = p[2]

  def p_pre_state_value_options(self, p):
    """pre_state_value_options : NAME
                               | '{' names '}' """
    if len(p) == 2:  # Only a single pre_state value
      p[0] = [p[1]]
      return
    assert isinstance(p[2], list)
    p[0] = p[2]

  def p_state_values(self, p):
    """state_values : state_values ',' state_value
                    | state_value"""
    if len(p) == 2:  # first state_value
      p[0] = [p[1]]
      return
    assert isinstance(p[1], list)
    for s in p[1]:
      if str(s) == str(p[3]):
        logging.error('[%s:%d] Duplicated state: %s', self._filename,
                      p.lineno(3), p[3])
        return
    p[1].append(p[3])
    p[0] = p[1]

  def p_state_value(self, p):
    """state_value : NAME param_values '.' NAME"""
    p[0] = stl.state.StateValueInTransition(p[1], p[4])
    p[0].param_values = p[2]

  def p_events(self, p):
    """events : EVENTS '{' role_events '}' """
    p[0] = p[3]

  def p_role_events(self, p):
    """role_events : role_events role_event
                   | role_event"""
    if len(p) == 2:  # first role_event
      p[0] = [p[1]]
      return
    assert isinstance(p[1], list)
    p[1].append(p[2])
    p[0] = p[1]

  def p_role_event(self, p):
    """role_event : NAME ARROW NAME param_values ARROW NAME ';' """
    p[0] = stl.event.EventInTransition(p[3], p[1], p[6])
    p[0].param_values = p[4]

  def p_params(self, p):
    """params : empty
              | '(' ')'
              | '(' params_without_paren ')' """
    if len(p) == 4:
      p[0] = p[2]
    else:
      p[0] = []

  def p_params_without_paren(self, p):
    """params_without_paren : params_without_paren ',' param
                            | param"""
    if len(p) == 2:  # first param
      p[0] = [p[1]]
      return
    assert isinstance(p[1], list)
    for f in p[1]:
      if f.name == p[3].name:
        logging.error('[%s:%d] Duplicated param: %s', self._filename,
                      p.lineno(3), p[3])
        return
    p[1].append(p[3])
    p[0] = p[1]

  def p_param(self, p):
    """param : type_or_role NAME
             | type_or_role '&' NAME"""
    if len(p) == 3:
      p[0] = stl.base.Param(p[2], p[1])
    else:
      p[0] = stl.base.Param(p[3], p[1])  # TODO(byungchul): Handle out param (&)

  def p_param_values(self, p):
    """param_values : empty
                    | '(' ')'
                    | '(' param_values_without_paren ')' """
    if len(p) == 4:
      p[0] = p[2]
    else:
      p[0] = []

  def p_param_values_without_paren(self, p):
    """param_values_without_paren : param_values_without_paren ',' param_value
                                  | param_value"""
    if len(p) == 2:  # first param_value
      p[0] = [p[1]]
      return
    assert isinstance(p[1], list)
    p[1].append(p[3])
    p[0] = p[1]

  def p_param_value(self, p):
    """param_value : value
                   | message_value
                   | message_array"""

    p[0] = p[1]

  def p_value(self, p):
    """value : constant
             | reference_maybe_with_ampersand"""
    p[0] = p[1]

  def p_constant(self, p):
    """constant : BOOLEAN
                | NULL
                | NUMBER
                | STRING_LITERAL"""
    p[0] = stl.base.Value(p[1])

  def p_reference_maybe_with_ampersand(self, p):
    """reference_maybe_with_ampersand : reference
                                      | '&' reference"""
    if len(p) == 2:
      p[0] = stl.base.Value('$' + p[1])  # FuncGetField()
    else:
      p[0] = stl.base.Value('&' + p[2])  # FuncSet

  def p_reference(self, p):
    """reference : NAME
                 | reference '.' NAME"""
    # TODO(byungchul): Support other module's names.
    #TODO(byungchul) : Build FuncGetField or FuncSet here.
    if len(p) == 2:
      p[0] = p[1]
    else:
      p[0] = p[1] + '.' + p[3]

  def p_message_array(self, p):
    """message_array : NAME array """
    assert isinstance(p[2].value, list)
    p[0] = stl.base.Expand(p[1])
    p[0].values = [p[2]]

  def p_message_value(self, p):
    """message_value : NAME '{' field_values '}' """
    p[0] = stl.base.Expand(p[1])
    p[0].values = p[3]

  def p_field_values(self, p):
    """field_values : field_values field_value
                    | empty"""
    if len(p) == 2:  # empty
      p[0] = []
      return
    assert isinstance(p[1], list)
    for f in p[1]:
      if f.name == p[2].name:
        logging.error('[%s:%d] Cannot set field again: %s', self._filename,
                      p.lineno(2), p[2].name)
    p[1].append(p[2])
    p[0] = p[1]

  def p_field_value(self, p):
    """field_value : NAME '=' rvalue"""
    assert isinstance(p[3], stl.base.Value)
    p[0] = p[3]
    p[0].name = p[1]
    p.set_lineno(0, p.lineno(1))

  def p_rvalue(self, p):
    """rvalue : value ';'
              | qualifier_value ';'
              | array ';'
              | struct ';'
              | message_array_value ';'
              | array
              | struct
              | message_array_value"""
    p[0] = p[1]

  def p_array(self, p):
    """array : '[' ']'
             | '[' array_elements ']'
             | '[' array_elements ',' ']' """
    if len(p) == 3:
      p[0] = stl.base.Value([])
    else:
      p[0] = stl.base.Value(p[2])

  def p_array_elements(self, p):
    """array_elements : array_elements ',' array_element
                      | array_element"""
    if len(p) == 2:  # first element
      p[0] = [p[1]]
      return
    assert isinstance(p[1], list)
    p[1].append(p[3])
    p[0] = p[1]

  def p_array_element(self, p):
    """array_element : value
                     | array
                     | struct"""
    p[0] = p[1]

  def p_struct(self, p):
    """struct : '{' field_values '}' """
    p[0] = stl.base.Value(p[2])

  def p_message_array_value(self, p):
    """message_array_value : message_array
                           | message_value"""
    p[0] = stl.base.Value(p[1])

  def p_qualifier_value(self, p):
    """qualifier_value : NAME param_values ARROW reference
                       | NAME param_values"""
    qual = self._local_env['_curr_module'].qualifiers[p[1]]
    assert qual
    if len(p) == 5:
      p[0] = stl.base.QualifierValue(qual, p[2], stl.base.Value('&' + p[4]))
    else:
      p[0] = stl.base.QualifierValue(qual, p[2])

  def p_type(self, p):
    """type : BOOL
            | INT
            | NAME
            | STRING"""
    p[0] = p[1]

  def p_type_or_role(self, p):
    """type_or_role : type
                    | ROLE"""
    p[0] = p[1]

  def p_empty(self, p):
    """empty : """
    p[0] = None

  def p_error(self, p):
    self._global_env['error'] = True
    if p is None:
      raise StlSyntaxError(
          '[{}] Syntax error: '
          'Reached end of file unexpectantly.'.format(self._filename))

    print self.error_handler.get_error(
        self._filename, self.parser, self.lexer.lexer)

    raise StlSyntaxError('[{}:{}] Syntax error at: {}'.format(
        self._filename, p.lexer.lineno, p.value))


def Parse(filename, global_env):
  """Parse a state transition spec of |filename| and fill |module_dict|.

  Args:
    filename: A state transition spec file.
    global_env: Dictionary to store global STL state. It has one field:
      global_env['modules']: Dictionary of stl.module.Module by name.
  """
  parser = StlParser(filename=filename, global_env=global_env)
  with open(filename) as data:
    return parser.parse(data.read())


def main():
  logging.basicConfig(level=logging.DEBUG)
  filename = sys.argv[1]
  global_env = {'modules': {}}
  pprint.pprint(Parse(filename, global_env), indent=2)


if __name__ == '__main__':
  main()
