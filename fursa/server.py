"""Loopback-only, no telemetry, persistence, uploads or third-party requests."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from .catalog import EVIDENCE, SKILLS
from .model import Matcher

HTML = Path(__file__).resolve().parent.parent / "web" / "index.html"
MAX_BODY = 4096


def unique_fields(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON fields are not accepted.")
        result[key] = value
    return result


def make_server(port=8765):
    matcher = Matcher()

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(5)

        def handle_one_request(self):
            try:
                super().handle_one_request()
            except ConnectionError:
                self.close_connection = True

        def log_message(self, format, *args):
            pass

        def send(self, status, body, content_type="application/json"):
            data = json.dumps(body).encode() if content_type == "application/json" else body
            self.send_response(status)
            self.send_header("Content-Type", content_type + "; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(data)

        def allowed(self):
            hosts = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
            if self.headers.get("Host") not in hosts:
                self.send(403, {"error": "Loopback Host required."})
                return False
            origin = self.headers.get("Origin")
            if origin is not None and origin not in {f"http://{host}" for host in hosts}:
                self.send(403, {"error": "Cross-origin requests are not accepted."})
                return False
            return True

        def do_GET(self):
            if not self.allowed():
                return
            path = urlsplit(self.path).path
            if path == "/":
                self.send(200, HTML.read_bytes(), "text/html")
            elif path == "/api/catalog":
                self.send(200, {"skills": list(SKILLS), "evidence": EVIDENCE, "synthetic": True})
            elif path == "/api/health":
                self.send(200, {"status": "ok", "model": "learned-tfidf", "synthetic": True})
            else:
                self.send(404, {"error": "Not found."})

        def do_POST(self):
            if not self.allowed():
                return
            if urlsplit(self.path).path != "/api/match":
                self.send(404, {"error": "Not found."})
                return
            if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
                self.send(415, {"error": "Use application/json."})
                return
            try:
                raw_length = self.headers.get("Content-Length", "")
                if (self.headers.get("Transfer-Encoding") is not None
                        or len(self.headers.get_all("Content-Length", [])) != 1
                        or not raw_length.isascii() or not raw_length.isdigit()):
                    raise ValueError("One decimal Content-Length is required; chunked bodies are unsupported.")
                length = int(raw_length)
                if not 0 < length <= MAX_BODY:
                    self.send(413, {"error": "JSON body must be 1 to 4096 bytes."})
                    return
                self.connection.settimeout(5)
                raw = self.rfile.read(length)
                if len(raw) != length:
                    raise ValueError("Incomplete request body.")
                payload = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_fields)
                result = matcher.match(payload)
            except (ValueError, UnicodeError, RecursionError):
                self.send(400, {"error": "Invalid input. Use catalogued skills and simulated evidence only."})
                return
            except TimeoutError:
                self.send(408, {"error": "Request body timed out."})
                return
            self.send(200, result)

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)
