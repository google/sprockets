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

"""Defines events."""

import importlib
import logging

import stl.base
import stl.lib


class Event(stl.base.ParameterizedObject):
  """User defined events.

  A user defined event must be an expression of a external event with arguments.
  For example,

  event eUserDefinedEvent = eBuiltInEvent(arg1, arg2);

  It provides all information to turn event.EventInTransition into
  stl.base.Func.

  Attributes:
    expand: Expression to expand to a resolved event, stl.base.Func.
  """

  def __init__(self, name):
    stl.base.ParameterizedObject.__init__(self, name)
    self.expand = None

  def __eq__(self, other):
    return (stl.base.ParameterizedObject.__eq__(self, other) and
            self.expand == other.expand)

  def __str__(self):
    return ('EVENT %s: p(%s) e(%s)' %
            (self.name, stl.base.GetCSV(self.params), str(self.expand)))

  def Resolve(self, env, resolved_params):
    logging.log(1, 'Resolving ' + self.name)
    if not self.expand:
      # Need to distinguish events without expand?
      return stl.base.FuncNoOp(self.name)
    if self.expand.name == self.name:
      raise NameError('Cannot expand self: ' + self.name)
    return Event.ResolveStatic(self.expand.name, self.expand.values, env,
                               resolved_params)

  @staticmethod
  def ResolveStatic(name, values, env, resolved_params):
    """A helper function to resolve events."""
    # TODO(byungchul): Support names in different modules.
    events = env['_current_module']['events']
    found = events.get(name)
    if not found:
      raise NameError('Event {} not found in {}'.format(name, events.keys()))

    # An external event
    if isinstance(found, EventFromExternal):
      resolved = found.Resolve(env, resolved_params)
      for v in values:
        resolved.args.append(v.Resolve(env, resolved_params))
      return resolved

    # A non-external event
    if len(values) != len(found.params):
      raise TypeError('Wrong number of parameters: ' + found.name)
    new_resolved_params = {}
    new_resolved_params['_source'] = resolved_params['_source']
    new_resolved_params['_target'] = resolved_params['_target']
    for p, v in zip(found.params, values):
      new_resolved_params[p.name] = v.Resolve(env, resolved_params)
    return found.Resolve(env, new_resolved_params)


class EventFromExternal(Event):
  """An external event (i.e. defined and provided in a python file).

  event mEventExample(int param1) = external "foo.bar.EventFunction";

  There should be a python module foo.bar with a top-level function
  EventFunction. The actual event signature should be the same as
  the one specified in the stl file, except it should expect to
  take a Context as it's first argument, in addition to the others.

  In the example above, EventFunction should look like:
    def EventFunction(context, param1):
      ...

  Attributes:
    name: The STL event name (e.g. mEventExample)
    external_name: name of the external funciton, including modules
        (e.g. "foo.bar.EventFunction")
    external_event: The actual, callable event function (e.g. EventFunction)
  """

  def __init__(self, name, external):
    Event.__init__(self, name)
    self.external_name = external
    module, event = external.rsplit('.', 1)
    self.external_event = importlib.import_module(module).__getattribute__(
        event)()
    assert isinstance(self.external_event, stl.lib.Event)

  def __eq__(self, other):
    return Event.__eq__(self,
                        other) and self.external_name == other.external_name

  def __str__(self):
    return '%s b(%s)' % (Event.__str__(self), self.external_name)

  def Resolve(self, env, resolved_params):
    logging.log(1, 'Resolving ' + self.name)
    return stl.base.FuncWithContext(self.external_name, self.external_event)


class EventInTransition(stl.base.NamedObject):
  """Event instance defined in a state transition spec.

  A event instance is defined in "events" in a state transition spec. Resolve()
  turns this into stl.base.Func resolved.

  Attributes:
    source: Source role of this event.
    target: Target role of this event.
    param_values: List of values to be resolved.
  """

  def __init__(self, event, source, target):
    stl.base.NamedObject.__init__(self, event)
    self.source = source
    self.target = target
    self.param_values = []

  def __eq__(self, other):
    return (stl.base.NamedObject.__eq__(self, other) and
            self.source == other.source and self.target == other.target and
            self.param_values == other.param_values)

  def __str__(self):
    return ('EVENT %s: s(%s), t(%s), v(%s)' %
            (self.name, self.source, self.target,
             stl.base.GetCSV(self.param_values)))

  def Resolve(self, env, resolved_params):
    logging.log(1, 'Resolving ' + self.name)

    # Resolve with implicit context parameters.
    source = stl.base.Role.FindStatic(self.source, env, resolved_params)
    target = stl.base.Role.FindStatic(self.target, env, resolved_params)
    old_source = resolved_params.pop('_source', None)
    old_target = resolved_params.pop('_target', None)
    resolved_params['_source'] = source
    resolved_params['_target'] = target

    func = Event.ResolveStatic(self.name, self.param_values, env,
                               resolved_params)
    if isinstance(func, stl.base.FuncWithContext):
      func.context.source = source
      func.context.target = target

    # Clear event context.
    if old_source:
      resolved_params['_source'] = old_source
    else:
      resolved_params.pop('_source', None)
    if old_target:
      resolved_params['_target'] = old_target
    else:
      resolved_params.pop('_target', None)

    return func
