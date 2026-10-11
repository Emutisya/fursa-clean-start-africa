import unittest

from fursa.model import Matcher, Tfidf


class InspectionTests(unittest.TestCase):
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
