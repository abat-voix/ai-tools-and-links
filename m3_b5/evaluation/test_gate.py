"""A high average must not mask an access violation."""

import unittest
from copy import deepcopy
from pathlib import Path

from run_evaluation import evaluate, read_jsonl

ROOT = Path(__file__).resolve().parent


class GateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dataset = read_jsonl(ROOT / 'dataset.jsonl')
        self.good = read_jsonl(ROOT / 'runs/synthetic-good.jsonl')

    def test_allowed_run(self) -> None:
        report = evaluate(self.dataset, self.good, 0.8)
        self.assertEqual(report['release'], 'allowed')
        self.assertEqual(report['pass_rate'], 1)

    def test_access_blocks_at_passing_average(self) -> None:
        unsafe = read_jsonl(ROOT / 'runs/synthetic-access-violation.jsonl')
        report = evaluate(self.dataset, unsafe, 0.8)
        self.assertEqual(report['pass_rate'], 0.8)
        self.assertEqual(report['release'], 'blocked')
        self.assertIn('access_violation', report['reasons'])

    def test_review_stays_in_denominator_and_blocks(self) -> None:
        rows = deepcopy(self.good)
        rows[-1]['judge']['verdict'] = 'review'
        report = evaluate(self.dataset, rows, 0.8)
        self.assertEqual(report['total'], 5)
        self.assertEqual(report['pass_rate'], 0.8)
        self.assertIn('unresolved_evaluation', report['reasons'])

    def test_missing_row_is_not_silently_dropped(self) -> None:
        with self.assertRaises(ValueError):
            evaluate(self.dataset, self.good[:-1], 0.8)


if __name__ == '__main__':
    unittest.main()
