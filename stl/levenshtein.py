"""Module for calculating the Levenshtein distance bewtween two strings."""

def closest_candidate(target, candidates):
  """Returns the candidate that most closely matches |target|."""
  return min(candidates, key=lambda candidate: distance(target, candidate))


def distance(a, b):
  """Returns the case-insensitive Levenshtein edit distance between |a| and |b|.

  The Levenshtein distance is a metric for measuring the difference between
  two strings. If |a| == |b|, the distance is 0. It is roughly the number
  of insertions, deletions, and substitutions needed to convert |a| -> |b|.

  This distance is at most the length of the longer string.
  This distance is 0 iff the strings are equal.

  Examples:
    levenshtein_distance("cow", "bow") == 1
    levenshtein_distance("cow", "bowl") == 2
    levenshtein_distance("cow", "blrp") == 4

  See https://en.wikipedia.org/wiki/Levenshtein_distance for more background.

  Args:
    a: A string
    b: A string

  Returns:
    The Levenshtein distance between the inputs.
  """
  a = a.lower()
  b = b.lower()

  if len(a) == 0:
    return len(b)

  if len(b) == 0:
    return len(a)

  # Create 2D array[len(a)+1][len(b)+1]
  #    | 0 b1 b2 b3 .. bN
  # ---+-------------------
  #  0 | 0  1  2  3 ..  N
  # a1 | 1  0  0  0 ..  0
  # a2 | 2  0  0  0 ..  0
  # a3 | 3  0  0  0 ..  0
  # .. | .  .  .  . ..  .
  # aM | M  0  0  0 ..  0
  dist = [[0 for _ in xrange(len(b)+1)] for _ in xrange(len(a)+1)]
  for i in range(len(a)+1):
    dist[i][0] = i
  for j in range(len(b)+1):
    dist[0][j] = j

  # Build up the dist[][] table dynamically. At the end, the Levenshtein
  # distance between |a| and |b| will be in the bottom right cell.
  for i in range(1, len(a)+1):
    for j in range(1, len(b)+1):
      cost = 0 if a[i-1] == b[j-1] else 1
      dist[i][j] = min(dist[i-1][j] + 1,
                       dist[i][j-1] + 1,
                       dist[i-1][j-1] + cost)

  return dist[-1][-1]
