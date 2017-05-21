import abc
import json
import re


class ErrorFormatter(object):
  """Interface for displaying STL parsing errors."""
  __metaclass__ = abc.ABCMeta

  @abc.abstractmethod
  def format(self, error):
    """Outputs parser_error.ErrorInfo |error| in a custom format."""
    pass


class JsonErrorFormatter(ErrorFormatter):
  """Format errors as json objects."""

  def format(self, error):
    """Format |error| as json."""
    return json.dumps(error._asdict())


class Color(object):
  """ANSI escape code base color codes.

  For foreground colors, add 30 to the color value.
  For background colors, add 40 to the color value.

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


class PrettyErrorFormatter(ErrorFormatter):
  """Pretty-ify errors with colors, highlights, and helpful markings."""

  ERROR_COLOR = Color.RED
  ANNOTATION_COLOR = Color.YELLOW

  def colorize(self,
               text,
               foreground=Color.DEFAULT,
               background=Color.DEFAULT,
               bold=True):
    bold = int(bold)
    fg_color = foreground + 30
    bg_color = background + 40
    return '\x1b[{bold};{fg_color};{bg_color}m{text}\x1b[0m'.format(
        text=text, bold=bold, fg_color=fg_color, bg_color=bg_color)

  def get_message_line(self, error):
    """Returns the formatted line with the error message."""
    file_position = '{}:{}:{}'.format(
        error.filename, error.position.line, error.position.start)
    return '{}({}): {}'.format(
        self.colorize('error', self.ERROR_COLOR),
        self.colorize(file_position, self.ANNOTATION_COLOR, bold=False),
        error.message)

  def get_source_line(self, error):
    """Returns the formatted line from the source that caused the error."""
    return '{}{}'.format(self.get_line_number_prefix(error), error.line)

  def get_source_annotation_line(self, error):
    """Returns a line that highlights the original source."""
    pre_annotation = ' ' * error.position.start
    annotation = '^' * (error.position.end - error.position.start + 1)
    return '{}{}'.format(
        self.get_line_number_prefix(error, show_number=False),
        self.colorize(pre_annotation + annotation, self.ANNOTATION_COLOR))

  def get_line_number_prefix(self, error, show_number=True):
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


  def format(self, error):
    lines = [self.get_message_line(error),
             self.get_source_line(error),
             self.get_source_annotation_line(error),]
    return '\n'.join(lines)
