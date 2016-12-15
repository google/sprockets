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

"""Tests for stl.state."""
# pylint: disable=invalid-name

import unittest

import stl.base
import stl.state


class StateTest(unittest.TestCase):

  def testStateEquality(self):
    sSimpleState = stl.state.State('sSimpleState')
    sSimpleState.values = ['kValue1']

    sSimpleState2 = stl.state.State('sSimpleState')
    sSimpleState2.values = ['kValue1']

    self.assertEqual(sSimpleState, sSimpleState2)

    sSimpleState2.values = ['DIFFERENT']
    self.assertNotEqual(sSimpleState, sSimpleState2)

    sSimpleState2.values = ['kValue1', 'kValue2']
    self.assertNotEqual(sSimpleState, sSimpleState2)

    sWithSingleParamState = stl.state.State('sWithSingleParamState')
    sWithSingleParamState.values = ['kValue1', 'kValue2', 'kValue3']
    sWithSingleParamState.params = [stl.base.Param('param', 'int')]

    sWithSingleParamState2 = stl.state.State('sWithSingleParamState')
    sWithSingleParamState2.values = ['kValue1', 'kValue2', 'kValue3']
    sWithSingleParamState2.params = [stl.base.Param('param', 'int')]

    self.assertEqual(sWithSingleParamState, sWithSingleParamState2)

    sWithSingleParamState2.params = []
    self.assertNotEqual(sWithSingleParamState, sWithSingleParamState2)

    sWithSingleParamState2.params = [stl.base.Param('param', 'bool')]
    self.assertNotEqual(sWithSingleParamState, sWithSingleParamState2)

    sWithMultipleParams = stl.state.State('sWithMultipleParams')
    sWithMultipleParams.values = ['kValue1', 'kValue2']
    sWithMultipleParams.params = [stl.base.Param('param1', 'int'),
                                  stl.base.Param('param2', 'role'),
                                  stl.base.Param('msg', 'string')]

    sWithMultipleParams2 = stl.state.State('sWithMultipleParams')
    sWithMultipleParams2.values = ['kValue1', 'kValue2']
    sWithMultipleParams2.params = [stl.base.Param('param1', 'int'),
                                   stl.base.Param('param2', 'role'),
                                   stl.base.Param('msg', 'string')]

    self.assertEqual(sWithMultipleParams, sWithMultipleParams2)

    sWithMultipleParams2.values = ['kValue0', 'kValue1', 'kValue2']
    self.assertNotEqual(sWithMultipleParams, sWithMultipleParams2)

    sWithMultipleParams2.values = ['kValue1', 'kValue2']
    sWithMultipleParams2.params = [stl.base.Param('param1', 'int'),
                                   stl.base.Param('msg', 'string'),
                                   stl.base.Param('param2', 'role')]
    self.assertNotEqual(sWithMultipleParams, sWithMultipleParams2)


if __name__ == '__main__':
  unittest.main()
