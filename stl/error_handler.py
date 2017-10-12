# Copyright 2017 Google Inc. All rights reserved.
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

"""Module for handling errors from parsing an STL file."""

import logging

import stl.error_formatter
import stl.lexer_error
import stl.parser_error


# Lexer errors live in the 100s
_UNKNOWN_LEXER_ERROR = stl.lexer_error.LexerError(
    error_name='unknown-lexer-error',
    error_id=100,
    error_msg='There was an unknown lexing/tokenizing error :(',
    token_value=None)
_MISSING_STRING_QUOTE = stl.lexer_error.LexerError(
    error_name='missing-string-quote',
    error_id=101,
    error_msg='Missing " " on string literal.',
    token_value='"')
_UNSUPPORTED_SINGLE_QUOTE = stl.lexer_error.LexerError(
    error_name='unsupported-single-quote',
    error_id=102,
    error_msg='Use double quotes (" ") for string literals.',
    token_value="'")

# To generate new parser errors:
#   1. Create a new STL file that contains the new error
#   2. Run `stl/parser.py your_error.stl`
#   3. The parser will dumb out the symbol stack in the logs
#   4. Take the symbols from the end of the stack that are representative
#          of your error to create a "stack pattern".
#   5. Create a ParserError object, and add it to the list of errors in
#          ParserErrorHandler.GetError

# Low level parse errors live in the 200s
_UNKNOWN_PARSER_ERROR = stl.parser_error.ParserError(
    error_name='unknown-parser-error',
    error_id=200,
    error_msg='There was an unknown parse error :(',
    stack_patterns=None)
_MISSING_SEMICOLON = stl.parser_error.ParserError(
    error_name='missing-semicolon',
    error_id=201,
    error_msg='Missing semicolon.',
    stack_patterns=[
        ['CONST', 'type', 'NAME'],
        ['MODULE', 'NAME'],
        ['TRANSITION', 'NAME', 'params', '=', 'NAME', '(', 'param_values_without_paren', ')'],
        ['NAME', 'ARROW', 'NAME', 'param_values', 'ARROW', 'NAME'],
    ])
_MISSING_CLOSING_CURLY_BRACE = stl.parser_error.ParserError(
    error_name='missing-closing-curly-brace',
    error_id=202,
    error_msg='Missing closing curly brace }.',
    stack_patterns=[
        ['{'],
    ])

# Higer level parse errors live in the 300s
_MISSING_POST_STATES = stl.parser_error.ParserError(
    error_name='missing-post-states',
    error_id=301,
    error_msg=('Transitions require "post_states". If there'
               ' are no explicit post_states use an empty'
               ' list (post_states = []).'),
    stack_patterns=[
        ['TRANSITION', 'NAME', 'params', '{', 'local_vars', 'pre_states', 'events'],
    ])
_MISSING_PRE_STATES = stl.parser_error.ParserError(
    error_name='missing-pre-states',
    error_id=302,
    error_msg=('Transitions require "pre_states", and the'
               ' "pre_states" must be non-empty.'),
    stack_patterns=[
        ['TRANSITION', 'NAME', 'params', '{'],
    ])
_EMPTY_PRE_STATES = stl.parser_error.ParserError(
    error_name='empty-pre-states',
    error_id=303,
    error_msg='Transitions require non-empty "pre_states".',
    stack_patterns=[
        ['TRANSITION', 'NAME', 'params', '{', 'local_vars', 'PRE_STATES', '=', '[']
    ])

# The ordering here is important, since the first matching error is
# the one that will get reported.
_ALL_LEXER_ERRORS = [
    _MISSING_STRING_QUOTE,
    _UNSUPPORTED_SINGLE_QUOTE,
    _UNKNOWN_LEXER_ERROR,
]

# The ordering here is important, since the first matching error is
# the one that will get reported.
_ALL_PARSER_ERRORS = [
    _MISSING_SEMICOLON,
    _MISSING_POST_STATES,
    _MISSING_PRE_STATES,
    _EMPTY_PRE_STATES,
    _MISSING_CLOSING_CURLY_BRACE,
    _UNKNOWN_PARSER_ERROR,
]


def _GetColumn(data, token):
  """Gets the column that |token| starts at within a line in |data|."""
  last_newline = data.rfind('\n', 0, token.lexpos)
  if last_newline < 0:
    last_newline = 0
  column = token.lexpos - last_newline
  return column


def _GetLine(data, token):
  """Gets the line of text that |token| is part of in |data|."""
  start_line_pos = data.rfind('\n', 0, token.lexpos) + 1
  end_line_pos = data.find('\n', start_line_pos)
  return data[start_line_pos:end_line_pos]


def _GetErrorPosition(lexer, token):
  error_start_column = _GetColumn(lexer.lexdata, token) - 1
  error_end_column = error_start_column + len(str(token.value)) - 1
  error_position = stl.error_formatter.ErrorPosition(line=lexer.lineno,
                                                     start=error_start_column,
                                                     end=error_end_column)
  return error_position


class ParserErrorHandler(object):
  """Determines the likely cause of a parse error."""

  def __init__(self, error_formatter):
    """Creates a ParserError instance.

    Args:
      error_formatter: An ErrorFormatter to format the parse errors.
    """
    self._formatter = error_formatter

  def Format(self, error):
    """Formats |error| into a string."""
    return self._formatter.Format(error)



  def GetError(self, filename, parser, lexer):
    """Returns an error string based on the state of |parser| and |lexer|.

    Args:
      filename: The name of the file the error occured in.
      parser: A PLY parser that has reached the p_error() state.
      lexer: The PLY lexer that |parser| used to lex.

    Returns:
      A formatted error string.
    """
    logging.debug('\nSymStack: {}\n'.format(
        '\n'.join(str(s) for s in parser.symstack)))

    parser_error = next(error
                        for error in _ALL_PARSER_ERRORS
                        if error.Matches(parser))

    final_token = parser.symstack[-1]
    error_position = _GetErrorPosition(lexer, final_token)

    error_info = stl.error_formatter.ErrorInfo(
        id=parser_error.error_id,
        filename=filename,
        line=_GetLine(lexer.lexdata, final_token),
        position=error_position,
        message=parser_error.error_msg)

    return self.Format(error_info)


class LexerErrorHandler(object):
  """Determines the likely cause of a lexing error."""

  def __init__(self, error_formatter):
    self._formatter = error_formatter

  def Format(self, error):
    """Formats |error| into a string."""
    return self._formatter.Format(error)

  def GetError(self, filename, token):
    # token.value has the entire remaining un-tokenized input string. Replace
    # it with just the illegal character that caused the lexing issue.
    token.value = token.value[0]

    lexer_error = next(error
                       for error in _ALL_LEXER_ERRORS
                       if error.Matches(token))

    error_info = stl.error_formatter.ErrorInfo(
        id=lexer_error.error_id,
        filename=filename,
        line=_GetLine(token.lexer.lexdata, token),
        position=_GetErrorPosition(token.lexer, token),
        message=lexer_error.error_msg)

    return self.Format(error_info)
