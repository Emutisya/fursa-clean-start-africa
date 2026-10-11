import argparse
import json
import os
import tempfile
from pathlib import Path

from .catalog import EVIDENCE, SKILLS
from .evaluate import evaluate
from .discovery import browse, compare, detail
from .model import Matcher
from .server import make_server


def main():
    parser = argparse.ArgumentParser(description="Fursa | synthetic skill-first discovery")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("catalog")
    browse_parser = sub.add_parser("browse")
    browse_parser.add_argument("--kind", choices=["opportunity", "pathway"], default="opportunity")
    browse_parser.add_argument("--skills", default="", help="All selected skills must occur in an item")
    detail_parser = sub.add_parser("detail")
    detail_parser.add_argument("id", help="Exact fictional resource ID")
    compare_parser = sub.add_parser("compare")
    compare_parser.add_argument("ids", nargs="+", help="Two to four distinct fictional IDs")
    train = sub.add_parser("train")
    train.add_argument("--output", default=str(Path("models") / "tfidf.json"))
    evaluate_parser = sub.add_parser("evaluate")
    evaluate_parser.add_argument("--output")
    match = sub.add_parser("match")
    match.add_argument("--skills", required=True, help="Comma-separated exact catalogued skills")
    match.add_argument("--evidence", default="", help="Comma-separated simulated evidence IDs")
    serve = sub.add_parser("serve")
    serve.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if args.command == "serve" and not 0 <= args.port <= 65535:
        parser.error("--port must be between 0 and 65535; use 0 to choose an available port.")
    if args.command == "serve":
        try:
            server = make_server(args.port)
        except OSError as error:
            parser.exit(
                2,
                f"Error: Could not start the local dashboard on port {args.port}. "
                f"Choose another --port or use --port 0 to select an available port. ({error})\n",
            )
        print(f"Synthetic demo: http://127.0.0.1:{server.server_port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
        return
    if args.command == "catalog":
        result = {"skills": list(SKILLS), "evidence": EVIDENCE}
    elif args.command == "browse":
        try:
            result = browse(args.kind, [s.strip() for s in args.skills.split(",") if s.strip()])
        except ValueError as error:
            parser.error(str(error))
    elif args.command == "detail":
        try:
            result = detail(args.id)
        except ValueError as error:
            parser.error(str(error))
    elif args.command == "compare":
        try:
            result = compare(args.ids)
        except ValueError as error:
            parser.error(str(error))
    elif args.command == "train":
        model = Matcher().model
        result = {"method": "smoothed-tfidf-logtf-l2", "document_count": model.document_count,
                  "corpus_sha256": model.fingerprint, "idf": model.idf}
    elif args.command == "evaluate":
        result = evaluate()
    else:
        try:
            result = Matcher().match({
                "skills": [s.strip() for s in args.skills.split(",") if s.strip()],
                "evidence": [s.strip() for s in args.evidence.split(",") if s.strip()]})
        except ValueError as error:
            parser.error(str(error))
    text = json.dumps(result, indent=2)
    output = getattr(args, "output", None)
    if output:
        path = Path(output)
        temporary = None
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent,
                                             prefix=f".{path.name}.", suffix=".tmp", delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(text + "\n")
            os.replace(temporary, path)
        except OSError as error:
            parser.exit(2, f"Error: Could not write output to {path}. Check the destination and permissions. ({error})\n")
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    print(text)


if __name__ == "__main__":
    main()
