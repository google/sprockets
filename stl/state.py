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
"""Defines state and trasitions."""

import logging

import stl.base
import stl.levenshtein


class State(stl.base.ParameterizedObject):
  """States.

  A state is defined with "state" keyword and its possible values. It can be
  parameterized. For example,

  state sStateExample(string param1, integer param2) {
    kStateValue1,
    kStateValue2,
  }

  Attributes:
    values: List of possible state values.
  """

  def __init__(self, name):
    stl.base.ParameterizedObject.__init__(self, name)
    self.values = []

  def __eq__(self, other):
    return (stl.base.ParameterizedObject.__eq__(self, other) and
            self.values == other.values)

  def __str__(self):
    return ('STATE %s: p(%s) v(%s)' % (self.name, stl.base.GetCSV(self.params),
                                       stl.base.GetCSV(self.values)))


class StateResolved(stl.base.ParameterizedObject):
  """State specified in trasition spec and resolved.

  Attributes:
    state: Original parameterized state.
    resolved_params: List of parameter values resolved. The order of values is
       same to that of parameters.
  """

  def __init__(self, name, state):
    stl.base.ParameterizedObject.__init__(self, name)
    self.state = state
    self.resolved_params = []

  def __str__(self):
    return 'STATE %s(%s)' % (self.name, stl.base.GetCSV(self.resolved_params))

  def __eq__(self, other):
    return (stl.base.ParameterizedObject.__eq__(self, other) and
            self.state == other.state and
            self.resolved_params == other.resolved_params)

  def InitialValue(self):
    """Returns the first state value which is defined as the initial value."""
    return StateValue(self, self.state.values[0])


class StateValue(stl.base.NamedObject):
  """State instance with value representing current state.

  Attributes:
    state: Original resolved state.
    value: Current value of |state|.
  """

  def __init__(self, state, value):
    stl.base.NamedObject.__init__(self, state.name)
    self.state = state
    self.value = value

  def __str__(self):
    return ('STATE-VALUE %s(%s).%s' % (
        self.name, stl.base.GetCSV(self.state.resolved_params), self.value))

  def __eq__(self, other):
    return (stl.base.NamedObject.__eq__(self, other) and
            self.state == other.state and self.value == other.value)


class StateValueInTransition(stl.base.NamedObject):
  """State instance defined in a state transition spec.

  A state instance is defined either in "pre_states", "post_states", or
  "error_states" in a state transition spec. Resolve() turns this into
  state.StateValue resolved.

  Attributes:
    value: Current value of state of |name|.
    param_values: List of unresolved parameters of state of |name|.
  """

  def __init__(self, state, value):
    stl.base.NamedObject.__init__(self, state)
    self.value = value
    self.param_values = []

  def __eq__(self, other):
    return (stl.base.NamedObject.__eq__(self, other) and
            self.value == other.value and
            self.param_values == other.param_values)

  def __str__(self):
    return ('STATE %s: p(%s) v(%s)' %
            (self.name, stl.base.GetCSV(self.param_values), str(self.value)))

  def Resolve(self, env, resolved_params):
    logging.log(1, 'Resolving ' + self.name)
    # TODO(byungchul): Support names in different modules.
    states = env['_current_module'].states
    if self.name not in states:
      did_you_mean = stl.levenshtein.closest_candidate(self.name, states.keys())
      raise NameError('Cannot find a state to expand: %s. Did you mean %s?' %
                      (self.name, did_you_mean))
    found = states[self.name]
    if len(self.param_values) != len(found.params):
      raise TypeError('Wrong number of parameters: %s. '
                      'Found %d params, expected %d params.' %
                      (found.name, len(found.params), len(self.param_values)))

    resolved_state = StateResolved(self.name, found)
    for v in self.param_values:
      resolved_state.resolved_params.append(v.Resolve(env, resolved_params))
    for v in found.values:
      if self.value == v:
        return StateValue(resolved_state, v)

    did_you_mean = stl.levenshtein.closest_candidate(self.value, found.values)
    raise NameError('Invalid value in state %s: %s. Did you mean %s?' %
                    (self.name, self.value, did_you_mean))


class Transition(stl.base.ParameterizedObject):
  """State transition spec.

  It defines pre_states, events, post_states. Optionally, it can have local
  variables and error_states. It can be parameterized. For example,

  transition tConnectTls(integer tlsId) {
    pre_states = [ sTlsState(tlsId).NotConnected ]
    events { rTlsClient -> TlsConnect(tlsId) -> rTlsServer }
    post_states = [ sTlsState(tlsId).Connected ]
  }

  Attributes:
    local_vars: List of local variables (stl.base.LocalVar)
    pre_states: List of state values either resolved (stl.state.StateValue) or
        resolved (stl.state.StateValueInTransition). These state values are used
        to determine whether or not this state transition can be executed.
    events: List of events either resolved (stl.base.Func) or unresolved
        (stl.event.EventInTransition) happending during this state transition.
        All function calls are sequentially executed and it aborts execution on
        any function returning False.
    post_states: List of state values either resolved (stl.tate.StateValue) or
        resolved (stl.state.StateValueInTransition). When all events finished
        with success, i.e returned True, these state values are used to
        determine the next state transition which must have a matched pre_state.
    error_states: List of state values either resolved (stl.state.StateValue) or
        resolved (stl.state.StateValueInTransition). When the execution is
        aborted, i.e any of event functions returned False, these state values
        are used to determine the next state transition which must have a
        matched pre_states. If None, error_states is same to pre_states which
        means no transition happened.
    expand: Expression to expand to a resolved transition, stl.state.Transition.
  """

  def __init__(self, name):
    stl.base.ParameterizedObject.__init__(self, name)
    self.local_vars = []
    self.pre_states = []
    self.events = []
    self.post_states = []
    self.error_states = []
    self.expand = None

  def __eq__(self, other):
    return (
        stl.base.ParameterizedObject.__eq__(self, other) and
        self.local_vars == other.local_vars and
        self.pre_states == other.pre_states and self.events == other.events and
        self.post_states == other.post_states and
        self.error_states == other.error_states and self.expand == other.expand)

  def __str__(self):
    if self.expand:
      return 'TRANSITION %s: %s' % (self.name, str(self.expand))
    return ('TRANSITION %s: p(%s) l(%s) i(%s) ev(%s) o(%s) e(%s)' %
            (self.name, stl.base.GetCSV(self.params),
             stl.base.GetCSV(self.local_vars), stl.base.GetCSV(self.pre_states),
             stl.base.GetCSV(self.events), stl.base.GetCSV(self.post_states),
             stl.base.GetCSV(self.error_states)))

  def IsResolved(self):
    """Whether or not this transition spec has been resolved."""
    return not self.params and not self.expand

  def Resolve(self, env, resolved_params):
    if self.IsResolved():
      return self
    logging.log(1, 'Resolving ' + self.name)
    if self.expand:
      if self.expand.name == self.name:
        raise NameError('Cannot expand self: ' + self.name)
      # TODO(byungchul): Support names in different modules.
      transitions = env['_current_module'].transitions
      if self.expand.name not in transitions:
        did_you_mean = stl.levenshtein.closest_candidate(
            self.expand.name, transitions.keys())
        raise NameError('Cannot find a transition to expand: %s.'
                        ' Did you mean %s?' %
                        (self.expand.name, did_you_mean))

      found = transitions[self.expand.name]
      if len(self.expand.values) != len(found.params):
        raise TypeError(
            'Wrong number of parameters: %s.'
            ' Found %d params, expected %d params.' %
            (found.name, len(found.params), len(self.expand.values)))

      new_resolved_params = {}
      for p, v in zip(found.params, self.expand.values):
        new_resolved_params[p.name] = v.Resolve(env, resolved_params)
      resolved = found.Resolve(env, new_resolved_params)
      resolved.name = self.name
      return resolved

    resolved = Transition(self.name)
    resolved.local_vars = self.local_vars
    new_resolved_params = resolved_params.copy()
    for v in self.local_vars:
      new_resolved_params[v.name] = v
    for s_list in self.pre_states:
      resolved.pre_states.append(
          [s.Resolve(env, new_resolved_params) for s in s_list])
    for e in self.events:
      resolved_e = e.Resolve(env, new_resolved_params)
      if not isinstance(resolved_e, stl.base.FuncWithContext):  # No action
        continue
      for r in env['_roles_to_test']:
        if resolved_e.context.source == r:
          resolved_e.context.test_source = True
          resolved.events.append(resolved_e)
          break
      for r in env['_roles_to_test']:
        if resolved_e.context.target == r:
          if resolved_e.context.test_source:
            raise RuntimeError('Invalid transition with 2 roles under test: '
                               '%s, %s' % (str(resolved_e.context.source),
                                           str(resolved_e.context.target)))
          resolved_e.context.test_source = False
          resolved.events.append(resolved_e)
          break
    for s in self.post_states:
      resolved.post_states.append(s.Resolve(env, new_resolved_params))
    for s in self.error_states:
      resolved.error_states.append(s.Resolve(env, new_resolved_params))
    return resolved

  def Run(self):
    """Execute this state transition.

    Returns:
      Whether or not all event functions returned True.
    """
    for e in self.events:
      if e.Run() is False:
        return False
    return True
