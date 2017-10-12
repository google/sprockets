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

"""Module for matching specific errors from the lexer."""


class LexerError(object):
  """Class for describing and matching errors from the lexer."""

  def __init__(self, error_name, error_id, error_msg, token_value):
    """Create a LexerError that matches |token_value|.

    Args:
     error_name: A short, human readable name for the error,
         using lowercase-with-dashes-format.
     error_id: An integer to identify a specific error:
         100s: Lexer errors.
         200s: Low level parsing errors.
         300s: High level parsing errors.
     error_msg: A message to display with this error that describes
         clearly what caused the error.
     token_value: A string to match against the token that the lexer
         failed at (or None to match against every token).

    Returns:
      LexerError that matches against |token_value|.
    """
    self.error_name = error_name
    self.error_id = error_id
    self.error_msg = error_msg
    self._token_value = token_value

  def Matches(self, token):
    return self._token_value is None or token.value == self._token_value
