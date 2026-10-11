import unittest
import math
from copy import deepcopy

from fursa.audit import compare_snapshots, model_snapshot, verify_snapshot


class AuditTests(unittest.TestCase):
    def test_model_diff_reports_consistent_vocabulary_and_frequency_changes_without_loading(self):
        before = model_snapshot()
        after = deepcopy(before)
        after["idf"].pop("timber")
        after["document_frequencies"].pop("timber")
        after["document_frequencies"]["zebra"] = 1
        after["idf"]["zebra"] = math.log((1 + after["document_count"]) / 2) + 1
        after["document_frequencies"]["metal"] += 1
        after["idf"]["metal"] = math.log((1 + after["document_count"]) / (1 + after["document_frequencies"]["metal"])) + 1
        result = compare_snapshots(before, after)
        self.assertEqual(result["added_terms"], ["zebra"])
        self.assertEqual(result["removed_terms"], ["timber"])
        self.assertEqual(result["changed_terms"][0]["term"], "metal")
        self.assertLess(result["changed_terms"][0]["idf_delta"], 0)
        after["idf"]["zebra"] = 0
        with self.assertRaisesRegex(ValueError, "inconsistent"):
            compare_snapshots(before, after)

    def test_verification_recomputes_fit_and_rejects_tampered_weights_or_provenance(self):
        snapshot = model_snapshot()
        self.assertTrue(verify_snapshot(snapshot)["matches_current_fit"])
        for field, value in (("corpus_sha256", "0" * 64), ("method", "invented"),
                             ("synthetic", 1), ("document_count", 0)):
            with self.subTest(field=field), self.assertRaises(ValueError):
                verify_snapshot({**snapshot, field: value})
        for weight in (float("nan"), True, .5):
            changed = deepcopy(snapshot)
            changed["idf"]["timber"] = weight
            with self.assertRaises(ValueError):
                verify_snapshot(changed)
        changed = deepcopy(snapshot)
        changed["document_frequencies"]["timber"] += 1
        with self.assertRaises(ValueError):
            verify_snapshot(changed)
