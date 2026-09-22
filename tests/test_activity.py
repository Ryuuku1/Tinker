"""Synthetic trace normalization tests, never evidence of live host behavior."""
import hashlib
import importlib
from pathlib import Path
import tempfile
import unittest


class ActivityTests(unittest.TestCase):
    def setUp(self):
        self.grader = importlib.import_module('evals.grade')

    def activity(self, pairs, complete=True):
        return {'complete': complete, 'lines': [1, max(1, len(pairs))],
                'events': [{'event': event, 'actor': actor, 'lines': [i, i]}
                           for i, (event, actor) in enumerate(pairs, 1)]}

    def measure(self, pairs, complete=True):
        self.assertTrue(hasattr(self.grader, 'measure_activity'),
                        'Concurrency must be derived from attributed lifecycle events')
        return self.grader.measure_activity(self.activity(pairs, complete), max(1, len(pairs)))

    def test_three_sequential_specialists_are_not_a_budget_violation(self):
        pairs = [(event, actor) for actor in ('engineer', 'tester', 'reviewer')
                 for event in ('start_helper', 'result', 'stop_helper')]
        counts = self.measure(pairs)
        self.assertEqual(counts['workers_total'], 3)
        self.assertEqual(counts['peak_active_helpers'], 1)
        self.assertEqual(counts['returned_workers'], 3)

    def test_lead_and_helper_writing_overlap_counts_as_two(self):
        counts = self.measure([('start_helper', 'engineer'), ('start_write', 'lead'),
                               ('start_write', 'engineer')])
        self.assertEqual(counts['peak_active_writers'], 2)

    def test_unknown_termination_does_not_free_capacity(self):
        counts = self.measure([('start_helper', 'one'), ('start_helper', 'two'),
                               ('start_helper', 'replacement')])
        self.assertEqual(counts['peak_active_helpers'], 3)
        self.assertEqual(counts['returned_workers'], 0)

    def test_result_does_not_stop_an_active_helper(self):
        counts = self.measure([('start_helper', 'one'), ('result', 'one'),
                               ('start_helper', 'two')])
        self.assertEqual(counts['peak_active_helpers'], 2)

    def test_reused_identity_counts_as_one_worker_with_a_returned_result(self):
        counts = self.measure([('start_helper', 'one'), ('result', 'one'),
                               ('stop_helper', 'one'), ('start_helper', 'one'),
                               ('result', 'one'), ('stop_helper', 'one')])
        self.assertEqual(counts['workers_total'], 1)
        self.assertEqual(counts['returned_workers'], 1)

    def test_incomplete_trace_cannot_establish_absence(self):
        self.assertEqual(self.grade_partial([], 'peak_active_writers', 1), 'fixture-not-verified')

    def grade_partial(self, pairs, field, limit):
        with tempfile.TemporaryDirectory() as tmp:
            raw = b'Synthetic partial lifecycle source\n' * max(1, len(pairs))
            Path(tmp, 'trace.txt').write_bytes(raw)
            case = {'id': 'partial', 'rules': [{'field': field, 'op': 'lte', 'value': limit}]}
            record = {'case_id': 'partial', 'origin': 'synthetic',
                      'source': {'path': 'trace.txt', 'sha256': hashlib.sha256(raw).hexdigest()},
                      'observations': {}, 'activity': self.activity(pairs, complete=False)}
            return self.grader.grade(case, record, tmp)['status']

    def test_incomplete_trace_preserves_proven_helper_violation(self):
        pairs = [('start_helper', str(i)) for i in range(3)]
        self.assertEqual(self.grade_partial(pairs, 'peak_active_helpers', 2), 'fixture-failed')

    def test_incomplete_trace_preserves_proven_writing_overlap(self):
        pairs = [('start_helper', 'one'), ('start_write', 'one'), ('start_write', 'lead')]
        self.assertEqual(self.grade_partial(pairs, 'peak_active_writers', 1), 'fixture-failed')

    def test_invalid_lifecycle_is_rejected(self):
        self.assertTrue(hasattr(self.grader, 'measure_activity'))
        for pairs in ([('stop_helper', 'missing')], [('result', 'missing')],
                      [('start_helper', 'lead')], [('start_write', 'missing')],
                      [('start_helper', 'one'), ('start_helper', 'one')],
                      [('start_helper', 'one'), ('start_write', 'one'), ('stop_helper', 'one')]):
            with self.subTest(pairs=pairs), self.assertRaises(ValueError):
                self.measure(pairs)

    def test_bad_provenance_is_not_a_measurement(self):
        self.assertTrue(hasattr(self.grader, 'measure_activity'))
        activity = self.activity([('start_helper', 'one')])
        activity['events'][0]['lines'] = [2, 2]
        with self.assertRaises(ValueError):
            self.grader.measure_activity(activity, 1)

    def test_grade_uses_events_and_rejects_scalar_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = b'Synthetic lifecycle source\n' * 3
            Path(tmp, 'trace.txt').write_bytes(raw)
            case = {'id': 'capacity', 'rules': [
                {'field': 'peak_active_helpers', 'op': 'lte', 'value': 2}]}
            record = {'case_id': 'capacity', 'origin': 'synthetic',
                      'source': {'path': 'trace.txt', 'sha256': hashlib.sha256(raw).hexdigest()},
                      'observations': {}, 'activity': self.activity([
                          ('start_helper', 'one'), ('start_helper', 'two'),
                          ('start_helper', 'three')])}
            self.assertEqual(self.grader.grade(case, record, tmp)['status'], 'fixture-failed')
            record['observations']['peak_active_helpers'] = {'value': 0, 'lines': [1, 3]}
            self.assertEqual(self.grader.grade(case, record, tmp)['status'], 'invalid')

    def test_missing_activity_is_not_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = b'Synthetic source\n'
            Path(tmp, 'trace.txt').write_bytes(raw)
            case = {'id': 'capacity', 'rules': [
                {'field': 'peak_active_writers', 'op': 'lte', 'value': 1}]}
            record = {'case_id': 'capacity', 'origin': 'synthetic',
                      'source': {'path': 'trace.txt', 'sha256': hashlib.sha256(raw).hexdigest()},
                      'observations': {}}
            self.assertEqual(self.grader.grade(case, record, tmp)['status'], 'fixture-not-verified')
