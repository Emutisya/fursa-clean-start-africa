import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from fursa.diagnostics import doctor


class DiagnosticsTests(unittest.TestCase):
    def test_offline_doctor_reports_real_inference_failure_instead_of_claiming_readiness(self):
        self.assertTrue(doctor()["ready"])
        with patch("fursa.model.Tfidf.rank", return_value=[]):
            result = doctor()
        self.assertFalse(result["ready"])
        failures = [row for row in result["checks"] if row["status"] == "failed"]
        self.assertEqual([row["check"] for row in failures], ["inference_boundaries"])
        self.assertIn("fixtures failed", failures[0]["message"])

    def test_failed_doctor_cli_emits_diagnostic_json_and_exits_nonzero(self):
        from fursa.__main__ import main
        output = io.StringIO()
        with patch.object(sys, "argv", ["fursa", "doctor"]), \
                patch("fursa.__main__.doctor", return_value={"ready": False, "checks": []}), \
                redirect_stdout(output), self.assertRaises(SystemExit) as caught:
            main()
        self.assertEqual(caught.exception.code, 1)
        self.assertFalse(json.loads(output.getvalue())["ready"])
