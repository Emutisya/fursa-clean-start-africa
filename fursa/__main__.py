import argparse
import json
from pathlib import Path

from .catalog import EVIDENCE, SKILLS
from .evaluate import evaluate
from .model import Matcher
from .server import make_server


def main():
    parser = argparse.ArgumentParser(description="Fursa | synthetic skill-first discovery")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("catalog")
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
    if args.command == "serve":
        server = make_server(args.port)
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
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
