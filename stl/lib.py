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

"""Defines STL public library class."""

import abc
import random


class Event(object):
  """Library class for implementing external events.

  An event is used to define an interaction between two roles in a system.
  Roles can send and receive messages defined by a protocol, and an Event
  defines both the behavior of the sender and the receiver.
  """

  __metaclass__ = abc.ABCMeta

  @abc.abstractmethod
  def Fire(self, context, *args):
    """Simulate initiating an interaction event.

    This method should initiate an interaction from |context.source| directed to
    |context.target|. Examples include sending a message over a TCP connection
    or invoking an API call.

    Args:
      context: Context of this event.
          context.source: Source role for this event. Use the attributes of
              the source role to initiate the simulated interaction.
          context.target: Target role for this event. Use the attributes of
              the target role to direct the event to the appropriate place.
      *args: Additional arguments required for the event. These arguments are
          passed as an event invocation within the STL.
    Returns:
      True if the event was fired successfully.
    """

  @abc.abstractmethod
  def Wait(self, context, *args):
    """Wait for and validate an interaction event.

    This method should block and wait for a specific interaction. For example,
    this method might wait for a specific message over a TCP connection.

    Args:
      context: Context of this event.
          context.source: Source role for this event. Use the attributes of
              the source role to validate where the event came from.
          context.target: Target role for this event. Use the attributes of
              the target role to validate the event recipient.
      *args: Additional arguments for validating the event. These arguments
          should be used to validate the incoming event.
    Returns:
      True if the event was successfully validated.
    """


class Qualifier(object):
  """Library class for defining external qualifiers.

  A qualifier is used to validate or generate values in a message field. During
  message matching, a qualifier may be used to:

    1. Determine if the value of a field in the message is valid.
    2. Extract the value of a message field into a local variable.

  During message generation, a qualifier may:

    1. Generate a valid value in a message field.
    2. Extract the generated value into a local variable.

  A qualifier must satisfy the following invariant:

    qual.Validate(qual.Generate(*args), *args) == True

  That is, any generated values for a given set of arguments must always be
  valid, no matter how many values have been generated or validated.
  """

  __metaclass__ = abc.ABCMeta

  @abc.abstractmethod
  def Validate(self, value, *args):
    """Validate a value.

    Args:
      value: The value to validate
      *args: External arguments necessary for validation.

    Returns:
      True if the value is valid, False otherwise.
    """

  @abc.abstractmethod
  def Generate(self, *args):
    """Generage a valid value.

    Args:
      *args: External arguments necessary for generation.

    Returns: The generated value.
    """


class AnyOf(Qualifier):
  """Qualify a value matching a set of possible values."""

  def __init__(self):
    Qualifier.__init__(self)

  def Validate(self, value, *args):
    return value in args

  def Generate(self, *args):
    return random.choice(args)


class RandomString(Qualifier):
  """Qualify random strings."""

  def __init__(self):
    Qualifier.__init__(self)

  def Validate(self, value):
    # Any value is acceptable.
    return True

  def Generate(self):
    return 'random-%s' % random.randint(0, 999999)


class UniqueString(Qualifier):
  """"Qualify strings which are always unique."""

  def __init__(self):
    Qualifier.__init__(self)
    self.num = 0
    self.previous = set()

  def Validate(self, value, prev):
    self.previous.add(prev)
    valid = value not in self.previous
    return valid

  def Generate(self, prev):
    self.previous.add(prev)
    value = 'unique-%d' % self.num
    self.num += 1
    while value in self.previous:
      value = 'unique-%d' % self.num
      self.num += 1
    return value


class UniqueInt(Qualifier):
  """"Qualify integers which are always unique."""

  def __init__(self):
    Qualifier.__init__(self)
    self.num = 1
    self.previous = set()

  def Validate(self, value, prev):
    self.previous.add(prev)
    valid = value not in self.previous
    return valid

  def Generate(self, prev):
    self.previous.add(prev)
    value = self.num
    self.num += 1
    while value in self.previous:
      value = self.num
      self.num += 1
    return value


class DifferentFrom(Qualifier):
  """Qualify a string which is different from the previous one."""

  def __init__(self):
    Qualifier.__init__(self)

  def Validate(self, value, prev):
    # This value must not match the previous one.
    return value != prev

  def Generate(self, prev):
    rand = random.randint(0, 999999)
    if 'random-%s' % rand == prev:
      rand += 1
    return 'random-%s' % rand


class RandomBool(Qualifier):
  """Qualify random boolean values."""

  def __init__(self):
    Qualifier.__init__(self)

  def Validate(self, value):
    # Any value is acceptable.
    return True

  def Generate(self):
    return random.choice([True, False])
