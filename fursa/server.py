"""Loopback-only, no telemetry, persistence, uploads or third-party requests."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from .catalog import EVIDENCE, SKILLS
from .model import Matcher

HTML = Path(__file__).resolve().parent.parent / "web" / "index.html"
MAX_BODY = 4096


def make_server(port=8765):
    matcher = Matcher()

    class Handler(BaseHTTPRequestHandler):
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

        def do_GET(self):
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
            if urlsplit(self.path).path != "/api/match":
                self.send(404, {"error": "Not found."})
                return
            host = self.headers.get("Host", "")
            if host not in {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}:
                self.send(403, {"error": "Loopback Host required."})
                return
            origin = self.headers.get("Origin")
            if origin and origin not in {f"http://127.0.0.1:{self.server.server_port}", f"http://localhost:{self.server.server_port}"}:
                self.send(403, {"error": "Cross-origin requests are not accepted."})
                return
            if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
                self.send(415, {"error": "Use application/json."})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= MAX_BODY:
                    self.send(413, {"error": "JSON body must be 1 to 4096 bytes."})
                    return
                self.connection.settimeout(5)
                payload = json.loads(self.rfile.read(length))
                result = matcher.match(payload)
            except (ValueError, UnicodeError, RecursionError):
                self.send(400, {"error": "Invalid input. Use catalogued skills and simulated evidence only."})
                return
            except TimeoutError:
                self.send(408, {"error": "Request body timed out."})
                return
            self.send(200, result)

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)
