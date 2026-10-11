"""Loopback-only, no telemetry, persistence, uploads or third-party requests."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .catalog import EVIDENCE, SKILLS
from .model import Matcher, SelectionError
from .discovery import browse, compare, detail, skill_map
from .jsonio import unique_fields

HTML = Path(__file__).resolve().parent.parent / "web" / "index.html"
MAX_BODY = 4096


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
            target = urlsplit(self.path)
            path = target.path
            if path == "/":
                self.send(200, HTML.read_bytes(), "text/html")
            elif path == "/api/catalog":
                self.send(200, {"skills": list(SKILLS), "evidence": EVIDENCE, "synthetic": True})
            elif path == "/api/health":
                self.send(200, {"status": "ok", "model": "learned-tfidf", "synthetic": True})
            elif path == "/api/skills":
                self.send(200, skill_map())
            elif path in {"/api/resources", "/api/compare"}:
                try:
                    if len(target.query) > 2048:
                        raise ValueError("Query too large.")
                    query = parse_qs(target.query, keep_blank_values=True, strict_parsing=True, max_num_fields=16)
                    if path == "/api/resources":
                        if set(query) - {"kind", "skill"} or len(query.get("kind", [])) > 1:
                            raise ValueError("Use one kind and unique catalogue skill filters.")
                        result = browse(query.get("kind", ["opportunity"])[0], query.get("skill", []))
                    else:
                        if set(query) - {"id"}:
                            raise ValueError("Only resource IDs are accepted.")
                        result = compare(query.get("id", []))
                except ValueError:
                    self.send(400, {"error": "Use bounded catalogue kind/skill filters or two to four distinct comparison IDs."})
                    return
                self.send(200, result)
            elif path.startswith("/api/resources/"):
                try:
                    result = detail(path[len("/api/resources/"):])
                except ValueError:
                    self.send(404, {"error": "Unknown fictional resource ID; use /api/resources."})
                    return
                self.send(200, result)
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
            except SelectionError as error:
                self.send(400, {"error": str(error), "error_code": error.code,
                                "recovery": "/api/catalog", "request_retained": False})
                return
            except (ValueError, UnicodeError, RecursionError):
                self.send(400, {"error": "Invalid input. Use catalogued skills and simulated evidence only.",
                                "error_code": "request_invalid_input", "recovery": "/api/catalog"})
                return
            except TimeoutError:
                self.send(408, {"error": "Request body timed out."})
                return
            self.send(200, result)

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)
