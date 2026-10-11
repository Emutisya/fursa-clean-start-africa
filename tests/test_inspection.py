import unittest

from fursa.model import Matcher, Tfidf


class InspectionTests(unittest.TestCase):
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
