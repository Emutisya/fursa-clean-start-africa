import unittest

from fursa.passport import checksum, export_passport


class PassportTests(unittest.TestCase):
    def test_export_is_canonical_and_checksum_covers_safety_and_selections(self):
        result = export_passport({"skills": ["solar", "electrical"], "evidence": ["e-solar"]})
        self.assertEqual(result, export_passport({"skills": ["electrical", "solar"], "evidence": ["e-solar"]}))
        body = {key: value for key, value in result.items() if key != "content_sha256"}
        self.assertEqual(checksum(body), result["content_sha256"])
        self.assertNotEqual(result["content_sha256"],
                            export_passport({"skills": ["solar", "electrical"]})["content_sha256"])
        with self.assertRaises(ValueError):
            export_passport({"skills": ["solar"], "name": "not accepted"})
