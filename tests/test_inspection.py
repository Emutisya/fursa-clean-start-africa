import unittest
from copy import deepcopy
from unittest.mock import patch

from fursa.catalog import EVIDENCE, SKILLS, corpus, fingerprint
from fursa.model import Matcher, Tfidf, tokens


class InspectionTests(unittest.TestCase):
    def test_overlap_review_distinguishes_lexical_only_suggestions_from_catalogue_associations(self):
        report = Matcher().overlap_review({"skills": ["customer service"]})
        opportunities = report["reviews"]["opportunities"]
        self.assertEqual(opportunities["lexical_only_returned"], ["o-nursery"])
        self.assertEqual([row["id"] for row in opportunities["declared_overlap"]], ["o-dispatch"])
        self.assertTrue(opportunities["declared_overlap"][0]["returned"])
        broad = Matcher().overlap_review({"skills": list(SKILLS)})
        self.assertTrue(any(row["not_returned_reason"] == "outside_top_three"
                            for row in broad["reviews"]["opportunities"]["declared_overlap"]))
        empty = Matcher().overlap_review({"skills": ["astronomy"]})
        self.assertEqual(empty["reviews"]["opportunities"]["declared_overlap"], [])

    def test_pathway_overlap_and_gap_explanations_follow_selections_not_ranking(self):
        matcher = Matcher()
        result = matcher.match({"skills": ["solar", "electrical"], "evidence": ["e-solar"]})
        paths = {row["id"]: row for row in result["pathways"]}
        self.assertEqual(paths["p-solar"]["shared_skills"], ["solar"])
        self.assertEqual(paths["p-solar"]["evidence_gaps"], [])
        self.assertEqual(paths["p-electrical"]["evidence_gaps"], ["Synthetic electrical work sample"])
        without = matcher.match({"skills": ["solar", "electrical"]})
        self.assertEqual([(row["id"], row["similarity"]) for row in result["pathways"]],
                         [(row["id"], row["similarity"]) for row in without["pathways"]])

    def test_evidence_audit_observes_gap_changes_without_affecting_either_ranking(self):
        matcher = Matcher()
        payload = {"skills": ["carpentry", "welding"], "evidence": ["e-carpentry"]}
        report = matcher.evidence_audit(payload)
        self.assertTrue(report["all_rankings_unchanged"])
        rows = {row["sample"]: row for row in report["scenarios"]}
        self.assertFalse(rows["e-carpentry"]["selected_after"])
        self.assertTrue(rows["e-welding"]["selected_after"])
        self.assertEqual(rows["e-carpentry"]["gap_changes"][0]["after"], ["Synthetic carpentry work sample"])
        self.assertEqual(rows["e-welding"]["gap_changes"][0]["after"], [])
        self.assertEqual(payload["evidence"], ["e-carpentry"])
        self.assertEqual(matcher.evidence_audit({"skills": ["astronomy"]})["scenarios"], [])
        baseline = matcher.match({"skills": ["carpentry"]})
        changed = deepcopy(baseline)
        changed["opportunities"][0]["similarity"] = 0
        with patch.object(matcher, "match", side_effect=[baseline, changed]):
            self.assertFalse(matcher.evidence_audit({"skills": ["carpentry"]})["all_rankings_unchanged"])

    def test_batch_validates_every_scenario_before_any_inference(self):
        matcher = Matcher()
        selections = [{"skills": ["solar"]}, {"skills": ["astronomy"]}]
        result = matcher.batch(selections)
        self.assertEqual([row["index"] for row in result["results"]], [0, 1])
        self.assertEqual(result["results"][0]["result"], matcher.match(selections[0]))
        self.assertTrue(result["results"][1]["result"]["no_match"])
        with patch.object(matcher, "match") as inference:
            with self.assertRaises(ValueError):
                matcher.batch([selections[0], {"skills": ["private"]}])
            inference.assert_not_called()
        for selections in ([], [{}] * 17, {"skills": ["solar"]}):
            with self.assertRaises(ValueError):
                matcher.batch(selections)

    def test_term_inspection_connects_fit_sources_and_document_frequency(self):
        matcher = Matcher()
        result = matcher.inspect_term("timber")
        sources = {row["id"]: row for row in result["sources"]}
        self.assertEqual(len(sources), result["document_frequency"])
        self.assertGreater(sources["o-timber"]["term_count"], 1)
        self.assertIn("skill:carpentry", sources)
        self.assertNotIn("o-metal", sources)
        for term in ("Timber", "timber metal", "", None, "unknown"):
            with self.assertRaises(ValueError):
                matcher.inspect_term(term)

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
