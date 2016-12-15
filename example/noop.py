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

"""Dummy external event functions.

It defines a set of dummy functions helpful for testing/debugging.
"""

import logging
import time

import stl.lib


class NoOp(stl.lib.Event):

  def Fire(self, context):
    """Do nothing, always return success."""
    del context  # Unused.
    return True

  def Wait(self, context):
    """Do nothing, always return success."""
    del context  # Unused.
    return True


class Sleep(stl.lib.Event):

  def Fire(self, context, sleep_secs):
    """A dummy method that just sleeps for |sleep_secs|."""
    del context  # Unused.
    time.sleep(sleep_secs)
    return True

  def Wait(self, context, sleep_secs):
    """A dummy method that just sleeps for |sleep_secs|."""
    del context  # Unused.
    time.sleep(sleep_secs)
    return True


class LogParams(stl.lib.Event):

  def Fire(self, *args):
    """A dummy method that dumps all args to logging.info."""
    logging.info('LogParams: %s', [str(arg) for arg in args])
    return True

  def Wait(self, *args):
    """A dummy method that dumps all args to logging.info."""
    logging.info('LogParams: %s', [str(arg) for arg in args])
    return True


class LogEncodedParams(stl.lib.Event):

  def Fire(self, context, params):
    return self._Log(context, params)

  def Wait(self, context, params):
    return self._Log(context, params)

  def _Log(self, context, params):
    """A dummy method that encodes |params| and dumps that to logging.info."""
    del context  # Unused.
    if not isinstance(params, list):
      params = [params]
    logging.info('LogEncodedParams: %s', [param.Encode() for param in params])
    return True
