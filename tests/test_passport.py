import unittest
import json
from unittest.mock import patch

from fursa.passport import checksum, compare_selections, edit_selections, export_passport, import_passport, merge_selections


class PassportTests(unittest.TestCase):
    def test_edits_remove_attached_simulations_and_reject_ambiguous_intent(self):
        before = {"skills": ["carpentry"], "evidence": ["e-carpentry"]}
        result = edit_selections(before, {"remove_skills": ["carpentry"], "add_skills": ["welding"]})
        self.assertEqual(result["skills"], ["welding"])
        self.assertEqual(result["evidence"], [])
        self.assertEqual(before["evidence"], ["e-carpentry"])
        for changes in ({"remove_skills": ["carpentry"]}, {"add_skills": ["carpentry"]},
                        {"remove_skills": ["welding"]}, {"name": []},
                        {"add_evidence": ["e-welding"]}, {"remove_evidence": ["e-welding"]},
                        {"add_skills": ["welding", "welding"]}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                edit_selections(before, changes)

    def test_merge_is_canonical_deduplicates_between_sets_and_preserves_unverified_status(self):
        sets = [{"skills": ["solar"], "evidence": ["e-solar"]},
                {"skills": ["electrical", "solar"]}]
        result = merge_selections(sets)
        self.assertEqual(result, merge_selections(list(reversed(sets))))
        self.assertEqual(import_passport(json.dumps(result).encode()),
                         {"skills": ["electrical", "solar"], "evidence": ["e-solar"]})
        self.assertEqual(result["verification"], "Unverified synthetic selections")
        for selections in ([], sets[:1], sets * 3, [sets[0], {"skills": ["unknown"]}]):
            with self.assertRaises(ValueError):
                merge_selections(selections)

    def test_comparison_describes_simulation_changes_not_people(self):
        before = {"skills": ["carpentry"]}
        evidence_only = compare_selections(before, {"skills": ["carpentry"], "evidence": ["e-carpentry"]})
        self.assertEqual(evidence_only["evidence_added"], ["e-carpentry"])
        for row in evidence_only["ranking_changes"]["opportunities"]:
            self.assertEqual(row["before_rank"], row["after_rank"])
        changed = compare_selections(before, {"skills": ["welding"]})
        self.assertEqual(changed["skills_removed"], ["carpentry"])
        self.assertEqual(changed["skills_added"], ["welding"])
        ranks = {row["id"]: row for row in changed["ranking_changes"]["opportunities"]}
        self.assertIsNone(ranks["o-timber"]["after_rank"])
        self.assertIsNone(ranks["o-metal"]["before_rank"])

    def test_import_round_trip_and_rejects_tampering_personal_data_and_stale_catalogue(self):
        body = export_passport({"skills": ["solar"], "evidence": ["e-solar"]})
        raw = json.dumps(body).encode()
        self.assertEqual(import_passport(raw), {"skills": ["solar"], "evidence": ["e-solar"]})
        for key, value in (("name", "rejected"), ("synthetic", 1), ("skills", ["welding"]),
                           ("schema", "credential.v1"), ("content_sha256", "bad")):
            with self.subTest(key=key), self.assertRaises(ValueError):
                import_passport(json.dumps({**body, key: value}).encode())
        with patch("fursa.passport.fingerprint", return_value="changed"), self.assertRaisesRegex(ValueError, "catalogue differs"):
            import_passport(raw)

    def test_import_rejects_oversize_duplicate_fields_and_wrong_encoding(self):
        for raw in (b"", b"x" * 16385, b'{"skills":[],"skills":[]}', b"{}", b"\xff",
                    json.dumps(export_passport({"skills": ["solar"]})).encode("utf-16")):
            with self.subTest(size=len(raw)), self.assertRaises(ValueError):
                import_passport(raw)

    def test_export_is_canonical_and_checksum_covers_safety_and_selections(self):
        result = export_passport({"skills": ["solar", "electrical"], "evidence": ["e-solar"]})
        self.assertEqual(result, export_passport({"skills": ["electrical", "solar"], "evidence": ["e-solar"]}))
        body = {key: value for key, value in result.items() if key != "content_sha256"}
        self.assertEqual(checksum(body), result["content_sha256"])
        self.assertNotEqual(result["content_sha256"],
                            export_passport({"skills": ["solar", "electrical"]})["content_sha256"])
        with self.assertRaises(ValueError):
            export_passport({"skills": ["solar"], "name": "not accepted"})
