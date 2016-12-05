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

"""Tests for stl.message."""
# pylint: disable=invalid-name

import unittest

import stl.base
import stl.message


class MessageTest(unittest.TestCase):

  def testMessageEquality_NoNesting(self):
    mSimpleJsonMsg = stl.message.Message(
        'mSimpleJsonMsg', 'stl.lib.JsonEncoding', is_array=False)
    mSimpleJsonMsg.fields = [
        stl.base.Field('msg', 'string'),
        stl.base.Field('id', 'int', optional=True),
        stl.base.Field('bits', 'bool', repeated=True)
    ]

    mSimpleJsonMsg2 = stl.message.Message(
        'mSimpleJsonMsg', 'stl.lib.JsonEncoding', is_array=False)
    mSimpleJsonMsg2.fields = [
        stl.base.Field('msg', 'string'),
        stl.base.Field('id', 'int', optional=True),
        stl.base.Field('bits', 'bool', repeated=True)
    ]
    self.assertEqual(mSimpleJsonMsg, mSimpleJsonMsg2)

    mSimpleProtobufMsg = stl.message.Message(
        'mSimpleProtobufMsg', 'stl.lib.ProtobufEncoding', is_array=False)
    mSimpleProtobufMsg.fields = [
        stl.base.Field('foo', 'string'),
        stl.base.Field('fizz', 'int', optional=True),
        stl.base.Field('buzz', 'bool', repeated=True)
    ]

    self.assertNotEqual(mSimpleJsonMsg, mSimpleProtobufMsg)

  def testMessageEquality_WithNesting(self):
    mInnerMsg = stl.message.Message('mInnerMsg', None, is_array=False)
    mInnerMsg.fields = [
        stl.base.Field('in', 'string'),
        stl.base.Field('k', 'int')
    ]

    mExtraMsg = stl.message.Message('mExtraMsg', None, is_array=False)
    mExtraMsg.fields = [stl.base.Field('nums', 'int', repeated=True)]

    mNestedJsonMsg = stl.message.Message(
        'mNestedJsonMsg', 'stl.lib.JsonEncoding', is_array=False)
    mNestedJsonMsg.fields = [
        stl.base.Field('inner', 'mInnerMsg'),
        stl.base.Field('extra', 'mExtraMsg', optional=True)
    ]
    mNestedJsonMsg.messages = {'mInnerMsg': mInnerMsg, 'mExtraMsg': mExtraMsg}

    mNestedJsonMsg2 = stl.message.Message(
        'mNestedJsonMsg', 'stl.lib.JsonEncoding', is_array=False)
    mNestedJsonMsg2.fields = [
        stl.base.Field('inner', 'mInnerMsg'),
        stl.base.Field('extra', 'mExtraMsg', optional=True)
    ]
    mNestedJsonMsg2.messages = {
        'mInnerMsg': mInnerMsg,
        'mExtraMsg': mExtraMsg
    }

    self.assertEqual(mNestedJsonMsg, mNestedJsonMsg2)

    mNestedJsonMsg2.messages = {'mInnerMsg': mInnerMsg}
    self.assertNotEqual(mNestedJsonMsg, mNestedJsonMsg2)

    mNestedJsonMsg2.messages = {
        'mInnerMsg': mInnerMsg,
        'mExtraMsg': mExtraMsg
    }
    mNestedJsonMsg2.fields = [stl.base.Field('inner', 'mInnerMsg')]
    self.assertNotEqual(mNestedJsonMsg, mNestedJsonMsg2)


if __name__ == '__main__':
  unittest.main()
