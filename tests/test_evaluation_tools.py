import unittest
from copy import deepcopy
from unittest.mock import patch

from fursa.evaluate import evaluate
from fursa.reporting import compare_reports


class EvaluationToolsTests(unittest.TestCase):
    def test_comparison_checks_provenance_and_returns_observed_differences(self):
        report = evaluate()
        same = compare_reports(report, deepcopy(report))
        self.assertEqual(same["changed_rankings"], [])
        self.assertTrue(all(value == 0 for value in same["metric_deltas"].values()))
        with patch("fursa.evaluate.Tfidf.rank", return_value=[]):
            changed = evaluate()
        observed = compare_reports(report, changed)
        self.assertEqual(observed["changed_rankings"][0]["id"], "q01")
        self.assertLess(observed["metric_deltas"]["mean_recall_at_3"], 0)
        for field, value in (("benchmark_sha256", "a" * 64), ("mean_recall_at_3", float("nan")),
                             ("held_out_cases", 1), ("cases", [])):
            invalid = {**report, field: value}
            with self.subTest(field=field), self.assertRaises(ValueError):
                compare_reports(report, invalid)
        with self.assertRaisesRegex(ValueError, "metrics do not match"):
            compare_reports(report, {**report, "mean_recall_at_3": 1})

    def test_query_diagnostics_distinguish_vocabulary_failures_and_negative_abstention(self):
        rows = {row["id"]: row for row in evaluate()["cases"]}
        self.assertEqual(rows["q13"]["diagnostics"]["outcome"], "missed_relevant")
        self.assertFalse(rows["q13"]["diagnostics"]["has_vector"])
        self.assertTrue(rows["q11"]["diagnostics"]["has_vector"])
        self.assertEqual(rows["q11"]["diagnostics"]["outcome"], "correct_abstention")
        self.assertEqual(rows["q13"]["diagnostics"]["missed_relevant"], ["o-timber"])
        for row in rows.values():
            self.assertEqual([item["id"] for item in row["diagnostics"]["results"]], row["ranked"])
            self.assertEqual(row["diagnostics"]["irrelevant_returned"],
                             sorted(set(row["ranked"]) - set(row["relevant"])))
