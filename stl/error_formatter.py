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

"""Module for formatting parser/syntax errors."""

import abc
import json
import re


class ErrorFormatter(object):
  """Interface for displaying STL parsing errors."""
  __metaclass__ = abc.ABCMeta

  @abc.abstractmethod
  def Format(self, error):
    """Outputs error_handler.ErrorInfo |error| in a custom format."""
    pass


class JsonErrorFormatter(ErrorFormatter):
  """Format errors as json objects."""

  def Format(self, error):
    """Format |error| as json."""
    return json.dumps(error._asdict())


class Color(object):
  """ANSI escape code base color codes.

  See https://en.wikipedia.org/wiki/ANSI_escape_code#Colors for more info.
  """

  BLACK = 0
  RED = 1
  GREEN = 2
  YELLOW = 3
  BLUE = 4
  MAGENTA = 5
  CYAN = 6
  WHITE = 7
  DEFAULT = 9
  
  @staticmethod
  def _IsBaseColor(color):
    return color in [Color.BLACK,
                     Color.RED,
                     Color.GREEN,
                     Color.YELLOW,
                     Color.BLUE,
                     Color.MAGENTA,
                     Color.CYAN,
                     Color.WHITE,
                     Color.DEFAULT]

  @staticmethod
  def Foreground(color):
    """Converts |color| into its foreground color code."""
    if not Color._IsBaseColor(color):
      raise ValueError('Expected a Color.COLOR constant, found: {}'.format(color))
    return color + 30
  
  @staticmethod
  def Background(color):
    """Converts |color| into its background color code."""
    if not Color._IsBaseColor(color):
      raise ValueError('Expected a Color.COLOR constant, found: {}'.format(color))  
    return color + 40  


class PrettyErrorFormatter(ErrorFormatter):
  """Pretty-ify errors with colors, highlights, and helpful markings."""

  _ERROR_COLOR = Color.RED
  _ANNOTATION_COLOR = Color.YELLOW

  def _Colorize(self,
               text,
               foreground=Color.DEFAULT,
               background=Color.DEFAULT,
               bold=True):
    bold = int(bold)
    fg_color = Color.Foreground(foreground) 
    bg_color = Color.Background(background)
    return '\x1b[{bold};{fg_color};{bg_color}m{text}\x1b[0m'.format(
        text=text, bold=bold, fg_color=fg_color, bg_color=bg_color)

  def _GetMessageLine(self, error):
    """Returns the formatted line with the error message."""
    file_position = '{}:{}:{}'.format(
        error.filename, error.position.line, error.position.start)
    return '{}({}): {}'.format(
        self._Colorize('error', self._ERROR_COLOR),
        self._Colorize(file_position, self._ANNOTATION_COLOR, bold=False),
        error.message)

  def _GetSourceLine(self, error):
    """Returns the formatted line from the source that caused the error."""
    return '{}{}'.format(self._GetLineNumberPrefix(error), error.line)

  def _GetSourceAnnotatinoLine(self, error):
    """Returns a line that highlights the original source."""
    pre_annotation = ' ' * error.position.start
    annotation = '^' * (error.position.end - error.position.start + 1)
    return '{}{}'.format(
        self._GetLineNumberPrefix(error, show_number=False),
        self._Colorize(pre_annotation + annotation, self._ANNOTATION_COLOR))

  def _GetLineNumberPrefix(self, error, show_number=True):
    """Returns a prefix to annotate a line with a line number.

    Args:
      error: The ErrorInfo to get the line number from.
      show_number: Whether to show or hide the number (hiding the number is
          useful to get a prefix with the same width and formatting).
    """
    prefix_with_number = ' {} | '.format(error.position.line)
    if show_number:
      return prefix_with_number
    return re.sub('\d', ' ', prefix_with_number)
  
  def Format(self, error):
    lines = [self._GetMessageLine(error),
             self._GetSourceLine(error),
             self._GetSourceAnnotationLine(error),]
    return '\n'.join(lines)
