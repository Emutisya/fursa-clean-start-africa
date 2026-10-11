import unittest
import json
from unittest.mock import patch

from fursa.passport import checksum, export_passport, import_passport


class PassportTests(unittest.TestCase):
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
