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
import base64
import json
import logging
import random

import stl.message


class Encoding(object):
  """Library class for implementing custom message encodings."""

  __metaclass__ = abc.ABCMeta

  @abc.abstractmethod
  def SerializeToString(self, values, message_type):
    """Serialize values into a string representation."""

  @abc.abstractmethod
  def ParseFromString(self, encoded, message_type):
    """Parse string into a dictionary of values."""


class JsonEncoding(Encoding):
  """Encodes and decodes JSON messages."""

  def SerializeToString(self, values, message_type):
    return json.dumps(values)

  def ParseFromString(self, encoded, message_type):
    return json.loads(encoded)


class ProtobufEncoding(Encoding):
  """Encodes and decodes protobuf messages."""

  def SerializeToString(self, values, message_type):
    pbuf = message_type.external()
    ProtobufEncoding._FillProtobufDict(values, pbuf)
    logging.log(1, 'Filled protobuf: %s: %s', str(self), str(pbuf))
    return pbuf.SerializeToString()

  def ParseFromString(self, encoded, message_type):
    pbuf = message_type.external()
    try:
      read_len = pbuf.MergeFromString(encoded)
    except stl.message.DecodeError:
      logging.exception('Could not decode protobuf.')
      return False
    assert read_len == len(encoded)
    decoded_dict = {}
    ProtobufEncoding._FillValueDict(pbuf, decoded_dict)
    return decoded_dict

  @staticmethod
  def _FillValueDict(pbuf_dict, value_dict):
    for f_desc, v in pbuf_dict.ListFields():
      if f_desc.label == f_desc.LABEL_REPEATED:
        value_dict[f_desc.name] = [
            ProtobufEncoding._GetValueFromProtobuf(f_desc, e) for e in v
        ]
      else:
        value_dict[f_desc.name] = ProtobufEncoding._GetValueFromProtobuf(f_desc,
                                                                         v)

  @staticmethod
  def _GetValueFromProtobuf(desc, pbuf_value):
    if desc.type != desc.TYPE_MESSAGE:
      return pbuf_value
    value_dict = {}
    ProtobufEncoding._FillValueDict(pbuf_value, value_dict)
    return value_dict

  @staticmethod
  def _FillProtobufDict(value_dict, pbuf_dict):
    for k in value_dict:
      if isinstance(value_dict[k], list):
        pbuf_list = getattr(pbuf_dict, k)
        for v in value_dict[k]:
          if isinstance(v, dict):
            ProtobufEncoding._FillProtobufDict(v, pbuf_list.add())
          else:
            pbuf_list.append(v)
      elif isinstance(value_dict[k], dict):
        ProtobufEncoding._FillProtobufDict(value_dict[k], getattr(pbuf_dict, k))
      else:
        setattr(pbuf_dict, k, value_dict[k])


class ProtobufBase64Encoding(Encoding):
  """Wraps protobuf-encoded messages with base64."""

  def __init__(self):
    self._proto_encoding = ProtobufEncoding()

  def SerializeToString(self, values, message_type):
    return base64.b64encode(
        self._proto_encoding.SerializeToString(values, message_type))

  def ParseFromString(self, encoded, message_type):
    return self._proto_encoding.ParseFromString(
        base64.b64decode(encoded), message_type)


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
    self.used_values = set()

  def Validate(self, value):
    valid = value not in self.used_values
    self.used_values.add(value)
    return valid

  def Generate(self):
    value = 'unique-%d' % self.num
    self.num += 1
    while value in self.used_values:
      value = 'unique-%d' % self.num
      self.num += 1
    self.used_values.add(value)
    return value


class UniqueInt(Qualifier):
  """"Qualify integers which are always unique."""

  def __init__(self):
    Qualifier.__init__(self)
    self.num = 0
    self.used_values = set()

  def Validate(self, value):
    valid = value not in self.used_values
    self.used_values.add(value)
    return valid

  def Generate(self):
    value = self.num
    self.num += 1
    while value in self.used_values:
      value = self.num
      self.num += 1
    self.used_values.add(value)
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
