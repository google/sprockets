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

"""Defines qualifier for message fields."""

import importlib
import logging

import stl.base


# TODO(seantopping): Support expanded qualifiers.
class Qualifier(stl.base.ParameterizedObject):
  """Field qualifier for messages.

  A user defined qualifier must inherit from stl.lib.Qualifier. Qualifiers
  are used to validate and generate values for message fields.

  Attributes:
    qual_type: The field type to be qualified (int, bool, string, message).
  """

  def __init__(self, name, qual_type):
    stl.base.ParameterizedObject.__init__(self, name)
    self.qual_type = qual_type

  def __eq__(self, other):
    return (stl.base.ParameterizedObject.__eq__(self, other) and
            self.qual_type == other.qual_type)

  def __str__(self):
    return 'Qualifier %s: p(%s)' % (self.name, stl.base.GetCSV(self.params))


class QualifierFromExternal(Qualifier):
  """Wraps an external qualifier defined in a python file.

  Example:
  qualifier int RandomInt() = external "foo.bar.RandomInt";

  There should be a python module "foo.bar" with a class RandomInt that inherits
  stl.lib.Qualifier.

  Attributes:
    external_name: Name of class that extends stl.lib.Qualifier.
    external: An instance of the stl.lib.Qualifier class.
  """

  def __init__(self, name, qual_type, external):
    Qualifier.__init__(self, name, qual_type)
    self.external_name = external
    module, event = external.rsplit('.', 1)
    self.external = importlib.import_module(module).__getattribute__(event)()

  def __eq__(self, other):
    return (Qualifier.__eq__(self, other) and
            self.external_name == other.external_name)

  def __str__(self):
    return '%s b(%s)' % (Qualifier.__str__(self), self.external_name)

  def Resolve(self, env, resolved_params):
    del env, resolved_params  # Unused.
    logging.log(1, 'Resolving ' + self.name)
    return self.external
