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

"""Module for state transition graph."""

import itertools
import logging
import networkx as nx


class StateVertex(object):
  """A vertex in state transition graph.

  It represents a state consisting of instances of state.StateValue.

  Attributes:
    state_list: List of state.StateValue's.
    id: A unique integer identifier for this vertex.
  """
  next_id = 0

  def __init__(self, state_list):
    self.state_list = sorted(state_list, key=str)
    self._edges = []
    self._visited = False
    self.id = 's%d' % StateVertex.GetNextId()

  def __str__(self):
    return str(self.state_list)

  def __repr__(self):
    return str(self)

  def __hash__(self):
    return hash(str(self))

  def __eq__(self, that):
    return str(self) == str(that)

  def __ne__(self, that):
    return not self == that

  @property
  def edges(self):
    return self._edges

  @staticmethod
  def GetNextId():
    next_id = StateVertex.next_id
    StateVertex.next_id += 1
    return next_id

  def AppendStateListNotExist(self, state_list):
    """Append state.StateValue's only when they are not already in."""
    for s in state_list:
      if not self._HasAssignedState(s.state):
        self.state_list.append(s)
    self.state_list.sort(key=str)

  def AddEdge(self, edge):
    self._edges.append(edge)

  def GetMatchingTransitions(self, transitions):
    """Return a list of state.Transition's compatible to this state.

    A transition is compatible to this state when the transition's pre_states
    is comparible with this state, i.e. the transition can be executed from
    this state.

    Args:
      transitions: List of state.Transitions among which it finds ones
          compatible to this state.
    Returns:
      List of state.Transition's compatible to this state.
    """
    return [t for t in transitions if self._MatchWithTransition(t)]

  def _MatchWithTransition(self, trans):
    """Whether it matches any of the transition's pre_state configurations."""

    def _MatchHelper(pre_states):
      for s in pre_states:
        if not self._MatchWithState(s):
          return False
      return True

    return any(
        _MatchHelper(list(pre_states))
        for pre_states in itertools.product(*trans.pre_states))

  def _MatchWithState(self, state):
    """Whether it doesn't have a state value not compatible with |state|."""
    for s in self.state_list:
      if state.state == s.state and state.value != s.value:
        logging.log(2, 'Not matched: %s, %s', str(state), str(s))
        return False
    return True

  def _HasAssignedState(self, state):
    """Whether StateResolved |state| already has an assigned value in |self|."""
    for s in self.state_list:
      if state == s.state:
        return True
    return False

  def Run(self):
    if not self._visited:
      self._visited = True
      self._RunInternal()
      self._visited = False

  def _RunInternal(self):
    """Run events in DFS manner."""
    for e in self._edges:
      if not e.transition.Run():
        logging.error('\033[91m[ FAILED ]\033[0m: %s', e.transition)
        continue
      logging.info('\033[92m[ PASSED ]\033[0m: %s', e.transition)
      e.output_vertex.Run()


class TransitionEdge(object):
  """An edge of 2 graph.StateVertex's in state transition graph.

  Attributes:
    transition: state.Transition in state transition spec.
    output_vertext: graph.StateVertex matching with |transition|'s post_states.
    error_vertext: graph.StateVertex matching with |transition|'s error_states.
  """

  def __init__(self, trans, output_vertex, error_vertex):
    self.transition = trans
    self.output_vertex = output_vertex
    self.error_vertex = error_vertex

  def __str__(self):
    return str(self.transition)


def _AddVertex(graph, vertex_list, vertex):
  if vertex not in graph:
    graph[vertex] = vertex
    vertex_list.append(vertex)
  return graph[vertex]


def BuildTransitionGraph(transitions, states):
  """Build a transition graph based on transitions and states."""
  initial_vertex = StateVertex([s.InitialValue() for s in states.values()])
  used_transitions = {}  # To check transitions not used.

  graph = {}
  graph[initial_vertex] = initial_vertex
  vertexes = [initial_vertex]
  for v in vertexes:
    matched_transitions = v.GetMatchingTransitions(transitions.values())
    logging.log(3, 'matched transitions for %s: %s', v, matched_transitions)
    for t in matched_transitions:
      trans_key = str(t)
      if trans_key in used_transitions:
        used_transitions[trans_key].append(v)
      else:
        used_transitions[trans_key] = [v]

      output_v = StateVertex(t.post_states)
      output_v.AppendStateListNotExist(v.state_list)
      output_v = _AddVertex(graph, vertexes, output_v)

      error_v = None
      if t.error_states:
        error_v = StateVertex(t.error_states)
        error_v.AppendStateListNotExist(v.state_list)
        error_v = _AddVertex(graph, vertexes, error_v)

      edge = TransitionEdge(t, output_v, error_v)
      logging.debug('Adding edge %s from %s to %s', edge, v, output_v)
      v.AddEdge(edge)

  nx_graph = nx.MultiDiGraph()
  edge_labels = {}
  for v in vertexes:
    for e in v.edges:
      edge_label = str(e.transition)
      if edge_label not in edge_labels:
        edge_labels[edge_label] = e.transition.name
      error_vertex_id = v.id
      if e.error_vertex:
        error_vertex_id = e.error_vertex.id
      nx_graph.add_edge(
          v.id,
          e.output_vertex.id,
          label=edge_labels[edge_label],
          transition=e.transition,
          error_vertex_id=error_vertex_id,
          weight=1)

  return nx_graph, initial_vertex.id
