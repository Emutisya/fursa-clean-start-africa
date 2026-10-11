import unittest

from fursa.evaluate import evaluate


class EvaluationToolsTests(unittest.TestCase):
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
