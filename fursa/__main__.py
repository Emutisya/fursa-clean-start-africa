import argparse
import json
import os
import tempfile
from pathlib import Path

from .catalog import EVIDENCE, SKILLS
from .evaluate import baseline_comparison, cutoff_diagnostics, evaluate, evaluation_slices, inspect_case, ranking_curves
from .discovery import browse, combined_review, compare, detail, preview_additions, related, review_plan, skill_map
from .model import Matcher
from .passport import compare_selections, convert_legacy, edit_selections, export_passport, merge_selections, read_passport
from .reporting import compare_reports, read_report
from .jsonio import read_json
from .audit import compare_snapshots, model_snapshot, verify_snapshot
from .server import make_server


def main():
    parser = argparse.ArgumentParser(description="Fursa | synthetic skill-first discovery")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("catalog")
    sub.add_parser("skill-map")
    sub.add_parser("inspect")
    term_parser = sub.add_parser("inspect-term")
    term_parser.add_argument("term")
    browse_parser = sub.add_parser("browse")
    browse_parser.add_argument("--kind", choices=["opportunity", "pathway"], default="opportunity")
    browse_parser.add_argument("--skills", default="", help="All selected skills must occur in an item")
    detail_parser = sub.add_parser("detail")
    detail_parser.add_argument("id", help="Exact fictional resource ID")
    related_parser = sub.add_parser("related")
    related_parser.add_argument("id")
    review_parser = sub.add_parser("review-plan")
    review_parser.add_argument("id")
    review_parser.add_argument("--skills", required=True)
    review_parser.add_argument("--evidence", default="")
    combined_parser = sub.add_parser("combined-review")
    combined_parser.add_argument("ids", nargs="+")
    combined_parser.add_argument("--skills", required=True)
    combined_parser.add_argument("--evidence", default="")
    preview_parser = sub.add_parser("preview-additions")
    preview_parser.add_argument("--skills", required=True)
    sensitivity_parser = sub.add_parser("sensitivity")
    sensitivity_parser.add_argument("--skills", required=True)
    audit_parser = sub.add_parser("audit-ranking")
    audit_parser.add_argument("--skills", required=True)
    compare_parser = sub.add_parser("compare")
    compare_parser.add_argument("ids", nargs="+", help="Two to four distinct fictional IDs")
    train = sub.add_parser("train")
    train.add_argument("--output", default=str(Path("models") / "tfidf.json"))
    verify_model = sub.add_parser("verify-model")
    verify_model.add_argument("path")
    model_compare = sub.add_parser("compare-models")
    model_compare.add_argument("before")
    model_compare.add_argument("after")
    model_compare.add_argument("--output")
    evaluate_parser = sub.add_parser("evaluate")
    evaluate_parser.add_argument("--output")
    evaluate_parser.add_argument("--kind", choices=["opportunity", "pathway"], default="opportunity")
    curves_parser = sub.add_parser("evaluation-curves")
    curves_parser.add_argument("--output")
    cutoffs_parser = sub.add_parser("evaluation-cutoffs")
    cutoffs_parser.add_argument("--output")
    slices_parser = sub.add_parser("evaluation-slices")
    slices_parser.add_argument("--output")
    baselines_parser = sub.add_parser("evaluation-baselines")
    baselines_parser.add_argument("--output")
    case_parser = sub.add_parser("inspect-case")
    case_parser.add_argument("id")
    case_parser.add_argument("--kind", choices=["opportunity", "pathway"], default="opportunity")
    evaluation_compare = sub.add_parser("compare-evaluations")
    evaluation_compare.add_argument("before")
    evaluation_compare.add_argument("after")
    evaluation_compare.add_argument("--output")
    match = sub.add_parser("match")
    match.add_argument("--skills", required=True, help="Comma-separated exact catalogued skills")
    match.add_argument("--evidence", default="", help="Comma-separated simulated evidence IDs")
    match.add_argument("--limit", type=int, choices=range(1, 13), default=3)
    batch_parser = sub.add_parser("match-batch")
    batch_parser.add_argument("path")
    batch_parser.add_argument("--output")
    passport_parser = sub.add_parser("passport")
    passport_parser.add_argument("--skills", required=True)
    passport_parser.add_argument("--evidence", default="")
    passport_parser.add_argument("--output")
    import_parser = sub.add_parser("import-passport")
    import_parser.add_argument("path")
    legacy_parser = sub.add_parser("convert-legacy-passport")
    legacy_parser.add_argument("path")
    legacy_parser.add_argument("--output")
    passport_compare = sub.add_parser("compare-passports")
    passport_compare.add_argument("before")
    passport_compare.add_argument("after")
    passport_merge = sub.add_parser("merge-passports")
    passport_merge.add_argument("paths", nargs="+")
    passport_merge.add_argument("--output")
    passport_edit = sub.add_parser("edit-passport")
    passport_edit.add_argument("path")
    for field in ("add-skills", "remove-skills", "add-evidence", "remove-evidence"):
        passport_edit.add_argument("--" + field, default="")
    passport_edit.add_argument("--output")
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
    elif args.command == "skill-map":
        result = skill_map()
    elif args.command == "inspect":
        result = Matcher().inspect()
    elif args.command == "inspect-term":
        try:
            result = Matcher().inspect_term(args.term)
        except ValueError as error:
            parser.error(str(error))
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
    elif args.command == "related":
        try:
            result = related(args.id)
        except ValueError as error:
            parser.error(str(error))
    elif args.command == "review-plan":
        try:
            result = review_plan(args.id, {
                "skills": [s.strip() for s in args.skills.split(",") if s.strip()],
                "evidence": [s.strip() for s in args.evidence.split(",") if s.strip()],
            })
        except ValueError as error:
            parser.error(str(error))
    elif args.command == "combined-review":
        try:
            result = combined_review(args.ids, {
                "skills": [s.strip() for s in args.skills.split(",") if s.strip()],
                "evidence": [s.strip() for s in args.evidence.split(",") if s.strip()],
            })
        except ValueError as error:
            parser.error(str(error))
    elif args.command == "preview-additions":
        try:
            result = preview_additions({"skills": [s.strip() for s in args.skills.split(",") if s.strip()]})
        except ValueError as error:
            parser.error(str(error))
    elif args.command == "sensitivity":
        try:
            result = Matcher().sensitivity({"skills": [s.strip() for s in args.skills.split(",") if s.strip()]})
        except ValueError as error:
            parser.error(str(error))
    elif args.command == "audit-ranking":
        try:
            result = Matcher().audit({"skills": [s.strip() for s in args.skills.split(",") if s.strip()]})
        except ValueError as error:
            parser.error(str(error))
    elif args.command == "compare":
        try:
            result = compare(args.ids)
        except ValueError as error:
            parser.error(str(error))
    elif args.command == "train":
        result = model_snapshot()
    elif args.command == "verify-model":
        try:
            result = verify_snapshot(read_json(args.path, 1048576))
        except (ValueError, OSError) as error:
            parser.error(str(error))
    elif args.command == "compare-models":
        try:
            result = compare_snapshots(read_json(args.before, 1048576), read_json(args.after, 1048576))
        except (ValueError, OSError) as error:
            parser.error(str(error))
    elif args.command == "evaluate":
        result = evaluate(args.kind)
    elif args.command == "evaluation-curves":
        result = ranking_curves()
    elif args.command == "evaluation-cutoffs":
        result = cutoff_diagnostics()
    elif args.command == "evaluation-slices":
        result = evaluation_slices()
    elif args.command == "evaluation-baselines":
        result = baseline_comparison()
    elif args.command == "inspect-case":
        try:
            result = inspect_case(args.id, args.kind)
        except ValueError as error:
            parser.error(str(error))
    elif args.command == "compare-evaluations":
        try:
            result = compare_reports(read_report(args.before), read_report(args.after))
        except (ValueError, OSError) as error:
            parser.error(str(error))
    elif args.command == "match-batch":
        try:
            selections = read_json(args.path, 32768)
            result = Matcher().batch(selections)
        except (ValueError, OSError) as error:
            parser.error(str(error))
    elif args.command == "import-passport":
        try:
            result = Matcher().match(read_passport(args.path))
        except (ValueError, OSError) as error:
            parser.error(str(error))
    elif args.command == "convert-legacy-passport":
        try:
            result = convert_legacy(read_json(args.path, 16384))
        except (ValueError, OSError) as error:
            parser.error(str(error))
    elif args.command == "compare-passports":
        try:
            result = compare_selections(read_passport(args.before), read_passport(args.after))
        except (ValueError, OSError) as error:
            parser.error(str(error))
    elif args.command == "merge-passports":
        try:
            if not 2 <= len(args.paths) <= 4:
                raise ValueError("Merge two to four versioned synthetic passport files.")
            result = merge_selections([read_passport(path) for path in args.paths])
        except (ValueError, OSError) as error:
            parser.error(str(error))
    elif args.command == "edit-passport":
        try:
            result = edit_selections(read_passport(args.path), {
                field: [s.strip() for s in getattr(args, field).split(",") if s.strip()]
                for field in ("add_skills", "remove_skills", "add_evidence", "remove_evidence")
            })
        except (ValueError, OSError) as error:
            parser.error(str(error))
    else:
        try:
            payload = {
                "skills": [s.strip() for s in args.skills.split(",") if s.strip()],
                "evidence": [s.strip() for s in args.evidence.split(",") if s.strip()]}
            result = export_passport(payload) if args.command == "passport" else Matcher().match(payload, args.limit)
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
