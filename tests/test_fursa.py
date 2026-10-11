import http.client
from contextlib import redirect_stderr
import io
import json
import math
from pathlib import Path
import socket
import subprocess
import sys
import threading
import tempfile
import unittest
from unittest.mock import patch

from fursa.catalog import corpus
from fursa.evaluate import CASES, evaluate
from fursa.model import Matcher, Tfidf
from fursa.server import make_server


class CLITests(unittest.TestCase):
    def test_failed_output_replacement_preserves_existing_report(self):
        from fursa.__main__ import main
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evaluation.json"
            path.write_text('{"previous": true}', encoding="utf-8")
            errors = io.StringIO()
            with patch.object(sys, "argv", ["fursa", "evaluate", "--output", str(path)]), \
                    patch("fursa.__main__.os.replace", side_effect=PermissionError("Isolated write failure")), \
                    redirect_stderr(errors), self.assertRaises(SystemExit) as caught:
                main()
            self.assertEqual(caught.exception.code, 2)
            self.assertIn("Could not write output", errors.getvalue())
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"previous": True})
            self.assertEqual(list(Path(directory).glob("*.tmp")), [])

    def test_output_path_failures_are_actionable_and_do_not_claim_success(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "blocked"
            target.write_text("existing file", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-m", "fursa", "train", "--output", str(target / "model.json")],
                text=True, capture_output=True, timeout=10,
            )
        self.assertEqual(result.returncode, 2)
        self.assertIn("Could not write output", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(result.stdout, "")

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

    def test_ranking_uses_full_precision_before_rounding_display_scores(self):
        model = Tfidf(["timber"])
        items = [{"id": "a", "title": "lower", "description": "timber", "skills": []},
                 {"id": "z", "title": "higher", "description": "timber", "skills": []}]
        with patch.object(model, "vector", side_effect=[{"timber": 1}, {"timber": .5000001}, {"timber": .5000002}]):
            ranked = model.rank("timber", items)
        self.assertEqual([row["id"] for row in ranked], ["z", "a"])
        self.assertEqual(ranked[0]["similarity"], ranked[1]["similarity"])

    def test_invalid_benchmarks_are_rejected_even_with_python_optimization(self):
        for cases in ([], [CASES[0]], [*CASES, CASES[0]], [*CASES, ("unknown", "new query", {"missing"})]):
            with patch("fursa.evaluate.CASES", cases), self.assertRaises(ValueError):
                evaluate()
        script = (
            "import importlib; m=importlib.import_module('fursa.evaluate'); "
            "m.CASES=[*m.CASES,m.CASES[0]]; m.evaluate()"
        )
        result = subprocess.run([sys.executable, "-O", "-c", script], text=True, capture_output=True, timeout=10)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Duplicate evaluation", result.stderr)

    def test_skill_match_and_evidence_gap(self):
        result = self.matcher.match({"skills": ["carpentry"]})
        self.assertEqual(result["opportunities"][0]["id"], "o-timber")
        self.assertIn("Synthetic carpentry work sample", result["opportunities"][0]["evidence_gaps"])
        with_evidence = self.matcher.match({"skills": ["carpentry"], "evidence": ["e-carpentry"]})
        self.assertEqual(with_evidence["opportunities"][0]["evidence_gaps"], [])
        self.assertEqual(result["opportunities"][0]["similarity"], with_evidence["opportunities"][0]["similarity"])
        self.assertTrue(result["human_review_required"])

    def test_bag_of_words_duplicates_and_training_overlap_are_rejected(self):
        duplicate = ("reordered", " ".join(reversed(CASES[0][1].split())), CASES[0][2])
        with patch("fursa.evaluate.CASES", [*CASES, duplicate]), self.assertRaisesRegex(ValueError, "Duplicate evaluation"):
            evaluate()
        leaked = ("leaked", " ".join(reversed(corpus()[0].split())), CASES[0][2])
        with patch("fursa.evaluate.CASES", [*CASES, leaked]), self.assertRaisesRegex(ValueError, "training/evaluation"):
            evaluate()

    def test_malformed_evaluation_cases_report_schema_errors(self):
        for case in (None, [], ("id",), (None, "timber", set()), ([], "timber", set()),
                     ("id", None, set()), ("id", "123", set()), ("id", "timber", []),
                     ("id", "timber", {1})):
            with self.subTest(case=case), patch("fursa.evaluate.CASES", [*CASES, case]):
                with self.assertRaisesRegex(ValueError, "Evaluation cases require"):
                    evaluate()

    def test_consumers_cannot_mutate_catalogs_through_match_results(self):
        expected = self.matcher.match({"skills": ["carpentry"]})
        result = self.matcher.match({"skills": ["carpentry"]})
        result["opportunities"][0]["skills"].clear()
        result["pathways"][0]["steps"].clear()
        self.assertEqual(self.matcher.match({"skills": ["carpentry"]}), expected)

    def test_invalid_training_and_retrieval_inputs_have_explicit_errors(self):
        for documents in (None, [], "timber", [None], [""], ["123"]):
            with self.subTest(documents=documents), self.assertRaises(ValueError):
                Tfidf(documents)
        for text in (None, 1, []):
            with self.assertRaisesRegex(ValueError, "string"):
                self.matcher.model.vector(text)
        for limit in (True, 0, -1, 1.5):
            with self.assertRaisesRegex(ValueError, "positive integer"):
                self.matcher.model.rank("timber", [], limit)

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

    def test_benchmark_provenance_changes_when_queries_change(self):
        original = evaluate()
        changed = [*CASES]
        identifier, query, relevant = changed[0]
        changed[0] = (identifier, query + " extra", relevant)
        with patch("fursa.evaluate.CASES", changed):
            observed = evaluate()
        self.assertEqual(observed["corpus_sha256"], original["corpus_sha256"])
        self.assertNotEqual(observed["benchmark_sha256"], original["benchmark_sha256"])

    def test_discounted_gain_and_resource_coverage_match_observed_rankings(self):
        report = evaluate()
        positive = [case for case in report["cases"] if case["relevant"]]
        for case in positive:
            gain = sum(1 / math.log2(index + 2) for index, identifier in enumerate(case["ranked"])
                       if identifier in case["relevant"])
            ideal = sum(1 / math.log2(index + 2) for index in range(min(3, len(case["relevant"]))))
            self.assertAlmostEqual(case["ndcg_at_3"], gain / ideal)
        self.assertAlmostEqual(report["mean_ndcg_at_3"], sum(case["ndcg_at_3"] for case in positive) / len(positive))
        for identifier, coverage in report["resource_coverage"].items():
            self.assertEqual(coverage["relevant_cases"], sum(identifier in case["relevant"] for case in report["cases"]))
            self.assertEqual(coverage["retrieved_relevant_cases"] + coverage["retrieved_irrelevant_cases"],
                             sum(identifier in case["ranked"] for case in report["cases"]))


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
        headers = {"Content-Type": "application/json"}
        for body in (json.dumps({"skills": ["carpentry"]}).encode("utf-16"),
                     '{"skills":["carpentry"],"skills":["welding"]}'):
            self.assertEqual(self.request("POST", "/api/match", body, headers)[0], 400)
        self.assertEqual(self.request("GET", "/api/catalog", headers={"Host": "example.invalid"})[0], 403)
        self.assertEqual(self.request("POST", "/api/match", "{}", {**headers, "Transfer-Encoding": "chunked"})[0], 400)
        self.assertEqual(self.request("POST", "/api/match", "{}", {**headers, "Content-Length": "+2"})[0], 400)
        self.assertEqual(self.post({"skills": []})[0], 400)
        self.assertEqual(self.post({"skills": ["carpentry"], "offence_type": "x"})[0], 400)
        self.assertEqual(self.request("POST", "/api/match", "{", {"Content-Type": "application/json"})[0], 400)
        self.assertEqual(self.request("POST", "/api/match", "x"*5000, {"Content-Type": "application/json"})[0], 413)
        self.assertEqual(self.request("POST", "/api/match", "{}")[0], 415)
        self.assertEqual(self.post({"skills": ["carpentry"]}, Origin="https://example.invalid")[0], 403)
        self.assertEqual(self.post({"skills": ["carpentry"]}, Host="example.invalid")[0], 403)
        self.assertEqual(self.request("GET", "/missing")[0], 404)

    def test_stalled_request_returns_timeout_without_breaking_server(self):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=8)
        try:
            connection.request("POST", "/api/match", "{}", {
                "Content-Type": "application/json", "Content-Length": "100",
            })
            response = connection.getresponse()
            self.assertEqual(response.status, 408)
            self.assertIn("timed out", json.loads(response.read())["error"])
        finally:
            connection.close()
        self.assertEqual(self.request("GET", "/api/health")[0], 200)

    def test_client_disconnect_does_not_log_a_server_failure(self):
        logs = io.StringIO()
        with redirect_stderr(logs), patch.object(self.server.RequestHandlerClass, "send", side_effect=ConnectionResetError("client closed")):
            connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
            try:
                connection.request("GET", "/api/health")
                with self.assertRaises(http.client.RemoteDisconnected):
                    connection.getresponse()
            finally:
                connection.close()
        self.assertEqual(logs.getvalue(), "")
        self.assertEqual(self.request("GET", "/api/health")[0], 200)


if __name__ == "__main__":
    unittest.main()
