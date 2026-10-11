import unittest
from copy import deepcopy
from unittest.mock import patch

from fursa.evaluate import cutoff_diagnostics, evaluate, evaluation_slices, ranking_curves
from fursa.reporting import compare_reports


class EvaluationToolsTests(unittest.TestCase):
    def test_slices_expose_denominators_and_partition_lexical_failures(self):
        report = evaluate()
        slices = evaluation_slices()["slices"]
        known, unknown = slices["positive_known_vector"], slices["positive_empty_vector"]
        self.assertEqual(unknown["case_ids"], ["q13", "q14"])
        self.assertEqual(unknown["mean_recall_at_3"], 0)
        self.assertIsNone(unknown["mean_correct_abstention"])
        total = known["case_count"] + unknown["case_count"]
        self.assertEqual(total, report["positive_cases"])
        weighted = sum(row["case_count"] * row["mean_recall_at_3"] for row in (known, unknown)) / total
        self.assertAlmostEqual(weighted, report["mean_recall_at_3"])
        self.assertEqual(slices["positive_multiple_relevant"]["case_ids"], ["q10"])

    def test_cutoff_sweep_reproduces_default_and_uses_full_ranking_cutoff(self):
        report = evaluate()
        sweeps = cutoff_diagnostics()["sweeps"]
        default = next(row for row in sweeps if row["cutoff"] == .08)
        self.assertEqual([row["ranked"] for row in default["cases"]], [row["ranked"] for row in report["cases"]])
        self.assertAlmostEqual(default["mean_recall_at_3"], report["mean_recall_at_3"])
        self.assertAlmostEqual(default["negative_abstention_rate"], report["negative_abstention_rate"])
        counts = [sum(len(case["ranked"]) for case in row["cases"]) for row in sweeps]
        self.assertEqual(counts, sorted(counts, reverse=True))
        self.assertLess(sweeps[-1]["mean_recall_at_3"], default["mean_recall_at_3"])

    def test_depth_curves_reproduce_top_three_and_do_not_hide_fixed_cutoff_misses(self):
        report = evaluate()
        rows = ranking_curves()["curves"]
        at_three = next(row for row in rows if row["k"] == 3)
        self.assertAlmostEqual(at_three["mean_recall"], report["mean_recall_at_3"])
        self.assertAlmostEqual(at_three["mean_precision"], report["mean_precision_at_3"])
        self.assertAlmostEqual(at_three["mean_ndcg"], report["mean_ndcg_at_3"])
        self.assertEqual([row["mean_recall"] for row in rows],
                         sorted(row["mean_recall"] for row in rows))
        self.assertLess(rows[-1]["mean_recall"], 1)

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
