import unittest
from unittest.mock import patch

from fursa.catalog import EVIDENCE, corpus, fingerprint
from fursa.model import Matcher, Tfidf, tokens


class InspectionTests(unittest.TestCase):
    def test_audit_includes_rejected_resources_and_matches_actual_rank_prefix(self):
        matcher = Matcher()
        payload = {"skills": ["spreadsheets"]}
        audit = matcher.audit(payload)
        accepted = [row for row in audit["opportunities"] if row["passes_cutoff"]]
        ranked = matcher.match(payload)["opportunities"]
        self.assertEqual([row["id"] for row in accepted[:3]], [row["id"] for row in ranked])
        self.assertGreater(len(audit["opportunities"]), len(accepted))
        for row in audit["opportunities"]:
            self.assertAlmostEqual(row["cutoff_margin"], row["cosine"] - audit["minimum_similarity"])
        gap = matcher.audit({"skills": ["astronomy"]})
        self.assertFalse(any(row["passes_cutoff"] for row in gap["opportunities"]))

    def test_leave_one_out_sensitivity_exposes_empty_selection_and_resource_dependencies(self):
        matcher = Matcher()
        result = matcher.sensitivity({"skills": ["carpentry", "welding"]})
        rows = {row["omitted_skill"]: row for row in result["scenarios"]}
        self.assertIn("o-timber", rows["carpentry"]["no_longer_returned"])
        self.assertIn("o-metal", rows["welding"]["no_longer_returned"])
        single = matcher.sensitivity({"skills": ["astronomy"]})["scenarios"][0]
        self.assertTrue(single["empty_selection"])
        self.assertEqual(single["ranked"], [])
        self.assertEqual(single["result_set_jaccard"], 1)
        self.assertEqual(result, matcher.sensitivity({"skills": ["welding", "carpentry"]}))

    def test_expanded_discovery_limit_preserves_prefix_and_strict_input_schema(self):
        payload = {"skills": ["bookkeeping", "spreadsheets", "logistics", "solar", "electrical"]}
        matcher = Matcher()
        small = matcher.match(payload, 1)
        larger = matcher.match(payload, 12)
        self.assertEqual(small["opportunities"], larger["opportunities"][:1])
        self.assertEqual(small["pathways"], larger["pathways"][:1])
        self.assertGreater(len(larger["pathways"]), 3)
        self.assertEqual(larger["provenance"]["limit"], 12)
        for limit in (True, 0, 13, 1.5):
            with self.assertRaises(ValueError):
                matcher.match(payload, limit)
        with self.assertRaises(ValueError):
            matcher.match({**payload, "limit": 12})

    def test_provenance_separates_catalogue_metadata_from_rank_input(self):
        matcher = Matcher()
        before = matcher.match({"skills": ["carpentry"]})["provenance"]
        after = matcher.match({"skills": ["carpentry"], "evidence": ["e-carpentry"]})["provenance"]
        self.assertEqual(before, after)
        changed = [dict(row) for row in EVIDENCE]
        changed[0]["description"] += " Revised simulation."
        with patch("fursa.catalog.EVIDENCE", changed):
            self.assertNotEqual(fingerprint(), before["catalog_sha256"])
        self.assertNotEqual(before["query_sha256"],
                            matcher.match({"skills": ["welding"]})["provenance"]["query_sha256"])

    def test_inspection_exposes_actual_fit_frequencies_and_resource_norms(self):
        matcher = Matcher()
        result = matcher.inspect()
        self.assertEqual(result, Matcher().inspect())
        for term in result["terms"]:
            self.assertEqual(term["document_frequency"], sum(term["term"] in tokens(text) for text in corpus()))
        for row in result["resources"]:
            self.assertAlmostEqual(row["squared_norm"], 1)
        result["terms"][0]["idf"] = -1
        self.assertTrue(all(row["idf"] >= 1 for row in matcher.inspect()["terms"]))

    def test_contributions_reconstruct_cosine_without_truncated_explanation(self):
        row = Matcher().match({"skills": ["solar", "electrical"]})["opportunities"][0]
        contributions = row["term_contributions"]
        self.assertGreater(len(contributions), 6)
        self.assertAlmostEqual(sum(term["cosine_contribution"] for term in contributions),
                               row["similarity"], places=6)
        for term in contributions:
            self.assertAlmostEqual(term["cosine_contribution"],
                                   term["query_weight"] * term["resource_weight"])
        self.assertEqual(row["shared_terms"], [term["term"] for term in contributions[:6]])

    def test_diagnostics_distinguish_empty_vector_from_catalogue_coverage(self):
        model = Tfidf(["timber metal"])
        result = model.diagnostics("timber timber unknown")
        self.assertEqual(result["unknown_terms"], ["unknown"])
        self.assertAlmostEqual(result["known_token_fraction"], 2 / 3)
        self.assertFalse(model.diagnostics("123")["has_vector"])
        gap = Matcher().match({"skills": ["astronomy"]})["diagnostics"]
        self.assertTrue(gap["has_vector"])
        self.assertEqual(gap["skills_without_opportunities"], ["astronomy"])
        self.assertIn("catalogue", gap["no_match_reason"])
