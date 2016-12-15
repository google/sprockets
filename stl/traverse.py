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

"""Algorithm for finding min-weight path which visits every edge in a graph.

General purpose graph traversal algorithm for finding the minimum weight
pseudo-Euler path which visits every edge in a strongly-connected graph at
least once.
"""

import collections
import networkx as nx


class Context(object):
  """Context object for running the Hungarian algorithm.

  Contains algorithm variables.

  Attributes:
    g: The complete bipartite graph we will find a maximum matching for.
    left: The set of left nodes.
    right: The set of right nodes.
    labels: Dictionary of vertex names to numeric algorithm label.
    num_matched: Current number of matched edges
    s: Set of left nodes in the augmenting tree
    t: Set of right nodes in the augmenting tree
    matches: Dictionary where matches[n] = m (and matches[m] = n) if n and m are
        currently matched.
    slack: Dictionary keyed on y, where slack[y] = min(for x in S: labels[x] +
        labels[y] - weight(x, y))
    slackx: Dictionary keyed on y, where slackx[y] is the node in right which
        gives y its current slack value.
    prev: Dictionary keyed on a node x in S, where prev[x] is the previous node
        in S along x's path in the augmenting tree.
  """

  def __init__(self):
    self.g = None
    self.left = None
    self.right = None
    self.labels = None
    self.num_matched = 0
    self.s = None
    self.t = None
    self.matches = None
    self.slack = None
    self.slackx = None
    self.prev = None

  def MaxBipartiteMatching(self, graph):
    """Find a maximum matching for a bipartite graph.

    This is O(n^3) implementation of the Hungarian method for complete bipartite
    matching problems.

    Args:
      graph: A networkx graph object, assumed to be bipartite.
    Returns:
      A dictionary keyed on node names in left to node names in right.
    """
    # Initialize algorithm variables
    self.g = nx.Graph(graph)
    # The data object will have data['bipartite'] == 0 if it is on the left.
    self.left = set(n for n, d in self.g.nodes(data=True) if not d['bipartite'])
    self.right = set(self.g) - self.left
    self.num_matched = 0
    self.s = set()
    self.t = set()
    self.matches = {}
    self.slack = {}
    self.slackx = {}
    self.prev = {}

    # Initialize labels to create a trivial equality subgraph.
    self.labels = {}
    for x in self.left:
      self.labels[x] = max([val['weight'] for val in self.g[x].values()])
    for y in self.right:
      self.labels[y] = 0

    # Augment until we have a perfect matching.
    while self.num_matched != len(self.left):
      self._Augment()
    # Return only the left -> right mappings.
    ret = {}
    for k in self.left:
      ret[k] = self.matches[k]
    return ret

  def _Augment(self):
    """Find an augmenting path starting from an unmatched node in |left|.

    Start with a root node in |left| and attempt to find an augmenting path
    starting from |root|. In order for a path to be augmenting, each edge in the
    path must have: weight(x, y) == labels[x] + labels[y]. The set of all edges
    which have this property is known as the "equality subgraph" for the current
    vertex labeling.

    In addition, an augmenting path must start with an unmatched edge and end
    with an unmatched edge; augmenting the path flips the matched-ness of each
    edge, so that the total number of matched edges increases by 1.

    If an augmenting path does not exist, we update the labels of all nodes in
    S and T to force new edges into the equality subgraph. Eventually, an
    augmenting path will be generated this way.
    """
    self.s = set()
    self.t = set()
    self.prev = {}
    queue = collections.deque()
    # Choose left node which is not yet matched
    root = list(self.left - set(self.matches.keys()))[0]
    queue.append(root)
    self.s.add(root)
    for y in self.right:
      self.slack[y] = self._CalcSlack(root, y)
      self.slackx[y] = root
    while True:
      # We will try to find an augmenting path.
      path_exists, x, y = self._FindAugmentingPath(queue)
      if path_exists:
        break
      self._UpdateLabels()
      queue.clear()
      # Try to find a newly-added edge in the equality subgraph.
      path_exists, x, y = self._FindAugmentingEdge(queue)
      if path_exists:
        break
    # Invert the augmenting path; the number of matched edges increases by 1.
    self._InvertPath(x, y)

  def _FindAugmentingPath(self, queue):
    """Find an augmenting path for the current labeling.

    Perform a BFS to find an augmenting path for the current labeling.

    Args:
      queue: Queue for performing BFS traversal.
    Returns:
      found: True if path was found.
      x: Left vertex of final path edge.
      y: Right vertex of final path edge.
    """
    while queue:
      x = queue.popleft()
      # Nodes in Right - T which share an edge with x in the equality subgraph.
      for y in self.right - self.t:
        if not self._InEqualitySubgraph(x, y):
          continue
        # Edge (x, y) is in the equality subgraph.
        if y not in self.matches:
          # Edge (x, y) is an unmatched edge terminating an augmenting path.
          return True, x, y
        # The edge is matched, but we will try
        self.t.add(y)
        queue.append(self.matches[y])
        self._AddToTree(self.matches[y], x)
    return False, None, None

  def _FindAugmentingEdge(self, queue):
    """Find a final edge for an augmenting path after updating labels.

    At least one new edge should have been added to the equality subgraph, so
    we check if any new edges will create an augmenting path.

    Args:
      queue: Queue for performing BFS traversal.
    Returns:
      found: True if path was found.
      x: Left vertex of final path edge.
      y: Right vertex of final path edge.
    """
    for y in (v for v in self.right - self.t if self.slack[v] == 0):
      # Edge (slackx[y], y) is now in the equality subgraph.
      if y not in self.matches:
        # y is a free node, so (slackx[y], y) terminates an augmenting path.
        return True, self.slackx[y], y
      self.t.add(y)
      if self.matches[y] not in self.s:
        queue.append(self.matches[y])
        self._AddToTree(self.matches[y], self.slackx[y])
    return False, None, None

  def _InvertPath(self, x, y):
    """Invert the augmenting path whose final edge is (x, y)."""
    self.num_matched += 1
    while True:
      if x in self.matches:
        ty = self.matches[x]
      self.matches[y] = x
      self.matches[x] = y
      if x not in self.prev:
        break
      y = ty
      x = self.prev[x]

  def _UpdateLabels(self):
    """Update labels to expand the equality subgraph.

    We will find the smallest slack value of a vertex in Right - T. The labels
    for vertices in S will decrease by slack, while the vertices in T increase
    by slack. This guarantees at least one vertex in Right will have a slack
    value of 0, thereby adding it to the equality subgraph.
    """
    delta = float('inf')
    for y in self.right - self.t:
      delta = min(delta, self.slack[y])
    for x in self.s:
      self.labels[x] -= delta
    for y in self.t:
      self.labels[y] += delta
    for y in self.right - self.t:
      self.slack[y] -= delta

  def _AddToTree(self, x, prevx):
    """Adds |x| to the current augmenting tree.

    x is a node which has already been matched to a node y in Right (which is
    itself connected to prevx via a non-matching edge in the equality subgraph).
    We indicate prevx comes before x in the tree so we can trace the path later.

    Args:
      x: Node which has already been matched to a node y in right
      prevx: Previous node in Left along the path.
    """
    self.s.add(x)
    self.prev[x] = prevx
    for y in self.right:
      # Find the minimum slack over all edges from nodes in S connected to y
      slack = self._CalcSlack(x, y)
      if slack < self.slack[y]:
        self.slack[y] = slack
        # Remember the node in S which brought the slack down.
        self.slackx[y] = x

  def _InEqualitySubgraph(self, x, y):
    """Return True if x and y are in the equality subgraph."""
    return self.g[x][y]['weight'] == self.labels[x] + self.labels[y]

  def _CalcSlack(self, x, y):
    """Calculate the slack for an edge (x, y)."""
    return self.labels[x] + self.labels[y] - self.g[x][y]['weight']


def MinEdgeCoverCircuit(graph, initial):
  """Calculates the minimum edge-covering circuit for a graph.

  The algorithm requires that the graph is strongly connected (every node can
  by reached by every other node). Begin by finding all nodes where the
  in-degree exceeds the out-degree (call this collection of nodes LEFT) and
  all nodes where the out-degree exceeds the in-degree (call this collection
  RIGHT). For each node in "left", we want to find N paths exiting that node,
  where N = in_degree - out_degree for that node. We split this node into N
  copies in LEFT (and do the same thing for each node in RIGHT). Each copy L in
  LEFT will eventually paired with a copy R in RIGHT. Each pairing's weight is
  defined as the minimum path weight from L to R. Thus, we create a bipartite
  matching which minimizes the total weight of all pairings. Once we have a
  final matching, we add "virtual" edges to the graph from L to R. The graph is
  now Eulerian (every node's in_degree == out_degree) and we can simply find an
  Eulerian circuit. We finish by substituting the virtual edges in the circuit
  with the actual paths.

  Args:
    graph: nx MultiGraph to examine.
    initial: initial vertex label.
  Returns:
    A list containing 3-tuples to distinguish edges in the original multi-graph:
    (source_node, target_node, edge_index)
  Raises:
    RuntimeError: if the graph is not properly formed.
  """
  if not nx.is_strongly_connected(graph):
    raise RuntimeError('Graph is not strongly connected.')
  left = [(n, x)
          for n in graph.nodes()
          for x in range(graph.in_degree(n) - graph.out_degree(n))]
  right = [(n, x)
           for n in graph.nodes()
           for x in range(graph.out_degree(n) - graph.in_degree(n))]
  b = nx.Graph()
  b.add_nodes_from(left, bipartite=0)
  b.add_nodes_from(right, bipartite=1)

  path_weights = nx.floyd_warshall(graph)
  edges = [(x, y, -path_weights[x[0]][y[0]]) for x in left for y in right]
  b.add_weighted_edges_from(edges)
  matches = Context().MaxBipartiteMatching(b)
  copy = graph.copy()
  for k, v in matches.items():
    sub_path = nx.shortest_path(
        graph, source=k[0], target=v[0], weight='weight')
    copy.add_edge(k[0], v[0], sub_path=sub_path)
  euler_circuit = list(nx.eulerian_circuit(copy, source=initial))

  for edge in copy.edges(data=True):
    edge[2]['visited'] = False

  expanded_circuit = []

  for circuit_edge in euler_circuit:
    s = circuit_edge[0]
    t = circuit_edge[1]
    # Find the first non-visited edge between s and t
    edge_index = 0
    for edge_index, edge in copy[s][t].items():
      if not edge['visited']:
        break
    edge['visited'] = True
    if 'sub_path' in edge:
      # This particular edge is a pseudo-edge between s and t
      # The path between s and t is a list of 2-tuples
      path = edge['sub_path']
      last = path[0]
      for node in path[1:]:
        # Find the smallest weight edge from 'last' to 'node'
        best_index = 0
        min_weight = float('inf')
        for k, v in graph[last][node].items():
          if v['weight'] < min_weight:
            min_weight = v['weight']
            best_index = k
        expanded_circuit.append((last, node, best_index))
        last = node
    else:
      expanded_circuit.append((s, t, edge_index))

  return expanded_circuit
