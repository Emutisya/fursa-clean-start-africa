import unittest

from fursa.discovery import browse


class DiscoveryTests(unittest.TestCase):
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
