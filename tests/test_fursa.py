import http.client
import json
import math
from pathlib import Path
import socket
import subprocess
import sys
import threading
import unittest

from fursa.catalog import corpus
from fursa.evaluate import CASES, evaluate
from fursa.model import Matcher, Tfidf
from fursa.server import make_server


class CLITests(unittest.TestCase):
    def test_occupied_port_explains_how_to_recover(self):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen()
            port = listener.getsockname()[1]
            result = subprocess.run(
                [sys.executable, "-m", "fursa", "serve", "--port", str(port)],
                cwd=Path(__file__).resolve().parents[1],
                text=True, capture_output=True, timeout=10,
            )
        self.assertEqual(result.returncode, 2)
        self.assertIn(f"Could not start the local dashboard on port {port}", result.stderr)
        self.assertIn("--port 0", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_invalid_ports_return_actionable_errors(self):
        for port in ("-1", "65536", "999999999999999999999"):
            with self.subTest(port=port):
                result = subprocess.run(
                    [sys.executable, "-m", "fursa", "serve", "--port", port],
                    cwd=Path(__file__).resolve().parents[1],
                    text=True, capture_output=True, timeout=10,
                )
                self.assertEqual(result.returncode, 2)
                self.assertIn("--port must be between 0 and 65535", result.stderr)
                self.assertIn("use 0 to choose an available port", result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertEqual(result.stdout, "")


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.matcher = Matcher()

    def test_learned_idf_and_normalized_vectors(self):
        model = Tfidf(["timber timber metal", "metal solar"])
        self.assertAlmostEqual(model.idf["metal"], 1)
        self.assertAlmostEqual(model.idf["timber"], math.log(3 / 2) + 1)
        vector = model.vector("timber metal")
        self.assertAlmostEqual(sum(value * value for value in vector.values()), 1)
        self.assertEqual(model.vector("unseenword"), {})

    def test_skill_match_and_evidence_gap(self):
        result = self.matcher.match({"skills": ["carpentry"]})
        self.assertEqual(result["opportunities"][0]["id"], "o-timber")
        self.assertIn("Synthetic carpentry work sample", result["opportunities"][0]["evidence_gaps"])
        with_evidence = self.matcher.match({"skills": ["carpentry"], "evidence": ["e-carpentry"]})
        self.assertEqual(with_evidence["opportunities"][0]["evidence_gaps"], [])
        self.assertEqual(result["opportunities"][0]["similarity"], with_evidence["opportunities"][0]["similarity"])
        self.assertTrue(result["human_review_required"])

    def test_invalid_and_empty(self):
        for payload in [None, [], {}, {"skills": []}, {"skills": "carpentry"},
                        {"skills": ["unknown"]}, {"skills": [False]},
                        {"skills": ["carpentry", "carpentry"]},
                        {"skills": ["carpentry"], "evidence": ["e-welding"]},
                        {"skills": ["carpentry"], "evidence": [3]},
                        {"skills": ["carpentry"], "evidence": "e-carpentry"},
                        {"skills": ["carpentry"], "evidence": ["e-carpentry", "e-carpentry"]}]:
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                self.matcher.match(payload)

    def test_no_match_is_not_negative_judgement(self):
        result = self.matcher.match({"skills": ["astronomy"]})
        self.assertTrue(result["no_match"])
        self.assertEqual(result["opportunities"], [])
        self.assertEqual(result["pathways"], [])

    def test_sensitive_inputs_are_excluded_by_schema(self):
        for field in ["criminal_history", "offence_type", "gender", "age", "ethnicity",
                      "nationality", "disability", "reoffending", "employability", "name"]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.matcher.match({"skills": ["carpentry"], field: "ignored?"})
        with self.assertRaises(ValueError):
            self.matcher.match({"skills": ["carpentry convicted male"]})

    def test_order_does_not_change_rankings(self):
        a = self.matcher.match({"skills": ["solar", "electrical"]})
        b = self.matcher.match({"skills": ["electrical", "solar"]})
        self.assertEqual(a, b)

    def test_heldout_evaluation_reproducible_and_disjoint(self):
        report = evaluate()
        self.assertEqual(report, evaluate())
        self.assertEqual(report["held_out_cases"], len(CASES))
        self.assertEqual(report["fit_documents"], len(corpus()))
        self.assertTrue(all(0 <= report[key] <= 1 for key in [
            "mean_recall_at_3", "mean_precision_at_3", "mean_reciprocal_rank", "negative_abstention_rate"]))
        self.assertEqual(report["negative_abstention_rate"], 1)


class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = make_server(0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def request(self, method, path, body=None, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        conn.request(method, path, body=body, headers=headers or {})
        response = conn.getresponse()
        data = response.read()
        status = response.status
        conn.close()
        return status, data

    def post(self, body, **headers):
        return self.request("POST", "/api/match", json.dumps(body),
                            {"Content-Type": "application/json", **headers})

    def test_local_inference(self):
        status, raw = self.post({"skills": ["solar", "electrical"], "evidence": []})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(raw)["opportunities"][0]["id"], "o-solar")

    def test_catalog_and_page(self):
        status, raw = self.request("GET", "/api/catalog")
        self.assertEqual(status, 200)
        self.assertIn("carpentry", json.loads(raw)["skills"])
        status, raw = self.request("GET", "/?clawpilotTheme=dark")
        self.assertEqual(status, 200)
        self.assertIn(b"Skills first. Human decisions always.", raw)

    def test_http_input_boundaries(self):
        self.assertEqual(self.post({"skills": []})[0], 400)
        self.assertEqual(self.post({"skills": ["carpentry"], "offence_type": "x"})[0], 400)
        self.assertEqual(self.request("POST", "/api/match", "{", {"Content-Type": "application/json"})[0], 400)
        self.assertEqual(self.request("POST", "/api/match", "x"*5000, {"Content-Type": "application/json"})[0], 413)
        self.assertEqual(self.request("POST", "/api/match", "{}")[0], 415)
        self.assertEqual(self.post({"skills": ["carpentry"]}, Origin="https://example.invalid")[0], 403)
        self.assertEqual(self.post({"skills": ["carpentry"]}, Host="example.invalid")[0], 403)
        self.assertEqual(self.request("GET", "/missing")[0], 404)


if __name__ == "__main__":
    unittest.main()
