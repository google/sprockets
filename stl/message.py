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

"""Defines protocol specifications and messages."""

import importlib
import logging
from google.protobuf import message
from google.protobuf import reflection

import stl.base  # pylint: disable=g-bad-import-order
import stl.lib  # pylint: disable=g-bad-import-order


class Message(stl.base.NamedObject):
  """Protocol specifications.

  A protocol specification is defined with "message" or "message[]" keywords.
  It allows nested messages. For example,

  message mProtocolExample {
    encode "json";

    required string field1;
    optional integer field2;
    repeated mNestedMessage field3;

    message mNestedMessage {
      optional string fieldInNestedMessage;
    }
  }

  Attributes:
    encode_name: Name for the encoding to use for this message (e.g. "json").
    encoding: An stl.lib.Encoding object which will be used to serialize and
      deserialize MessageValues.
    is_array: Whether this message is an array.
    fields: List of fields (stl.base.Field) defined in this protocol or message.
    messages: Map of nested messages and their name.
  """

  def __init__(self, name, encode_name, is_array):
    stl.base.NamedObject.__init__(self, name)
    self.encode_name = encode_name
    # Encode name might not be provided if this is a sub-message.
    if self.encode_name:
      module, encoding = encode_name.rsplit('.', 1)
      self.encoding = importlib.import_module(module).__getattribute__(
          encoding)()
    self.is_array = is_array
    self.fields = []
    self.messages = {}

  def __eq__(self, other):
    return (stl.base.NamedObject.__eq__(self, other) and
            self.encode_name == other.encode_name and
            self.is_array == other.is_array and self.fields == other.fields and
            self.messages == other.messages)

  def __str__(self):
    if self.is_array:
      pattern = 'MESSAGE(%s)[] %s: f(%s) m(%s)'
    else:
      pattern = 'MESSAGE(%s) %s: f(%s) m(%s)'
    return pattern % (self.encode_name, self.name, stl.base.GetCSV(self.fields),
                      stl.base.GetCSV(self.messages))

  def Resolve(self, env, resolved_fields):
    logging.log(1, 'Resolving ' + self.name)
    msg_value = MessageValue(self.name, self)
    outer_messages = [env['_current_module']['messages']]
    if self.is_array:
      msg_value.value_dict_or_array = self.ValidateArray(resolved_fields,
                                                         outer_messages)
    else:
      msg_value.value_dict_or_array = self.ValidateDict(resolved_fields,
                                                        outer_messages)
    return msg_value

  def ValidateArray(self, array_value, outer_messages):
    return [
        self.ValidateDict(dict_value, outer_messages)
        for dict_value in array_value
    ]

  def ValidateDict(self, dict_value, outer_messages):
    """Validate a dictionary value.

    It checks whether all individual fields of |dict_value| are valid, i.e.
    all required fields exist and the values of fields correspond to their
    types.

    Args:
      dict_value: Dictionary value to validate.
      outer_messages: Messages visible from the scope of |dict_value|.
    Returns:
      Dictionary value validated.
    Raises:
      NameError: If any required fields are missed.
    """
    valid_dict = {}
    for f in self.fields:
      if f.name in dict_value:
        valid_dict[f.name] = self._ValidateField(f, dict_value[f.name],
                                                 outer_messages)
      elif not f.optional:
        raise NameError("Mandatoray field missing in message '%s': %s" %
                        (self.name, f.name))
    return valid_dict

  def _ValidateField(self, field, value, outer_messages):
    """Validate a field of dictionary value according to its type."""
    if field.repeated:  # Array
      if not isinstance(value, list):
        raise ValueError("Value list expected in field '%s' in message '%s'" %
                         (field.name, self.name))
      temp_field = stl.base.Field(field.name,
                                  field.type_)  # clear repeated flag
      return [self._ValidateField(temp_field, e, outer_messages) for e in value]

    if field.type_ == 'bool':
      if (value is None or isinstance(value, bool) or
          (isinstance(value, stl.base.LocalVar) and value.type_ == 'bool') or
          Message._IsValidFunc(value, 'bool')):
        return value
      raise ValueError("Boolean value expected in field '%s' in message '%s'" %
                       (field.name, self.name))

    if field.type_ == 'int':
      if (value is None or isinstance(value, int) or
          (isinstance(value, stl.base.LocalVar) and value.type_ == 'int') or
          Message._IsValidFunc(value, 'int')):
        return value
      raise ValueError("Integer value expected in field '%s' in message '%s'" %
                       (field.name, self.name))

    if field.type_ == 'string':
      if (value is None or stl.base.IsString(value) or
          (isinstance(value, stl.base.LocalVar) and value.type_ == 'string') or
          Message._IsValidFunc(value, 'string')):
        return value
      if isinstance(value, MessageValue):  # Message value must be serialized.
        return value
      raise ValueError("String value expected in field '%s' in message '%s'" %
                       (field.name, self.name))

    # Sub-message or dictionary.
    sub_msg = None
    if field.type_ in self.messages:
      sub_msg = self.messages[field.type_]
    else:
      for m in outer_messages:
        if field.type_ in m:
          sub_msg = m[field.type_]
          break
      if not sub_msg:
        raise NameError('Cannot find a message: ' + field.type_)

    if not isinstance(value, dict):
      raise ValueError("Struct value expected in field '%s' in message '%s'" %
                       (field.name, self.name))
    return sub_msg.ValidateDict(value, outer_messages + [self.messages])

  @staticmethod
  def _IsValidFunc(value, type_):
    """Whether or not a function |value| is compatible with |type|."""
    if (isinstance(value, stl.base.FuncGetField) and
        isinstance(value.obj, stl.base.Role) and
        value.obj.fields[value.field].type_ == type_):
      return True
    if isinstance(value, stl.base.FuncSet):
      if isinstance(value.obj, stl.base.LocalVar) and value.obj.type_ == type_:
        return True
      if (isinstance(value.obj, stl.base.Role) and
          value.obj.fields[value.field].type_ == type_):
        return True
    if isinstance(
        value, stl.base.QualifierValue.Resolved) and value.qual_type == type_:
      return True
    return None


class MessageFromExternal(Message):
  """A protocol specification external.

  message mProtocolExample {
    encode "json";
    external "external.class.Name";

  Attributes:
    external: External message class name.
    descriptor: google.protobuf.descriptor.Descriptor to generate self.external.
  """

  def __init__(self, name, encode_name, is_array, external):
    Message.__init__(self, name, encode_name, is_array)
    # Import external message type if it is passed as a string.
    if stl.base.IsString(external):
      module, message_type = external.rsplit('.', 1)
      self.descriptor = importlib.import_module(module).__getattribute__(
          message_type).DESCRIPTOR
    # Otherwise, a descriptor should be passed.
    else:
      self.descriptor = external
    self.external = MessageFromExternal._MakeClass(self.descriptor)
    self._ExtractFieldsFromDesc(self.descriptor)

  def __str__(self):
    return '%s b(%s)' % (Message.__str__(self), self.descriptor.name)

  def _ExtractFieldsFromDesc(self, desc):
    for f in desc.fields:
      if f.type == f.TYPE_MESSAGE:
        if f.name not in self.messages:
          self.messages[f.name] = MessageFromExternal(f.name, self.encode_name,
                                                      False, f.message_type)
        type_ = f.name
      else:
        type_ = MessageFromExternal._GetFieldType(f)
      field = stl.base.Field(f.name, type_, f.label == f.LABEL_OPTIONAL,
                             f.label == f.LABEL_REPEATED)
      self.fields.append(field)

  @staticmethod
  def _GetFieldType(f):
    """Return type for protobuf field, |f|."""
    if f.type == f.TYPE_BOOL:
      return 'bool'
    if f.type == f.TYPE_STRING:
      return 'string'
    if (f.type == f.TYPE_ENUM or f.type == f.TYPE_FIXED32 or
        f.type == f.TYPE_FIXED64 or f.type == f.TYPE_INT32 or
        f.type == f.TYPE_INT64 or f.type == f.TYPE_SFIXED32 or
        f.type == f.TYPE_SFIXED64 or f.type == f.TYPE_SINT32 or
        f.type == f.TYPE_SINT64 or f.type == f.TYPE_UINT32 or
        f.type == f.TYPE_UINT64):
      return 'int'
    # TODO(byungchul): Need to support more types
    # raise NotImplementedError('Not supported protobuf type: ' + f.name)
    return 'int'

  @staticmethod
  def _MakeClass(descriptor):
    """Utility function for generating an external class from a Descriptor."""
    attributes = {}
    for name, nested_type in descriptor.nested_types_by_name.items():
      attributes[name] = MessageFromExternal._MakeClass(nested_type)
    attributes[
        reflection.GeneratedProtocolMessageType._DESCRIPTOR_KEY] = descriptor  # pylint: disable=protected-access, line-too-long
    return reflection.GeneratedProtocolMessageType(
        str(descriptor.name), (message.Message,), attributes)


class MessageValue(stl.base.NamedObject):
  """Message instances.

  A message instance is expanded from a protocol spec, Message and values
  corresponding to fields.

  Attributes:
    msg: Protocol spec (message.Message)
    value_dict_or_array: Map (or array of maps) of protocol fields and values.
  """

  def __init__(self, name, msg):
    stl.base.NamedObject.__init__(self, name)
    self.msg = msg
    self.value_dict_or_array = None

  def __str__(self):
    return 'MESSAGE-VALUE %s: v(%s)' % (self.name,
                                        str(self.value_dict_or_array))

  def Encode(self):
    """Encode this message instance into actual data stream.

    The supported encoding methods are: json, protobuf, and user-defined
    encodings.

    Returns:
      A string encoded.
    """
    assert self.value_dict_or_array is not None
    logging.log(1, 'Encoding ' + self.name)
    resolved = MessageValue._ResolveVars(self.value_dict_or_array)
    logging.debug('Resolved: ' + str(resolved))
    return self.msg.encoding.SerializeToString(resolved, self.msg)

  def _EncodeToString(self):
    """Coerce to string type."""
    return self.Encode()

  def Match(self, encoded):
    """Whether or not |encoded| is compatible with this message instance.

    If |encoded| has all required fields, and values of all fields are same to
    those of this message instance, it is compatible. Otherwise, i.e
    1) it doesn't have some required fields
    2) it has some values of fields different from specified in |value_dict| of
       this message instance

    Args:
      encoded: A string expected to be encoded with same encoding method of
          this message instance.

    Returns:
      Whether or not |encoded| is compatible with this message instance.
    """
    logging.log(1, 'Decoding %s: %s', self.name, encoded)
    decoded = self.msg.encoding.ParseFromString(encoded, self.msg)
    logging.info('Matching message value:\nExpected: %s\nActual: %s\n',
                 self.value_dict_or_array, decoded)
    return MessageValue._MatchValue(self.value_dict_or_array, decoded)

  def _MatchFromString(self, encoded_string):
    return self.Match(encoded_string)

  @staticmethod
  def _ResolveVars(value):
    """Resolve any variables or run any functions in |value|.

    Args:
      value: Value which may have variables or functions to resolve.
    Returns:
      Resolved value.
    Raises:
      ValueError: If a concrete value for |value| cannot be determined.
    """
    if isinstance(value, dict):
      resolved_value = {}
      for k, v in value.iteritems():
        resolved_value[k] = MessageValue._ResolveVars(v)
      return resolved_value

    if isinstance(value, list):
      return [MessageValue._ResolveVars(v) for v in value]

    if isinstance(value, stl.base.QualifierValue.Resolved):
      return value.Generate()

    if isinstance(value, stl.base.LocalVar):
      # Local var is initialized with random value.
      if value.value is None:
        raise ValueError("LocalVar '%s' does not have a value." % value.name)
      return value.value

    if isinstance(value, stl.base.Func):
      return value.Run()

    if isinstance(value, MessageValue):
      # type must be string. Coerce value to string.
      return value._EncodeToString()  # pylint: disable=protected-access

    return value

  @staticmethod
  def _MatchValue(expected, actual):
    """Whether or not |expected| is same value of |actual|.

    Args:
      expected: Expected value.
      actual: Actual value.

    Returns:
      True if:
        1) Type of |expected| and of |actual| must be same.
        2) If type of |expected| is dictionary or sub-message, all fields
           specified in |expected| must have same value in |actual|.
        3) If type of |expected| is array, all entries specified in |expected|
           must exist in |actual| in any order.
        4) If type of |expected| is either integer or string, |expected| must
           be same to |actual|.
    """
    if isinstance(expected, dict):
      if not isinstance(actual, dict):
        return False
      for k, v in expected.iteritems():
        if k not in actual:
          logging.log(1, 'Not exist: field=' + k)
          return False
        if not MessageValue._MatchValue(v, actual[k]):
          logging.log(1, 'Different: field=%s, expected=%s, actual=%s', k, v,
                      actual[k])
          return False
      return True

    if isinstance(expected, list):
      if not isinstance(actual, list):
        return False
      for e in expected:
        found = False
        for a in actual:
          if MessageValue._MatchValue(e, a):
            found = True
            break
        if not found:
          return False
      return True

    if isinstance(expected, stl.base.QualifierValue.Resolved):
      return expected.ValidateAndSet(actual)

    if isinstance(expected, stl.base.FuncSet):
      # TODO(byungchul): Type checking.
      expected.SetValue(actual)
      return True

    if isinstance(expected, stl.base.LocalVar):
      return expected.value == actual

    if isinstance(expected, stl.base.Func):
      return expected.Run() == actual

    if isinstance(expected, MessageValue):
      # type must be string.
      return expected._MatchFromString(actual)  # pylint: disable=protected-access

    return expected == actual
