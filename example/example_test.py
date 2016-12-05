#!/usr/bin/env python
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
"""Tests for example user-defined encoding scheme."""

import unittest

import stl.base
import stl.message


class KeyValueEncodingTestCase(unittest.TestCase):
  """Test KeyValueEncoding serialization and parsing."""

  def testSerializeToString(self):
    message = stl.message.Message(
        'mMessage', 'example_lib.KeyValueEncoding', False)
    field1 = stl.base.Field('request_id', 'int')
    field1.encoding_props['ord'] = 0
    field1.encoding_props['key'] = 'ri'
    field2 = stl.base.Field('data', 'string')
    field2.encoding_props['ord'] = 1
    field2.encoding_props['key'] = 'da'
    field3 = stl.base.Field('broadcast', 'bool')
    field3.encoding_props['ord'] = 2
    field3.encoding_props['key'] = 'br'
    message.fields = [field1, field2, field3]

    values = {'request_id': 10, 'data': 'dummy_data', 'broadcast': True}
    serialized = message.encoding.SerializeToString(values, message)
    self.assertEquals('ri=10,da=dummy_data,br=True', serialized)

  def testParseFromString(self):
    message = stl.message.Message(
        'mMessage', 'example_lib.KeyValueEncoding', False)
    field1 = stl.base.Field('request_id', 'int')
    field1.encoding_props['ord'] = 0
    field1.encoding_props['key'] = 'ri'
    field2 = stl.base.Field('data', 'string')
    field2.encoding_props['ord'] = 1
    field2.encoding_props['key'] = 'da'
    field3 = stl.base.Field('broadcast', 'bool')
    field3.encoding_props['ord'] = 2
    field3.encoding_props['key'] = 'br'
    message.fields = [field1, field2, field3]

    encoded = 'ri=10,da=dummy_data,br=True'
    decoded = message.encoding.ParseFromString(encoded, message)
    expected = {'request_id': 10, 'data': 'dummy_data', 'broadcast': True}
    self.assertEquals(expected, decoded)


if __name__ == '__main__':
  unittest.main()
