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

"""Module for matching specific errors from the parser."""


class ParserError(object):
  """Class for describing and matching errors from the parser."""

  def __init__(self, error_name, error_id, error_msg, stack_patterns):
    """Create a ParserError that matches against any of the |stack_patterns|.

    Args:
     error_name: A short, human readable name for the error,
         using lowercase-with-dashes-format.
     error_id: An integer to identify a specific error:
         100s: Lexer errors.
         200s: Low level parsing errors.
         300s: High level parsing errors.
     error_msg: A message to display with this error that describes
         clearly what caused the error.
     stack_patterns: A list of "stack patterns", where each stack pattern
         is a list of strings corresponding to symbols on the parser's symbol
         stack at the time it errored out. The string values for the symbols
         can match essentially any terminal or non-terminal symbol used in the
         grammar from parser.py.
         Examples: ['TRANSITION', 'NAME', 'params', '=']
         (or None to match against any symbol stack).

    Returns:
      ParserError that matches against |stack_patterns|.
    """
    self.error_name = error_name
    self.error_id = error_id
    self.error_msg = error_msg
    self._stack_patterns = stack_patterns

  def Matches(self, parser):
    if self._stack_patterns is None:
      return True

    return any(self._SymbolStackEndsWith(parser.symstack, stack_pattern)
               for stack_pattern in self._stack_patterns)

  def _SymbolStackEndsWith(self, parser_symbol_stack, stack_pattern):
    """Determines if |stack| matches against |symbol_stack|.

    Args:
      symbol_stack: The symbol stack from parser.symstack left on th parser
          when an error was generarted.
      stack: A list of strings to match against the token 'type' in
          |symbol_stack|. (e.g. ['TRANSITION', 'NAME', 'params', '=']
    """
    parser_symbol_stack_str = ' '.join(s.type for s in parser_symbol_stack)
    stack_pattern_str = ' '.join(stack_pattern)
    return parser_symbol_stack_str.endswith(stack_pattern_str)
