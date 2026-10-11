import unittest

from fursa.discovery import browse, detail


class DiscoveryTests(unittest.TestCase):
    def test_detail_connects_resources_to_simulated_evidence_and_pathways(self):
        result = detail("o-solar")
        self.assertEqual({item["id"] for item in result["evidence_options"]}, {"e-solar", "e-electrical"})
        self.assertEqual({item["id"] for item in result["related_pathways"]}, {"p-solar", "p-electrical"})
        result["resource"]["skills"].clear()
        result["related_pathways"][0]["steps"].clear()
        self.assertEqual(len(detail("o-solar")["resource"]["skills"]), 2)
        self.assertEqual(len(detail("p-solar")["resource"]["steps"]), 4)
        for identifier in ("o-unknown", "name", None, []):
            with self.assertRaises(ValueError):
                detail(identifier)

    def test_browse_uses_all_selected_skills_and_returns_independent_data(self):
        rows = browse(skills=["spreadsheets", "bookkeeping"])["items"]
        self.assertEqual([row["id"] for row in rows], ["o-accounts"])
        rows[0]["skills"].clear()
        self.assertEqual(len(browse(skills=["bookkeeping"])["items"]), 1)
        self.assertEqual(browse(skills=["astronomy"])["items"], [])
        self.assertEqual(len(browse("pathway")["items"]), 12)

    def test_browse_rejects_unbounded_or_duplicate_filters(self):
        for skills in ("carpentry", ["name"], ["carpentry", "carpentry"], [False]):
            with self.subTest(skills=skills), self.assertRaises(ValueError):
                browse(skills=skills)
        with self.assertRaises(ValueError):
            browse("jobs")
