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
"""Container for STL modules."""


class Module(object):
  """STL Module.

  A module is a namespaced set of STL components. Every STL file must be
  prefaced with a module name. For example:

  module my_module;

  Attributes:
    name: The name of this module.
    consts: Dictionary of stl.base.Const
    roles: Dictionary of stl.base.Role
    states: Dictionary of stl.state.State
    qualifiers: Dictionary of stl.qualifier.Qualifier
    messages: Dictionary of stl.message.Message
    events: Dictionary of stl.event.Event
    transitions: Dictionary of stl.state.Transition
  """

  def __init__(self, name):
    self.name = name
    self.consts = {}
    self.roles = {}
    self.states = {}
    self.qualifiers = {}
    self.messages = {}
    self.events = {}
    self.transitions = {}

  def __eq__(self, other):
    return (isinstance(other, Module) and self.name == other.name and
            self.consts == other.consts and self.roles == other.roles and
            self.states == other.states and
            self.qualifiers == other.qualifiers and
            self.messages == other.messages and self.events == other.events and
            self.transitions == other.transitions)

  def HasDefinition(self, name):
    """Whether this module has a named object |name|.

    Args:
      name: The string name of the object to look for.

    Returns:
      True if this module has an object with name |name|, False otherwise.
    """
    return (name in self.consts or name in self.roles or name in self.states or
            name in self.qualifiers or name in self.messages or
            name in self.events or name in self.transitions)
