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
import stl.levenshtein
import stl.parser
import stl.traverse


def ParseArgs():
  """Returns the parsed command line args."""
  parser = argparse.ArgumentParser()

  parser.add_argument('manifest', help='The manifest (*.test) file to run.')
  parser.add_argument(
      '-a',
      '--manifest-args',
      nargs='*',
      help=('A list of <key>=<value> pairs. '
            'Each instance of $<key> in the manifest file is replaced by '
            '<value> verbatim. In particular, if you want to pass a string, it '
            'must be explicitly quoted, e.g.: ip="0.0.0.0"'))
  parser.add_argument(
      '-d',
      '--debug',
      help='Increase logging verbosity to debug level.',
      action='store_true')
  parser.add_argument(
      '-g',
      '--graph',
      help='Continuously draw the state graph image to the specified file.')

  return parser.parse_args()


def AddManifestRootToPath(manifest_filename):
  """Adds the folder that the manifest resides in to the python sys.path."""
  manifest_root = os.path.abspath(os.path.dirname(manifest_filename))
  sys.path.append(manifest_root)
  logging.debug('Appended %s to the sys.path.', manifest_root)


def LoadManifest(manifest_filename, manifest_arg_dict):
  """Loads the manifest, replacing any specified manifest args."""
  with open(manifest_filename) as manifest_file:
    manifest = manifest_file.read()
    for key, value in manifest_arg_dict.items():
      logging.debug('Replacing $%s with %s', key, value)
      manifest = manifest.replace('${}'.format(key), value)

  logging.debug('Manifest file with subsitutions:\n %s', manifest)

  try:
    return ast.literal_eval(manifest)
  except SyntaxError:
    logging.exception('You may have forgotten to pass '
                      '--manifest-args="key=value" to substitute for $key')
    sys.exit(3)


def ParseStl(stl_file, global_env):
  stl.parser.Parse(stl_file, global_env)


def LoadModules(manifest, test_manifest_filename, global_env):
  """Builds transition graph for each module."""
  global_env = {'modules': {}}
  manifest_root = os.path.abspath(os.path.dirname(test_manifest_filename))
  if 'import_paths' in manifest:
    for f in manifest['import_paths']:
      sys.path.append(os.path.join(manifest_root, f))
  if 'stl_files' in manifest:
    for f in manifest['stl_files']:
      f = os.path.join(os.path.dirname(test_manifest_filename), f)
      ParseStl(f, global_env)
  logging.debug(str(global_env['modules']))
  return global_env['modules']


def FillInModuleRoles(modules, manifest):
  """Fills in role information in |modules|."""
  for r in manifest['roles']:
    module, name = r['role'].split('::', 1)
    if name not in modules[module].roles:
      raise NameError("Cannot find a role in module '%s': %s" % (module, name))
    role = modules[module].roles[name]
    for v in r:
      if v == 'role':
        continue
      role[v] = r[v]


def FillInConstants(modules, manifest):
  """Fills in constant information in |modules|."""
  if 'constants' not in manifest:
    return
  for key, val in manifest['constants'].items():
    module, name = key.split('::', 1)
    if module not in modules:
      did_you_mean = stl.levenshtein.closest_candidate(module, modules.keys())
      raise NameError('Cannot find module "%s" referenced by "%s".'
                      ' Did you mean %s?' % (module, key, did_you_mean))
    if name not in modules[module].consts:
      did_you_mean = stl.levenshtein.closest_candidate(
          name, sum((m.consts.keys() for m in modules.values()), []))
      if did_you_mean in modules[module].consts:
        raise NameError('Cannot find a constant in module "%s": %s.'
                        ' Did you mean %s?' % (module, name, did_you_mean))
      else:
        did_you_mean_module = next(m_name for m_name, m in modules.items()
                                   if did_you_mean in m.consts)
        raise NameError('Cannot find a constant in module "%s": %s.'
                        ' Did you mean %s::%s?' %
                        (module, name, did_you_mean_module, did_you_mean))

    const = modules[module].consts[name]
    if const.value is not None:
      raise RuntimeError("Const '%s' in module '%s' already has a value: %s" %
                         (const.name, module, str(const.value)))
    const.value = val
  # Check that all consts are defined.
  for module in modules.values():
    for const in module.consts.values():
      if const.value is None:
        raise RuntimeError("Const '%s' in module '%s' is undefined." %
                           (const.name, module.name))


def GetRolesToTest(modules, manifest):
  """Returns the roles to test."""
  roles_to_test = []
  for r in manifest['test']:
    module, name = r.split('::', 1)
    if name not in modules[module].roles:
      did_you_mean = stl.levenshtein.closest_candidate(
          name, sum((m.roles.keys() for m in modules.values()), []))
      if did_you_mean in modules[module].roles:
        raise NameError('Cannot find a role in module "%s": %s.'
                        ' Did you mean %s?' % (module, name, did_you_mean))
      else:
        did_you_mean_module = next(m_name for m_name, m in modules.items()
                                   if did_you_mean in m.roles)
        raise NameError('Cannot find a role in module "%s": %s.'
                        ' Did you mean %s::%s?' %
                        (module, name, did_you_mean_module, did_you_mean))
    roles_to_test.append(modules[module].roles[name])
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
  for m in modules.values():
    env['_current_module'] = m
    for t in m.transitions.values():
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
  for t in transitions.values():
    pre_states = list(itertools.chain(*t.pre_states))
    for i in pre_states + t.post_states + t.error_states:
      key = str(i.state)
      if key not in states:
        states[key] = i.state
      elif i.state != states[key]:
        raise RuntimeError('Duplicated states: ' + str(i.state))

  logging.debug(str(states))
  return states


class Visualizer(object):

  def __init__(self, transition_graph, graph_file=None):
    self.graph_file = graph_file
    self.a_graph = nx.nx_agraph.to_agraph(transition_graph)
    self.a_graph.layout(prog='dot')
    for node in self.a_graph.nodes():
      node.attr['style'] = 'filled'
      node.attr['fillcolor'] = 'grey'
    if self.graph_file:
      self.a_graph.draw(self.graph_file)

  def TransitionRunning(self, edge):
    # |edge| is a 3-tuple (source_name, target_name, edge_index). Since we're
    # traversing a multi-graph, there can be multiple edges between the same
    # pair of vertices, so |edge_index| specifies which edge we should color
    # among the collection of edges from |source_name| to |target_name|.
    self.a_graph.get_edge(edge[0], edge[1], key=edge[2]).attr['color'] = 'green'
    self.a_graph.draw(self.graph_file)

  def TransitionPassed(self, edge):
    self.a_graph.get_node(edge[0]).attr['fillcolor'] = 'grey'
    self.a_graph.get_node(edge[1]).attr['fillcolor'] = 'green'
    self.a_graph.get_edge(edge[0], edge[1], key=edge[2]).attr['color'] = 'blue'
    self.a_graph.draw(self.graph_file)

  def TransitionFailed(self, edge, error_vertex_id):
    self.a_graph.get_node(edge[0]).attr['fillcolor'] = 'grey'
    self.a_graph.get_edge(edge[0], edge[1], key=edge[2]).attr['color'] = 'red'
    self.a_graph.get_node(error_vertex_id).attr['fillcolor'] = 'green'
    self.a_graph.draw(self.graph_file)


def TraverseGraph(transitions, states, args=None):
  """Does that actual graph traversal, going through all transitions."""
  transition_graph, initial_vertex = stl.graph.BuildTransitionGraph(
      transitions, states)

  graph_file = None
  if args:
    graph_file = args.graph
  visualizer = Visualizer(transition_graph, graph_file)

  circuit_stack = stl.traverse.MinEdgeCoverCircuit(transition_graph,
                                                   initial_vertex)
  circuit_stack.reverse()

  success = True
  while circuit_stack:
    edge = circuit_stack.pop()
    source, target, edge_i = edge
    attr = transition_graph[source][target][edge_i]
    transition = attr['transition']
    visualizer.TransitionRunning(edge)
    if attr['weight'] != float('inf'):
      logging.info('\033[93m[ RUNNING ]\033[0m: %s', transition.name)
      if transition.Run():
        logging.info('\033[92m[ PASSED ]\033[0m: %s', transition.name)
        visualizer.TransitionPassed(edge)
        continue
      else:
        logging.error('\033[91m[ FAILED ]\033[0m: %s', transition.name)
        success = False
        attr['weight'] = float('inf')
    error_vertex_id = attr['error_vertex_id']
    visualizer.TransitionFailed(edge, error_vertex_id)
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
      for key, value in multi_edge.items():
        if value['weight'] < min_weight:
          min_weight = value['weight']
          min_edge_i = key
      if transition_graph[s][t][min_edge_i]['weight'] == float('inf'):
        return success
      path_stack.append((s, t, min_edge_i))
    # TODO(seantopping): Implement a better error recovery algorithm.
    circuit_stack.extend(reversed(path_stack))
  return success


def RunTest(manifest_filename, manifest_arg_dict, args=None):
  AddManifestRootToPath(manifest_filename)

  manifest = LoadManifest(manifest_filename, manifest_arg_dict)

  global_env = {}
  modules = LoadModules(manifest, manifest_filename, global_env)

  if 'error' in global_env and global_env['error']:
    return False

  FillInModuleRoles(modules, manifest)
  FillInConstants(modules, manifest)

  roles_to_test = GetRolesToTest(modules, manifest)

  transitions = ResolveTransitions(modules, roles_to_test)

  states = InitializeStates(transitions)

  return TraverseGraph(transitions, states, args)


def Main():
  """Test driver main function."""
  args = ParseArgs()

  if args.debug:
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
  else:
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)

  manifest_filename = args.manifest
  manifest_arg_dict = {}
  for arg in args.manifest_args:
    key, value = arg.split('=', 1)
    manifest_arg_dict[key] = value

  return RunTest(manifest_filename, manifest_arg_dict, args)


if __name__ == '__main__':
  sys.exit(0 if Main() else 1)
