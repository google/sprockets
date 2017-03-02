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
"""Tests for the stl parser."""
# pylint: disable=invalid-name

import unittest

import stl.base
import stl.event
import stl.message
import stl.parser
import stl.qualifier
import stl.state


class StlParserTest(unittest.TestCase):

  # A dummy file name to appease the lexer/parser.
  # This file does not actually exist anywhere.
  TEST_FILENAME = 'dummy.stl'

  def setUp(self):
    self.actual_module_dict = {}
    stl.parser._InitializeModuleDict(self.actual_module_dict)
    self.parse_env = {}
    self.lexer = stl.parser._GetLexer(self.TEST_FILENAME)
    self.parser = stl.parser._GetParser(self.TEST_FILENAME,
                                        self.actual_module_dict,
                                        self.parse_env)
    self.expected_module_dict = {}
    stl.parser._InitializeModuleDict(self.expected_module_dict)
    self.expected_module_dict['name'] = 'foo'

  def tearDown(self):
    self.actual_module_dict = {}
    self.expected_module_dict = {}
    self.lexer = None
    self.parser = None

  def Parse(self, text):
    """Parse |text| and store the parsed information in self.module_dict.

    Args:
      text: The text to parse.

    Returns:
      self.module_dict, which is a dictionary with the parsed text information.
    """
    self.parser.parse(text, lexer=self.lexer)

  def testLineNumber(self):
    input_text = ('module foo;\n'
                  'const int a = 1;\n'
                  '\n'
                  '// Comments\n'
                  'const int b = 2;')
    self.Parse(input_text)
    self.assertEqual(5, self.lexer.lineno)
    self.assertFalse('error' in self.parse_env)

  def testEmptyFileFailure(self):
    input_text = ''

    with self.assertRaises(stl.parser.StlSyntaxError):
      self.Parse(input_text)
    self.assertTrue('error' in self.parse_env and self.parse_env['error'])

  def testSingleCommentFailure(self):
    input_text = '// This is just a comment.'
    with self.assertRaises(stl.parser.StlSyntaxError):
      self.Parse(input_text)
    self.assertTrue('error' in self.parse_env and self.parse_env['error'])

  def testEmptyModuleFailure(self):
    input_text = 'module foo;'
    with self.assertRaises(stl.parser.StlSyntaxError):
      self.Parse(input_text)
    self.assertTrue('error' in self.parse_env and self.parse_env['error'])

  def testConst_Bool(self):
    input_text = ('module foo;\n'
                  '// Constants\n'
                  '//\n'
                  'const bool a = true;\n'
                  'const bool b = false;\n')
    self.expected_module_dict['consts'] = {
        'a': stl.base.Const('a', 'bool', stl.base.Value(True)),
        'b': stl.base.Const('b', 'bool', stl.base.Value(False))
    }

    self.Parse(input_text)
    self.assertDictEqual(self.expected_module_dict, self.actual_module_dict)
    self.assertFalse('error' in self.parse_env)

  def testConst_Int(self):
    input_text = ('module foo;\n'
                  '// Constants\n'
                  '//\n'
                  'const int a = -5;\n'
                  'const int b = 0;\n'
                  'const int c = 123456789;\n')
    self.expected_module_dict['consts'] = {
        'a': stl.base.Const('a', 'int', stl.base.Value(-5)),
        'b': stl.base.Const('b', 'int', stl.base.Value(0)),
        'c': stl.base.Const('c', 'int', stl.base.Value(123456789))
    }

    self.Parse(input_text)
    self.assertDictEqual(self.expected_module_dict, self.actual_module_dict)
    self.assertFalse('error' in self.parse_env)

  def testConst_String(self):
    input_text = ('module foo;\n'
                  '// Constants\n'
                  '//\n'
                  'const string a = "a";\n'
                  'const string b = "";\n'
                  'const string c = "A long string";\n'
                  'const string d = "With \\"esc\\\\apes\\"";\n')
    self.expected_module_dict['consts'] = {
        'a': stl.base.Const('a', 'string', stl.base.Value('a')),
        'b': stl.base.Const('b', 'string', stl.base.Value('')),
        'c': stl.base.Const('c', 'string', stl.base.Value('A long string')),
        'd': stl.base.Const('d', 'string', stl.base.Value(r'With "esc\apes"'))
    }

    self.Parse(input_text)
    self.assertDictEqual(self.expected_module_dict, self.actual_module_dict)
    self.assertFalse('error' in self.parse_env)

  def testRole(self):
    input_text = ('module foo;\n'
                  '// Roles\n'
                  '//\n'
                  'role rRoleA {\n'
                  '  bool myBoolean;\n'
                  '  int i;\n'
                  '  int j;\n'
                  '  string msg;\n'
                  '}\n'
                  '\n'
                  'role rRoleB {}\n')
    rRoleA = stl.base.Role('rRoleA')
    rRoleA.fields = {
        'myBoolean': stl.base.Field('myBoolean', 'bool'),
        'i': stl.base.Field('i', 'int'),
        'j': stl.base.Field('j', 'int'),
        'msg': stl.base.Field('msg', 'string')
    }
    self.expected_module_dict['roles'] = {
        'rRoleA': rRoleA,
        'rRoleB': stl.base.Role('rRoleB')
    }

    self.Parse(input_text)
    self.assertDictEqual(self.expected_module_dict, self.actual_module_dict)
    self.assertFalse('error' in self.parse_env)

  def testState_NoParams(self):
    input_text = ('module foo;\n'
                  '// States\n'
                  '//\n'
                  'state sSimpleState {\n'
                  '  kValue1,\n'
                  '}')

    sSimpleState = stl.state.State('sSimpleState')
    sSimpleState.values = ['kValue1']

    self.expected_module_dict['states'] = {'sSimpleState': sSimpleState,}

    self.Parse(input_text)
    self.assertDictEqual(self.expected_module_dict, self.actual_module_dict)
    self.assertFalse('error' in self.parse_env)

  def testState_Params(self):
    input_text = ('module foo;\n'
                  '// States\n'
                  '//\n'
                  'state sWithSingleParamState(int param) {\n'
                  '  kValue1,\n'
                  '  kValue2,\n'
                  '  kValue3,\n'
                  '}\n'
                  'state sWithMultipleParams(int p1, role p2, string p3) {\n'
                  '  kValue1,\n'
                  '  kValue2,\n'
                  '}')

    sWithSingleParamState = stl.state.State('sWithSingleParamState')
    sWithSingleParamState.values = ['kValue1', 'kValue2', 'kValue3']
    sWithSingleParamState.params = [stl.base.Param('param', 'int')]

    sWithMultipleParams = stl.state.State('sWithMultipleParams')
    sWithMultipleParams.values = ['kValue1', 'kValue2']
    sWithMultipleParams.params = [
        stl.base.Param('p1', 'int'), stl.base.Param('p2', 'role'),
        stl.base.Param('p3', 'string')
    ]
    self.expected_module_dict['states'] = {
        'sWithSingleParamState': sWithSingleParamState,
        'sWithMultipleParams': sWithMultipleParams
    }

    self.Parse(input_text)
    self.assertDictEqual(self.expected_module_dict, self.actual_module_dict)
    self.assertFalse('error' in self.parse_env)

  def testMessages_NoNesting(self):
    input_text = ('module foo;\n'
                  '// Messages\n'
                  '//\n'
                  'message mSimpleJsonMsg {\n'
                  '  encode "stl.lib.JsonEncoding";\n'
                  '  required string msg;\n'
                  '  optional int id;\n'
                  '  repeated bool bits;\n'
                  '}\n'
                  '\n'
                  'message mSimpleProtobufMsg {\n'
                  '  encode "stl.lib.ProtobufEncoding";\n'
                  '  external "stl.parser_test_proto_pb2.SimpleMsg";\n'
                  '}')

    mSimpleJsonMsg = stl.message.Message(
        'mSimpleJsonMsg', 'stl.lib.JsonEncoding', is_array=False)
    mSimpleJsonMsg.fields = [
        stl.base.Field('msg', 'string'), stl.base.Field(
            'id', 'int', optional=True), stl.base.Field(
                'bits', 'bool', repeated=True)
    ]

    # See parser_test_proto.proto for the specificiation
    mSimpleProtobufMsg = stl.message.Message(
        'mSimpleProtobufMsg', 'stl.lib.ProtobufEncoding', is_array=False)
    mSimpleProtobufMsg.fields = [
        stl.base.Field('foo', 'string'), stl.base.Field(
            'fizz', 'int', optional=True), stl.base.Field(
                'buzz', 'bool', repeated=True)
    ]

    self.expected_module_dict['messages'] = {
        'mSimpleJsonMsg': mSimpleJsonMsg,
        'mSimpleProtobufMsg': mSimpleProtobufMsg,
    }
    self.Parse(input_text)
    self.assertDictEqual(self.expected_module_dict, self.actual_module_dict)
    self.assertFalse('error' in self.parse_env)

  def testMessages_WithNesting(self):
    input_text = ('module foo;\n'
                  '// Messages\n'
                  '//\n'
                  'message mNestedJsonMsg {\n'
                  '  encode "stl.lib.JsonEncoding";\n'
                  '\n'
                  '  required mInnerMsg inner;\n'
                  '  optional mExtraMsg extra;\n'
                  '\n'
                  '  message mInnerMsg {\n'
                  '    required string in;\n'
                  '    required int k;\n'
                  '  }\n'
                  '\n'
                  '  message mExtraMsg {\n'
                  '    repeated int nums;\n'
                  '  }\n'
                  '}')
    mInnerMsg = stl.message.Message('mInnerMsg', None, is_array=False)
    mInnerMsg.fields = [
        stl.base.Field('in', 'string'), stl.base.Field('k', 'int')
    ]

    mExtraMsg = stl.message.Message('mExtraMsg', None, is_array=False)
    mExtraMsg.fields = [stl.base.Field('nums', 'int', repeated=True)]

    mNestedJsonMsg = stl.message.Message(
        'mNestedJsonMsg', 'stl.lib.JsonEncoding', is_array=False)
    mNestedJsonMsg.fields = [
        stl.base.Field('inner', 'mInnerMsg'), stl.base.Field(
            'extra', 'mExtraMsg', optional=True)
    ]
    mNestedJsonMsg.messages = {'mInnerMsg': mInnerMsg, 'mExtraMsg': mExtraMsg}

    self.expected_module_dict['messages'] = {'mNestedJsonMsg': mNestedJsonMsg}

    self.Parse(input_text)
    self.assertDictEqual(self.expected_module_dict, self.actual_module_dict)
    self.assertFalse('error' in self.parse_env)

  def testMessages_IsArray(self):
    input_text = ('module foo;\n'
                  '// Messages\n'
                  '//\n'
                  'message[] mMessageArray {\n'
                  '  encode "stl.lib.JsonEncoding";\n'
                  '  required string msg;\n'
                  '}')

    mMessageArray = stl.message.Message(
        'mMessageArray', 'stl.lib.JsonEncoding', is_array=True)
    mMessageArray.fields = [stl.base.Field('msg', 'string')]

    self.expected_module_dict['messages'] = {'mMessageArray': mMessageArray}

    self.Parse(input_text)
    self.assertDictEqual(self.expected_module_dict, self.actual_module_dict)
    self.assertFalse('error' in self.parse_env)

  def testQualifier_External(self):
    input_text = ('module foo;\n'
                  '// Qualifiers\n'
                  '//\n'
                  'qualifier int qUniqueInt(int prev) =\n'
                  '    external "stl.lib.UniqueInt";')

    qUniqueInt = stl.qualifier.QualifierFromExternal('qUniqueInt', 'int',
                                                     'stl.lib.UniqueInt')

    qUniqueInt.params = [stl.base.Param('prev', 'int')]

    self.expected_module_dict['qualifiers'] = {'qUniqueInt': qUniqueInt}

    self.Parse(input_text)
    self.assertDictEqual(self.expected_module_dict, self.actual_module_dict)
    self.assertFalse('error' in self.parse_env)

  def testEvent_NoDefinition(self):
    input_text = ('module foo;\n'
                  '// Events\n'
                  '//\n'
                  'event eSimplestEvent;\n'
                  'event eSimpleEventWithParams(string s, int i);')

    eSimplestEvent = stl.event.Event('eSimplestEvent')

    eSimpleEventWithParams = stl.event.Event('eSimpleEventWithParams')
    eSimpleEventWithParams.params = [
        stl.base.Param('s', 'string'), stl.base.Param('i', 'int')
    ]

    self.expected_module_dict['events'] = {
        'eSimplestEvent': eSimplestEvent,
        'eSimpleEventWithParams': eSimpleEventWithParams
    }

    self.Parse(input_text)
    self.assertDictEqual(self.expected_module_dict, self.actual_module_dict)
    self.assertFalse('error' in self.parse_env)

  def testEvent_WithDefinition(self):
    input_text = ('module foo;\n'
                  '// Events\n'
                  '//\n'
                  'event eEvent(int id, string name) =\n'
                  '  BuiltInFunction(id);\n'
                  '\n'
                  'event eSimpleEvent(int a, int b, int c);'
                  'event eDerivedFromSimpleEvent(int q) =\n'
                  '  eSimpleEvent(q, 0, 27);\n')

    eEvent = stl.event.Event('eEvent')
    eEvent.params = [
        stl.base.Param('id', 'int'), stl.base.Param('name', 'string')
    ]
    eEvent.expand = stl.base.Expand('BuiltInFunction')
    eEvent.expand.values = [stl.base.Value('$id')]

    eSimpleEvent = stl.event.Event('eSimpleEvent')
    eSimpleEvent.params = [
        stl.base.Param('a', 'int'), stl.base.Param('b', 'int'),
        stl.base.Param('c', 'int')
    ]

    eDerivedFromSimpleEvent = stl.event.Event('eDerivedFromSimpleEvent')
    eDerivedFromSimpleEvent.params = [stl.base.Param('q', 'int')]
    eDerivedFromSimpleEvent.expand = stl.base.Expand('eSimpleEvent')
    eDerivedFromSimpleEvent.expand.values = [
        stl.base.Value('$q'), stl.base.Value(0), stl.base.Value(27)
    ]

    self.expected_module_dict['events'] = {
        'eEvent': eEvent,
        'eSimpleEvent': eSimpleEvent,
        'eDerivedFromSimpleEvent': eDerivedFromSimpleEvent
    }

    self.Parse(input_text)
    self.assertDictEqual(self.expected_module_dict, self.actual_module_dict)
    self.assertFalse('error' in self.parse_env)

  def testEvent_WithMessage(self):
    input_text = ('module foo;\n'
                  '// Events\n'
                  '//\n'
                  'event eEvent =\n'
                  '  Function(mSimpleMessage {\n'
                  '              msg = "Hello, World!";\n'
                  '              num = 36;\n'
                  '           });')

    msg = stl.base.Value('Hello, World!')
    msg.name = 'msg'

    num = stl.base.Value(36)
    num.name = 'num'

    mSimpleMessage = stl.base.Expand('mSimpleMessage')
    mSimpleMessage.values = [msg, num]

    Function = stl.base.Expand('Function')
    Function.values = [mSimpleMessage]

    eEvent = stl.event.Event('eEvent')
    eEvent.expand = Function

    self.expected_module_dict['events'] = {'eEvent': eEvent}

    self.Parse(input_text)
    self.assertDictEqual(self.expected_module_dict, self.actual_module_dict)
    self.assertFalse('error' in self.parse_env)

  def testEvent_WithMessageArray(self):
    input_text = ('module foo;\n'
                  '// Events\n'
                  '//\n'
                  'event eEvent =\n'
                  '  Func(mMessageArray [{\n'
                  '          msg = "First!";\n'
                  '      },\n'
                  '      {\n'
                  '          msg = "Second!";\n'
                  '      },\n'
                  '      {,\n'
                  '          msg = "Third!";\n'
                  '      }]);'
                  '\n'
                  'event eEventEmpty =\n'
                  '  Func(mEmptyArray []);')

    first = stl.base.Value('First!')
    first.name = 'msg'

    second = stl.base.Value('Second!')
    second.name = 'msg'

    third = stl.base.Value('Third!')
    third.name = 'msg'

    mMessageArray = stl.base.Expand('mMessageArray')
    mMessageArray.values = [stl.base.Value([first, second, third])]

    eEvent = stl.event.Event('eEvent')
    eEvent.expand = mMessageArray

    mEmptyArray = stl.base.Expand('mEmptyArray')
    mEmptyArray.values = []

    eEventEmpty = stl.base.Expand('mEmptyArray')
    eEventEmpty.expand = mEmptyArray

    self.expected_module_dict['events'] = {
        'eEvent': eEvent,
        'eEventEmpty': eEventEmpty
    }

    # TODO(mbjorge): Enable when message[] is supported.
    _ = input_text
    # self.Parse(input_text)
    # self.assertDictEqual(self.expected_module_dict, self.actual_module_dict)
    # self.assertFalse('error' in self.parse_env)

  def testTransition_NoVariablesNoOring(self):
    input_text = ('module foo;\n'
                  '// Transitions\n'
                  '//\n'
                  'transition tBasic(int id) {\n'
                  '  pre_states = [ sState.kValue1 ]\n'
                  '  events {\n'
                  '    rRole1 -> eEvent(id) -> rRole2;\n'
                  '  }\n'
                  '  post_states = [ sState.kValue2 ]\n'
                  '  error_states = [ sState.kValue3 ]\n'
                  '}\n'
                  '\n'
                  'transition tBasic27 = tBasic(27);')

    tBasic = stl.state.Transition('tBasic')
    tBasic.params = [stl.base.Param('id', 'int')]
    tBasic.pre_states = [[
        stl.state.StateValueInTransition('sState', 'kValue1')
    ]]

    eEventInTransistion = stl.event.EventInTransition('eEvent', 'rRole1',
                                                      'rRole2')
    eEventInTransistion.param_values = [stl.base.Value('$id')]

    tBasic.events = [eEventInTransistion]
    tBasic.post_states = [stl.state.StateValueInTransition('sState', 'kValue2')]
    tBasic.error_states = [
        stl.state.StateValueInTransition('sState', 'kValue3')
    ]

    tBasic27 = stl.state.Transition('tBasic27')
    tBasic27.expand = stl.base.Expand('tBasic')
    tBasic27.expand.values = [stl.base.Value(27)]

    self.expected_module_dict['transitions'] = {
        'tBasic': tBasic,
        'tBasic27': tBasic27
    }

    self.Parse(input_text)
    self.assertDictEqual(self.expected_module_dict, self.actual_module_dict)
    self.assertFalse('error' in self.parse_env)

  def testTransition_WithOringNoVariables(self):
    input_text = ('module foo;\n'
                  '// Transitions\n'
                  '//\n'
                  'transition tBasic(int id) {\n'
                  '  pre_states = [ sState.{kValue11, kValue22},\n'
                  '                 sOtherState.{kValueA, kValueB} ]\n'
                  '  events {\n'
                  '    rRole1 -> eEvent(id) -> rRole2;\n'
                  '  }\n'
                  '  post_states = [ sState.kValue2 ]\n'
                  '  error_states = [ sState.kValue3 ]\n'
                  '}\n'
                  '\n'
                  'transition tBasic27 = tBasic(27);')

    tBasic = stl.state.Transition('tBasic')
    tBasic.params = [stl.base.Param('id', 'int')]
    tBasic.pre_states = [[
        stl.state.StateValueInTransition('sState', 'kValue11'),
        stl.state.StateValueInTransition('sState', 'kValue22')
    ], [
        stl.state.StateValueInTransition('sOtherState', 'kValueA'),
        stl.state.StateValueInTransition('sOtherState', 'kValueB')
    ]]

    eEventInTransistion = stl.event.EventInTransition('eEvent', 'rRole1',
                                                      'rRole2')
    eEventInTransistion.param_values = [stl.base.Value('$id')]
    tBasic.events = [eEventInTransistion]

    tBasic.post_states = [stl.state.StateValueInTransition('sState', 'kValue2')]
    tBasic.error_states = [
        stl.state.StateValueInTransition('sState', 'kValue3')
    ]

    tBasic27 = stl.state.Transition('tBasic27')
    tBasic27.expand = stl.base.Expand('tBasic')
    tBasic27.expand.values = [stl.base.Value(27)]

    self.expected_module_dict['transitions'] = {
        'tBasic': tBasic,
        'tBasic27': tBasic27
    }

    self.Parse(input_text)
    self.maxDiff = None
    self.assertDictEqual(self.expected_module_dict, self.actual_module_dict)
    self.assertFalse('error' in self.parse_env)

  def testTransition_WithVariables(self):
    input_text = ('module foo;\n'
                  '// Transitions\n'
                  '//\n'
                  'transition tBasic {\n'
                  '  string data;\n'
                  '  pre_states = [ sState.kPreValue ]\n'
                  '  events {\n'
                  '    rRole1 -> eFillData(&data) -> rRole2;\n'
                  '    rRole2 -> eUseData(data) -> rRole3;\n'
                  '  }\n'
                  '  post_states = [ sState.kPostValue ]\n'
                  '}')

    tBasic = stl.state.Transition('tBasic')
    tBasic.local_vars = [stl.base.LocalVar('data', 'string')]
    tBasic.pre_states = [[
        stl.state.StateValueInTransition('sState', 'kPreValue')
    ]]

    eFillData = stl.event.EventInTransition('eFillData', 'rRole1', 'rRole2')
    eFillData.param_values = [stl.base.Value('&data')]
    eUseData = stl.event.EventInTransition('eUseData', 'rRole2', 'rRole3')
    eUseData.param_values = [stl.base.Value('$data')]
    tBasic.events = [eFillData, eUseData]

    tBasic.post_states = [
        stl.state.StateValueInTransition('sState', 'kPostValue')
    ]

    self.expected_module_dict['transitions'] = {'tBasic': tBasic}

    self.Parse(input_text)
    self.assertDictEqual(self.expected_module_dict, self.actual_module_dict)
    self.assertFalse('error' in self.parse_env)


if __name__ == '__main__':
  unittest.main()
