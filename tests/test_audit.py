import unittest
from copy import deepcopy

from fursa.audit import model_snapshot, verify_snapshot


class AuditTests(unittest.TestCase):
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
