#!/usr/bin/env python
# Copyright 2017 Google Inc. All rights reserved.
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

"""Tests for handling stl parser errors."""
# pylint: disable=invalid-name

import unittest

import stl.error_formatter
import stl.error_handler
import stl.lexer
import stl.parser


class StlParserErrorTest(unittest.TestCase, stl.error_formatter.ErrorFormatter):

  # A dummy file name to appease the lexer/parser.
  # This file does not actually exist anywhere.
  TEST_FILENAME = 'dummy.stl'

  def setUp(self):
    self.foo_module = stl.module.Module('foo')
    self.global_env = {'modules': {'foo': self.foo_module}}
    self.parser = stl.parser.StlParser(self.TEST_FILENAME,
                                       self.global_env,
                                       error_formatter=self)
    self.expected_error_id = None
    self.format_called = False

  def tearDown(self):
    self.assertTrue(self.format_called)
    self.format_called = False
    self.expected_error = None

  def Format(self, error):
    """Will be called by the parser error handler to "Format" a parse error."""
    self.format_called = True
    self.assertEqual(self.expected_error.error_id, error.id)
    return ''

  def Parse(self, text):
    """Parse |text| and store the parsed information in self.global_env.

    Args:
      text: The text to parse.
    """
    self.parser.parse(text)

  def testMissingSemiColon_Module(self):
    input_text = ('module foo\n'
                  'const int a = 1;\n'
                  'const int b = 2;')
    self.expected_error = stl.error_handler._MISSING_SEMICOLON
    with self.assertRaises(stl.parser.StlSyntaxError):
      self.Parse(input_text)

  def testMissingSemiColon_ConstWithoutValue(self):
    input_text = ('module foo;\n'
                  'const int a\n'
                  'const int b = 2;')
    self.expected_error = stl.error_handler._MISSING_SEMICOLON
    with self.assertRaises(stl.parser.StlSyntaxError):
      self.Parse(input_text)

  def testMissingSemiColon_Transition(self):
    input_text = ('module foo;\n'
                  'const int a;\n'
                  'transition tTransitionBar1 = tTransistion(1)\n'
                  'transition tTransitionBar2 = tTransistion(2);')
    self.expected_error = stl.error_handler._MISSING_SEMICOLON
    with self.assertRaises(stl.parser.StlSyntaxError):
      self.Parse(input_text)

  def testMissingSemiColon_TransitionEvent(self):
    input_text = ('module foo;\n'
                  'transition tExample {\n'
                  '  pre_states = [ sState.kFoo ]\n'
                  '  events {\n'
                  '    rSender -> Event() -> rReceiver\n'
                  '  }\n'
                  '  post_states = []\n'
                  '}')
    self.expected_error = stl.error_handler._MISSING_SEMICOLON
    with self.assertRaises(stl.parser.StlSyntaxError):
      self.Parse(input_text)

  def testMissingStringQuote_Const(self):
    input_text = ('module foo;\n'
                  'const string fail = "FAIL;\n'
                  'const int i = 0;')
    self.expected_error = stl.error_handler._MISSING_STRING_QUOTE
    with self.assertRaises(stl.lexer.StlSyntaxError):
      self.Parse(input_text)

  def testSingleQuote_Const(self):
    input_text = ('module foo;\n'
                  'const string fail = \'FAIL\'\n'
                  'const int i = 0;')
    self.expected_error = stl.error_handler._UNSUPPORTED_SINGLE_QUOTE
    with self.assertRaises(stl.lexer.StlSyntaxError):
      self.Parse(input_text)

  def testMissingClosingCurlyBrace_Message(self):
    input_text = ('module foo;\n'
                  'message mMessageWithData {\n'
                  '  encode "stl.lib.JsonEncoding";\n'
                  '\n'
                  '  message mNestedMessage {\n'
                  '    required string data;\n'
                  '  }\n'
                  '\n'  # Missing closing curly brace.
                  '\n'
                  'message mOtherMessage {\n'
                  '  encode "stl.lib.JsonEncoding";\n'
                  '  require int request_id;\n'
                  '}')
    self.expected_error = stl.error_handler._MISSING_CLOSING_CURLY_BRACE
    with self.assertRaises(stl.parser.StlSyntaxError):
      self.Parse(input_text)

  def testMissingPostStates_Transition(self):
    input_text = ('module foo;\n'
                  'transition tTransistion {\n'
                  '  pre_states = [ sState.kFoo ]\n'
                  '  events {\n'
                  '    rSender -> Event() -> rReceiver;\n'
                  '  }\n'
                  '}')
    self.expected_error = stl.error_handler._MISSING_POST_STATES
    with self.assertRaises(stl.parser.StlSyntaxError):
      self.Parse(input_text)

  def testMissingPreStates_Transition(self):
    input_text = ('module foo;\n'
                  'transition tTransistion {\n'
                  '  events {\n'
                  '    rSender -> Event() -> rReceiver;\n'
                  '  }\n'
                  '  post_states = []\n'
                  '}')
    self.expected_error = stl.error_handler._MISSING_PRE_STATES
    with self.assertRaises(stl.parser.StlSyntaxError):
      self.Parse(input_text)

  def testEmptyPreStates_Transition(self):
    input_text = ('module foo;\n'
                  'transition tTransistion {\n'
                  '  pre_states = []\n'
                  '  events {\n'
                  '    rSender -> Event() -> rReceiver;\n'
                  '  }\n'
                  '  post_states = []\n'
                  '}')
    self.expected_error = stl.error_handler._EMPTY_PRE_STATES
    with self.assertRaises(stl.parser.StlSyntaxError):
      self.Parse(input_text)


if __name__ == '__main__':
  unittest.main()

if __name__ == '__main__':
  unittest.main()
