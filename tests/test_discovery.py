import unittest

from fursa.catalog import SKILLS
from fursa.discovery import browse, compare, detail, preview_additions, related, review_plan, skill_map


class DiscoveryTests(unittest.TestCase):
    def test_addition_preview_uses_only_unselected_catalogue_skills(self):
        result = preview_additions({"skills": ["astronomy"]})
        self.assertEqual(result["baseline_opportunities"], [])
        rows = {row["added_skill"]: row for row in result["scenarios"]}
        self.assertNotIn("astronomy", rows)
        self.assertIn("o-timber", rows["carpentry"]["newly_visible"])
        self.assertEqual(preview_additions({"skills": list(SKILLS)})["scenarios"], [])
        with self.assertRaises(ValueError):
            preview_additions({"skills": ["real biography"]})

    def test_review_plan_distinguishes_missing_skills_and_unverified_samples(self):
        result = review_plan("o-solar", {"skills": ["solar"], "evidence": ["e-solar"]})
        rows = {row["skill"]: row for row in result["evidence_review"]}
        self.assertTrue(rows["solar"]["simulated_sample_selected"])
        self.assertFalse(rows["electrical"]["selected_skill"])
        self.assertEqual(result["skills_to_explore"], ["electrical"])
        self.assertNotIn("approved", result)
        with self.assertRaises(ValueError):
            review_plan("o-solar", {"skills": ["solar"], "evidence": ["e-electrical"]})

    def test_related_resources_explain_overlap_without_self_links(self):
        result = related("o-accounts")
        rows = {row["resource"]["id"]: row for row in result["related"]}
        self.assertNotIn("o-accounts", rows)
        self.assertEqual(rows["o-dispatch"]["shared_skills"], ["spreadsheets"])
        self.assertEqual(rows["o-dispatch"]["additional_skills"], ["customer service", "logistics"])
        self.assertEqual({row["resource"]["id"] for row in related("p-carpentry")["related"]}, {"o-timber"})
        with self.assertRaises(ValueError):
            related("unknown")

    def test_skill_map_distinguishes_coverage_gaps_from_co_occurrence(self):
        skills = {row["skill"]: row for row in skill_map()["skills"]}
        self.assertEqual(skills["astronomy"]["opportunities"], [])
        self.assertEqual(skills["astronomy"]["pathways"], [])
        self.assertEqual(skills["spreadsheets"]["co_occurring_skills"],
                         ["bookkeeping", "customer service", "logistics"])
        skills["carpentry"]["terms"].clear()
        self.assertIn("timber", next(row for row in skill_map()["skills"] if row["skill"] == "carpentry")["terms"])

    def test_comparison_is_order_independent_and_does_not_choose_a_winner(self):
        result = compare(["o-accounts", "o-dispatch"])
        self.assertEqual(result, compare(["o-dispatch", "o-accounts"]))
        self.assertEqual(result["common_skills"], ["spreadsheets"])
        self.assertEqual(result["skill_matrix"]["bookkeeping"], ["o-accounts"])
        self.assertNotIn("winner", result)
        for identifiers in ([], ["o-accounts"], ["o-accounts"] * 2,
                            ["o-accounts", "unknown"], [None, "o-dispatch"], ["x"] * 5):
            with self.assertRaises(ValueError):
                compare(identifiers)

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
