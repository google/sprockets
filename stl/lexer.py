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

"""Lexing (tokenizing) a state transition (STL) spec."""


import logging

import ply.lex


class StlSyntaxError(SyntaxError):
  """Error for incorrect STL syntax."""


class StlLexer(object):

  def __init__(self, filename=None, **kwargs):
    """Create a Lex lexer.

    To pass this into a Ply Yacc parser, pass it in using the .lexer propert
    of an StlLexer instance:
      my_lexer = StlLexer()
      my_parser = ply.yacc.parser(lexer=my_lexer.lexer)

    Args:
      filename: The filename string to use in any error messaging.
      kwargs: Forwarded to ply.lex.lex.
    """
    self._filename = filename
    self.lexer = ply.lex.lex(module=self, **kwargs)

  RESERVED = {
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

  # |literals| is a special field for ply.lex. Each of these
  # characters is interpreted as a separate token
  literals = ':;{}()[]=,.&'

  # |tokens| is a special field for ply.lex. This must contain a list
  # of all possible token types.
  tokens = [
      'ARROW',  # ->
      'BOOLEAN',
      'NAME',
      'NULL',
      'NUMBER',
      'STRING_LITERAL',
  ] + list(RESERVED.values())

  # A string containing ignored characters (spaces and tabs)
  t_ignore = ' \t'

  def t_ARROW(self, t):
    r'->'
    return t

  def t_BOOLEAN(self, t):
    r'(true|false)'
    t.value = (t.value == 'true')
    return t

  def t_NULL(self, t):
    r'null'
    t.value = None
    return t

  def t_NAME(self, t):
    r'[a-zA-Z_]\w*'
    t.type = self.RESERVED.get(t.value, 'NAME')
    return t

  def t_NUMBER(self, t):
    r'-?\d+'
    t.value = int(t.value)
    return t

  def t_STRING_LITERAL(self, t):
    r'"([^\\"]|\\"|\\\\)*"'
    t.value = t.value[1:-1].replace('\\"', '"').replace('\\\\', '\\')
    return t

  def t_COMMENT(self, t):
    r'//.*'
    del t  # unused argument

  # Define a rule so we can track line numbers.
  def t_newline(self, t):
    r'\n+'
    t.lexer.lineno += len(t.value)

  # Error handling rule.
  def t_error(self, t):
    logging.error('[%s:%d] Illegal character: %s',
                  self._filename,
                  t.lexer.lineno,
                  t.value[0])
    t.lexer.skip(1)

  def debug(self):
    """Print out all the tokens from the lexer|."""
    for token in self.lexer.tokens():
      print token
