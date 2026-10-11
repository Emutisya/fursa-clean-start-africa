"""Loopback-only, no telemetry, persistence, uploads or third-party requests."""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .catalog import EVIDENCE, OPPORTUNITIES, PATHWAYS, SKILLS, fingerprint
from .model import Matcher, SelectionError
from .discovery import browse, compare, detail, skill_map
from .jsonio import unique_fields

HTML = Path(__file__).resolve().parent.parent / "web" / "index.html"
MAX_BODY = 4096


def make_server(port=8765, max_connections=8):
    if type(max_connections) is not int or not 1 <= max_connections <= 32:
        raise ValueError("Local server connection limit must be an integer from 1 to 32.")
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

        def send(self, status, body, content_type="application/json", headers=None):
            data = json.dumps(body).encode() if content_type == "application/json" else body
            self.send_response(status)
            self.send_header("Content-Type", content_type + "; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'")
            for name, value in (headers or {}).items():
                self.send_header(name, value)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(data)

        def allowed(self):
            hosts = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
            if len(self.headers.get_all("Host", [])) != 1 or self.headers.get("Host") not in hosts:
                self.send(403, {"error": "Loopback Host required."})
                return False
            origin = self.headers.get("Origin")
            if (len(self.headers.get_all("Origin", [])) > 1
                    or origin is not None and origin not in {f"http://{host}" for host in hosts}):
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
                self.send(200, {"skills": list(SKILLS), "evidence": EVIDENCE, "synthetic": True,
                                "catalog_sha256": fingerprint(),
                                "opportunity_ids": [row["id"] for row in OPPORTUNITIES],
                                "pathway_ids": [row["id"] for row in PATHWAYS]})
            elif path == "/api/health":
                self.send(200, {"status": "ok", "model": "learned-tfidf", "synthetic": True})
            elif path == "/api/match":
                self.method_not_allowed()
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

        def do_HEAD(self):
            self.do_GET()

        def method_not_allowed(self):
            if not self.allowed():
                return
            path = urlsplit(self.path).path
            if path == "/api/match":
                allowed = "POST"
            elif path in {"/", "/api/catalog", "/api/health", "/api/skills", "/api/resources", "/api/compare"} or path.startswith("/api/resources/"):
                allowed = "GET, HEAD"
            else:
                self.send(404, {"error": "Not found."})
                return
            self.send(405, {"error": "This route does not accept this method. Use the Allow header.",
                            "error_code": "request_method_not_allowed"}, headers={"Allow": allowed})

        do_PUT = method_not_allowed
        do_DELETE = method_not_allowed
        do_PATCH = method_not_allowed
        do_OPTIONS = method_not_allowed
        do_TRACE = method_not_allowed
        do_CONNECT = method_not_allowed

        def do_POST(self):
            if not self.allowed():
                return
            if urlsplit(self.path).path != "/api/match":
                self.method_not_allowed()
                return
            media = [part.strip().lower() for part in self.headers.get("Content-Type", "").split(";")]
            if (len(self.headers.get_all("Content-Type", [])) != 1 or media[0] != "application/json"
                    or len(media) > 2 or any(part not in {"charset=utf-8", 'charset="utf-8"'} for part in media[1:])):
                self.send(415, {"error": "Use one application/json Content-Type with optional charset=utf-8."})
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

    class LimitedServer(ThreadingHTTPServer):
        def __init__(self):
            super().__init__(("127.0.0.1", port), Handler)
            self.slots = threading.BoundedSemaphore(max_connections)

        def process_request(self, request, client_address):
            if not self.slots.acquire(blocking=False):
                body = b'{"error":"Local server busy. Retry after another request finishes.","error_code":"server_busy"}'
                try:
                    request.settimeout(1)
                    request.sendall(
                        b"HTTP/1.0 503 Service Unavailable\r\n"
                        b"Content-Type: application/json; charset=utf-8\r\n"
                        b"Cache-Control: no-store\r\nX-Content-Type-Options: nosniff\r\n"
                        b"Retry-After: 1\r\nConnection: close\r\nContent-Length: "
                        + str(len(body)).encode("ascii") + b"\r\n\r\n" + body)
                except OSError:
                    pass
                finally:
                    self.shutdown_request(request)
                return
            try:
                super().process_request(request, client_address)
            except BaseException:
                self.slots.release()
                raise

        def process_request_thread(self, request, client_address):
            try:
                super().process_request_thread(request, client_address)
            finally:
                self.slots.release()

    return LimitedServer()
