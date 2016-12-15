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

"""Tests for stl.base."""
# pylint: disable=invalid-name

import unittest

import stl.base


class BaseTest(unittest.TestCase):

  def testConstEquality(self):
    a_bool_true = stl.base.Const('a', 'bool', stl.base.Value(True))
    self.assertEqual(a_bool_true,
                     stl.base.Const('a', 'bool', stl.base.Value(True)))

    a_bool_false = stl.base.Const('a', 'bool', stl.base.Value(False))
    self.assertNotEqual(a_bool_true, a_bool_false)

    a_int_0 = stl.base.Const('a', 'int', stl.base.Value(0))
    b_int_0 = stl.base.Const('b', 'int', stl.base.Value(0))
    self.assertNotEqual(a_int_0, b_int_0)

    a_str_0 = stl.base.Const('a', 'string', stl.base.Value(0))
    a_str_0str = stl.base.Const('a', 'string', stl.base.Value('0'))
    self.assertNotEqual(a_str_0, a_str_0str)

    self.assertNotEqual(a_bool_true, b_int_0)

  def testRoleEquality(self):
    rRoleEmpty = stl.base.Role('empty')
    self.assertEqual(rRoleEmpty, stl.base.Role('empty'))

    rRoleFields = stl.base.Role('fields')
    rRoleFields.fields = {
        'a': stl.base.Field('a', 'int'),
        'b': stl.base.Field('b', 'string')
    }
    rRoleFields2 = stl.base.Role('fields')
    rRoleFields2.fields = {
        'a': stl.base.Field('a', 'int'),
        'b': stl.base.Field('b', 'string')
    }
    self.assertEqual(rRoleFields, rRoleFields2)
    self.assertNotEqual(rRoleEmpty, rRoleFields)

    rRoleFieldsSameNameDifferentType = stl.base.Role('fields')
    rRoleFieldsSameNameDifferentType.fields = {
        'a': stl.base.Field('a', 'bool'),
        'b': stl.base.Field('b', 'int')
    }
    self.assertNotEqual(rRoleFields, rRoleFieldsSameNameDifferentType)

    rRoleMissingField = stl.base.Role('fields')
    rRoleMissingField.fields = {'a': stl.base.Field('a', 'int')}
    self.assertNotEqual(rRoleFields, rRoleMissingField)


if __name__ == '__main__':
  unittest.main()
