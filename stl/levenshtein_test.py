"""Tests for levenshtein."""

import unittest

import stl.levenshtein


class LevenshteinTest(unittest.TestCase):

  def testEmpty(self):
    a = ''
    b = ''
    expected_distance = 0
    actual_distance = stl.levenshtein.distance(a, b)
    self.assertEqual(expected_distance, actual_distance)

  def testIdentical(self):
    a = 'xxxxx'
    b = 'xxxxx'
    expected_distance = 0
    actual_distance = stl.levenshtein.distance(a, b)
    self.assertEqual(expected_distance, actual_distance)

  def testIdentical_CaseInsensitive(self):
    a = 'xxxxx'
    b = 'xXxXx'
    expected_distance = 0
    actual_distance = stl.levenshtein.distance(a, b)
    self.assertEqual(expected_distance, actual_distance)

  def testOneLetter(self):
    a = 'a'
    b = 'b'
    expected_distance = 1
    actual_distance = stl.levenshtein.distance(a, b)
    self.assertEqual(expected_distance, actual_distance)

  def testAllDifferent_SameLength(self):
    a = 'abcde'
    b = 'vwxyz'
    expected_distance = 5
    actual_distance = stl.levenshtein.distance(a, b)
    self.assertEqual(expected_distance, actual_distance)

  def testAllDifferent_DifferentLength(self):
    a = 'abc'
    b = 'vwxyz'
    expected_distance = 5
    actual_distance = stl.levenshtein.distance(a, b)
    self.assertEqual(expected_distance, actual_distance)

  def testSomeDifferent_DifferentLength(self):
    a = 'abcd'
    b = 'axcxe'
    expected_distance = 3
    actual_distance = stl.levenshtein.distance(a, b)
    self.assertEqual(expected_distance, actual_distance)

  def testClosestCandidate_NoCandidates(self):
    with self.assertRaises(ValueError):
      stl.levenshtein.closest_candidate('', [])

  def testClosestCandidate_OneCadidate_ExactMatch(self):
    target = 'abc'
    candidates = ['abc']
    expected_candidate = 'abc'
    actual_candidate = stl.levenshtein.closest_candidate(target, candidates)
    self.assertEqual(expected_candidate, actual_candidate)

  def testClosestCandidate_OneCandiate_NoExactMatch(self):
    target = 'abc'
    candidates = ['xyz']
    expected_candidate = 'xyz'
    actual_candidate = stl.levenshtein.closest_candidate(target, candidates)
    self.assertEqual(expected_candidate, actual_candidate)

  def testClosestCandidate_MultipleCandidates_ExactMatch(self):
    target = 'abc'
    candidates = ['xyz', 'jkl', 'abcde', 'abc']
    expected_candidate = 'abc'
    actual_candidate = stl.levenshtein.closest_candidate(target, candidates)
    self.assertEqual(expected_candidate, actual_candidate)

  def testClosestCandidate_MultipleCandidates_NoExactMatch(self):
    target = 'abc'
    candidates = ['xyz', 'jkl', 'abcde', 'abq']
    expected_candidate = 'abq'
    actual_candidate = stl.levenshtein.closest_candidate(target, candidates)
    self.assertEqual(expected_candidate, actual_candidate)


if __name__ == '__main__':
  unittest.main()
