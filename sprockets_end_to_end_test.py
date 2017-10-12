"""End-to-end tests for all of Sprockets."""

import os
import shutil
import tempfile
import unittest

import mock

import test_driver

@mock.patch('test_driver.Visualizer')
class EndToEndTest(unittest.TestCase):

  def testSimpleExample(self, mock_visualizer):
    # RunTest returns True on success.
    self.assertTrue(test_driver.RunTest(
        'end_to_end_test_data/simple_example.test', {}))

  def testDidYouMean_Transition(self, mock_visualizer):
    # The tConnectTlsActual transition has a a typo; raise an exception
    # with a helpful error message.
    with self.assertRaisesRegexp(NameError, 'Did you mean tConnectTls?'):
      test_driver.RunTest(
          'end_to_end_test_data/did_you_mean_transition.test', {})

  def testDidYouMean_StateValue(self, mock_visualizer):
    # The tDisconnectTls post_state has a typo; raise an exception
    # with a helpful error message.
    with self.assertRaisesRegexp(NameError, 'Did you mean kNotConnected?'):
      test_driver.RunTest(
          'end_to_end_test_data/did_you_mean_state_value.test', {})


if __name__ == '__main__':
  unittest.main()
