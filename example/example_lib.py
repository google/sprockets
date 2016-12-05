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

"""Encodes a message into a concatenated sequence of key/value pairs."""

import stl.lib


class KeyValueEncoding(stl.lib.Encoding):
  """Key/Value pair encoding.

  Each message field should have two extra properties:
    ord: The ordering of the keys.
    key: The key to use in the encoded message.

  The format of the encoded message is:
    '<key1>=<value1>,<key2>=<value2>,...'
  """

  def SerializeToString(self, values, message_type):
    kv_pairs = [None] * len(message_type.fields)
    for field in message_type.fields:
      order = field.encoding_props['ord']
      key = field.encoding_props['key']
      if field.name in values:
        val = values[field.name]
        if field.type_ == 'bool':
          kv_pairs[order] = '%s=%s' % (key, val)
        if field.type_ == 'int':
          kv_pairs[order] = '%s=%d' % (key, val)
        if field.type_ == 'string':
          kv_pairs[order] = '%s=%s' % (key, val)
    delim = ','
    return delim.join(kv_pairs)

  def ParseFromString(self, encoded, message_type):
    values = {}
    field_dict = {
        field.encoding_props['key']: field
        for field in message_type.fields
    }
    for pair in encoded.split(','):
      key, value = pair.split('=')
      field = field_dict[key]
      if field.type_ == 'bool':
        values[field.name] = value == 'True'
      if field.type_ == 'int':
        values[field.name] = int(value)
      if field.type_ == 'string':
        values[field.name] = value
    return values
