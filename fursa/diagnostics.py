"""Bounded offline consistency checks, not deployment certification."""
import json

from .audit import model_snapshot, verify_snapshot
from .catalog import EVIDENCE, SKILLS, validate_catalog
from .evaluate import evaluate
from .model import Matcher, SelectionError
from .passport import export_passport, import_passport
from .reporting import validate_report


def doctor():
    checks = []

    def run(name, action):
        try:
            details = action()
        except (ValueError, OSError) as error:
            checks.append({"check": name, "status": "failed", "message": str(error)})
        else:
            checks.append({"check": name, "status": "passed", "details": details})

    def benchmark(kind):
        report = validate_report(evaluate(kind))
        return {"cases": report["held_out_cases"], "benchmark_sha256": report["benchmark_sha256"]}

    def passport_roundtrip():
        selection = {"skills": ["carpentry"], "evidence": ["e-carpentry"]}
        envelope = export_passport(selection)
        if import_passport(json.dumps(envelope).encode("utf-8")) != selection:
            raise ValueError("Synthetic passport round trip disagrees with selected catalogue IDs.")
        return {"schema": envelope["schema"], "verification": envelope["verification"]}

    def inference_boundaries():
        matcher = Matcher()
        matched = matcher.match({"skills": ["carpentry"]})
        gap = matcher.match({"skills": ["astronomy"]})
        if (not matched["opportunities"] or matched["opportunities"][0]["id"] != "o-timber"
                or not gap["no_match"] or gap["pathways"]):
            raise ValueError("Catalogue inference fixtures failed; inspect model and coverage before using the demo.")
        try:
            matcher.match({"skills": ["solar"], "name": "synthetic rejected field"})
        except SelectionError as error:
            if error.code != "selection_unknown_fields":
                raise ValueError("Unknown-field exclusion returned an unexpected recovery category.") from error
        else:
            raise ValueError("Unknown personal fields were accepted; do not use this build.")
        return {"synthetic_match": "o-timber", "unsupported_skill_abstained": True, "unknown_fields_rejected": True}

    def evidence_invariance():
        result = Matcher().evidence_audit({"skills": list(SKILLS)})
        if not result["all_rankings_unchanged"] or len(result["scenarios"]) != len(EVIDENCE):
            raise ValueError("Evidence flags changed lexical rankings or a simulated toggle was omitted.")
        return {"simulated_toggles": len(result["scenarios"]), "ranking_unchanged": True}

    run("catalogue_integrity", validate_catalog)
    run("current_fit_audit", lambda: verify_snapshot(model_snapshot()))
    run("opportunity_benchmark_arithmetic", lambda: benchmark("opportunity"))
    run("pathway_benchmark_arithmetic", lambda: benchmark("pathway"))
    run("passport_roundtrip", passport_roundtrip)
    run("inference_boundaries", inference_boundaries)
    run("evidence_invariance", evidence_invariance)
    return {
        "synthetic": True, "human_review_required": True,
        "ready": all(row["status"] == "passed" for row in checks), "checks": checks,
        "message": "Offline prototype consistency only. No server connectivity, security, fairness, credential or deployment certification.",
    }
