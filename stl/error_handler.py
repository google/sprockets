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

"""Module for handling errors from parsing an STL file."""

import collections


ErrorInfo = collections.namedtuple('ErrorInfo', ['id', 'filename', 'line', 'position', 'message'])
# Args:
#   id: An identifier for the type of error.
#   filename: Name of the file the error occured in.
#   line: The text of the line the error occured in.
#   position: An ErrorPosition pointing to where the error occured.
#   messasge: The human readable message explaining the error

ErrorPosition = collections.namedtuple('ErrorPosiion', ['line', 'start', 'end'])
# Args:
#   line: The line number of the error.
#   start: The position (column) the error starts at in the line (inclusive).
#   end: The position (column) the error ends at in the line (inclusive).


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

  def _GetColumn(self, data, token):
    """Gets the column that |token| starts at within a line in |data|."""
    last_newline = data.rfind('\n', 0, token.lexpos)
    if last_newline < 0:
      last_newline = 0
    column = token.lexpos - last_newline
    return column

  def _GetLine(self, data, token):
    """Gets the line of text that |token| is part of in |data|."""
    start_line_pos = data.rfind('\n', 0, token.lexpos) + 1
    end_line_pos = data.find('\n', start_line_pos)
    return data[start_line_pos:end_line_pos]


  def GetError(self, filename, parser, lexer):
    """Returns an error string based on the state of |parser| and |lexer".

    Args:
      filename: The name of the file the error occured in.
      parser: A PLY parser that has reached the p_error() state.
      lexer: The PLY lexer that |parser| used to lex.

    Returns:
      A formatted error string.
    """
    print 'SymStack: {}'.format(parser.symstack)
    final_token = parser.symstack[-1]
    error_start_column = self._GetColumn(lexer.lexdata, final_token) - 1
    error_end_column = error_start_column + len(final_token.value) - 1
    error_position = ErrorPosition(line=lexer.lineno,
                                   start=error_start_column,
                                   end=error_end_column)
    error = ErrorInfo(
        id=0,
        filename=filename,
        line=self._GetLine(lexer.lexdata, final_token),
        position=error_position,
        message='There was a parsing error :(')
    return self.format(error)
