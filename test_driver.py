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

r"""Test Driver for Cast conformance test based on STL.

To run:
  $ python ./test_driver.py <manifest file>
"""

import argparse
import ast
import itertools
import logging
import os
import sys

import networkx as nx

import stl.graph
import stl.parser
import stl.traverse


def ParseArgs():
  """Returns the parsed command line args."""
  parser = argparse.ArgumentParser()

  class KeyValueAction(argparse.Action):
    """Convert "key1=value1 key2=value2" into the corresponding dict."""

    def __init__(self, option_strings, dest, nargs=None, **kwargs):
      super(KeyValueAction, self).__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
      key_value_pairs = [tuple(pair.split('=')) for pair in values.split()]
      setattr(namespace, self.dest, dict(key_value_pairs))

  parser.add_argument('manifest', help='The manifest (*.test) file to run.')
  parser.add_argument(
      '-a',
      '--manifest-args',
      help=('A series of space separated key=value pairs. '
            'Each instance of $key in the manifest file is replaced by value '
            'verbatim. In particular, if you want to pass a string, it must '
            'be explicitly quoted, e.g.: ip="0.0.0.0"'),
      action=KeyValueAction)
  parser.add_argument(
      '-d',
      '--debug',
      help='Increase logging verbosity to debug level.',
      action='store_true')

  return parser.parse_args()


def NewModuleDict():
  m = {}
  m['consts'] = {}
  m['roles'] = {}
  m['states'] = {}
  m['messages'] = {}
  m['events'] = {}
  m['transitions'] = {}
  return m


def AddManifestRootToPath(manifest_filename):
  """Adds the folder that the manifest resides in to the python sys.path."""
  manifest_root = os.path.abspath(os.path.dirname(manifest_filename))
  sys.path.append(manifest_root)
  logging.debug('Appended %s to the sys.path.', manifest_root)


def LoadManifest(manifest_filename, manifest_args):
  """Loads the manifest, replacing any specified manifest args."""
  with open(manifest_filename) as manifest_file:
    manifest = manifest_file.read()
    if manifest_args:
      for key, value in manifest_args.iteritems():
        logging.debug('Replacing $%s with %s', key, value)
        manifest = manifest.replace('${}'.format(key), value)

  logging.debug('Manifest file with subsitutions:\n %s', manifest)

  try:
    return ast.literal_eval(manifest)
  except SyntaxError:
    logging.exception('You may have forgotten to pass '
                      '--manifest-args="key=value" to substitute for $key')
    sys.exit(3)


def ParseStl(stl_file, modules):
  m = NewModuleDict()
  stl.parser.Parse(stl_file, m)
  # TODO(byungchul): Support module in multiple files.
  modules[m['name']] = m


def LoadModules(manifest, test_manifest_filename):
  """Builds transition graph for each module."""
  modules = {}
  if 'stl_files' in manifest:
    for f in manifest['stl_files']:
      f = os.path.join(os.path.dirname(test_manifest_filename), f)
      ParseStl(f, modules)
  logging.debug(str(modules))
  return modules


def FillInModuleRoles(modules, manifest):
  """Fills in role information in |modules|."""
  for r in manifest['roles']:
    module, name = r['role'].split('::', 1)
    if name not in modules[module]['roles']:
      raise NameError("Cannot find a role in module '%s': %s" % (module, name))
    role = modules[module]['roles'][name]
    for v in r:
      if v == 'role':
        continue
      role[v] = r[v]


def GetRolesToTest(modules, manifest):
  """Returns the roles to test."""
  roles_to_test = []
  for r in manifest['test']:
    module, name = r.split('::', 1)
    if name not in modules[module]['roles']:
      raise NameError("Cannot find a role in module '%s': %s" % (module, name))
    roles_to_test.append(modules[module]['roles'][name])
  logging.debug(str(roles_to_test))

  if not roles_to_test:
    raise RuntimeError('No roles to test')
  return roles_to_test


def ResolveTransitions(modules, roles_to_test):
  """Resolves transitions, if any."""
  env = {}
  env['_modules'] = modules
  env['_roles_to_test'] = roles_to_test
  transitions = {}
  for m in modules.itervalues():
    env['_current_module'] = m
    m['resolved_transitions'] = {}
    for t in m['transitions'].itervalues():
      if t.params:
        continue
      resolved_t = t.Resolve(env, {})
      if not resolved_t.IsResolved():
        raise RuntimeError('Cannot resolve transition: ' + resolved_t.name)
      if resolved_t.name in transitions:
        raise NameError('Duplicated transitions: ' + resolved_t.name)
      if resolved_t.events:
        transitions[resolved_t.name] = resolved_t

  logging.debug(str(transitions))
  return transitions


def InitializeStates(transitions):
  """Gathers resolved states with initial values."""
  states = {}
  for t in transitions.itervalues():
    pre_states = list(itertools.chain(*t.pre_states))
    for i in pre_states + t.post_states + t.error_states:
      key = str(i.state)
      if key not in states:
        states[key] = i.state
      elif i.state != states[key]:
        raise RuntimeError('Duplicated states: ' + str(i.state))

  logging.debug(str(states))
  return states


def TraverseGraph(transitions, states):
  """Does that actual graph traversal, going through all transisitons."""
  transition_graph, initial_vertex = stl.graph.BuildTransitionGraph(transitions,
                                                                    states)

  # TODO(seantopping): Separate visualization from traversal algorithm.
  a_graph = nx.nx_agraph.to_agraph(transition_graph)
  a_graph.layout(prog='dot')
  for node in a_graph.nodes():
    node.attr['style'] = 'filled'
    node.attr['fillcolor'] = 'grey'
  a_graph.draw('graph.png')

  circuit_stack = stl.traverse.MinEdgeCoverCircuit(transition_graph,
                                                   initial_vertex)
  circuit_stack.reverse()

  success = True
  while circuit_stack:
    edge = circuit_stack.pop()
    source, target, edge_i = edge
    s = a_graph.get_node(source)
    t = a_graph.get_node(target)
    e = a_graph.get_edge(source, target, key=edge_i)

    e.attr['color'] = 'green'
    a_graph.draw('graph.png')
    attr = transition_graph[source][target][edge_i]
    transition = attr['transition']
    if attr['weight'] != float('inf'):
      if transition.Run():
        logging.info('\033[92m[ PASSED ]\033[0m: %s', transition.name)
        s.attr['fillcolor'] = 'grey'
        t.attr['fillcolor'] = 'green'
        e.attr['color'] = 'blue'
        a_graph.draw('graph.png')
        continue
      else:
        logging.error('\033[91m[ FAILED ]\033[0m: %s', transition.name)
        success = False
        attr['weight'] = float('inf')
    error_vertex_id = attr['error_vertex_id']
    error_vertex = a_graph.get_node(error_vertex_id)
    e.attr['color'] = 'red'
    s.attr['fillcolor'] = 'grey'
    error_vertex.attr['fillcolor'] = 'green'
    a_graph.draw('graph.png')
    new_path = nx.shortest_path(
        transition_graph, error_vertex_id, target, weight='weight')
    path_stack = []
    for i in range(len(new_path) - 1):
      s = new_path[i]
      t = new_path[i + 1]
      # Get the edge-index with the smallest weight
      multi_edge = transition_graph[s][t]
      min_weight = float('inf')
      min_edge_i = 0
      for key, value in multi_edge.iteritems():
        if value['weight'] < min_weight:
          min_weight = value['weight']
          min_edge_i = key
      if transition_graph[s][t][min_edge_i]['weight'] == float('inf'):
        return success
      path_stack.append((s, t, min_edge_i))
    # TODO(seantopping): Implement a better error recovery algorithm.
    circuit_stack.extend(reversed(path_stack))
  return success


def Main():
  """Test driver main function."""
  args = ParseArgs()

  if args.debug:
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
  else:
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)

  AddManifestRootToPath(args.manifest)

  manifest = LoadManifest(args.manifest, args.manifest_args)

  modules = LoadModules(manifest, args.manifest)

  FillInModuleRoles(modules, manifest)

  roles_to_test = GetRolesToTest(modules, manifest)

  transitions = ResolveTransitions(modules, roles_to_test)

  states = InitializeStates(transitions)

  success = TraverseGraph(transitions, states)
  return success


if __name__ == '__main__':
  sys.exit(0 if Main() else 1)
