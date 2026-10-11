"""Compare recorded synthetic reports without inventing outcome improvements."""
import json
import math
import hashlib

from .jsonio import unique_fields
from .catalog import OPPORTUNITIES, PATHWAYS

METRICS = ("mean_recall_at_3", "mean_ndcg_at_3", "mean_precision_at_3",
           "mean_reciprocal_rank", "negative_abstention_rate")
MAX_REPORT_BYTES = 1048576


def validate_report(report):
    if not isinstance(report, dict):
        raise ValueError("Evaluation report must be an object.")
    if any(type(report.get(field)) is not int or report[field] < 1
           for field in ("held_out_cases", "positive_cases", "negative_cases", "fit_documents", "vocabulary_size")):
        raise ValueError("Evaluation counts must be positive integers, not booleans.")
    for field in ("corpus_sha256", "benchmark_sha256"):
        value = report.get(field)
        if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise ValueError("Evaluation reports require SHA-256 corpus and benchmark provenance.")
    for metric in METRICS:
        value = report.get(metric)
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError("Evaluation metrics must be finite numbers between zero and one.")
    cases = report.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("Evaluation report must include observed cases.")
    ids = []
    kind = report.get("resource_kind", "opportunity")
    if not isinstance(kind, str) or kind not in {"opportunity", "pathway"}:
        raise ValueError("Recorded resource kind must be opportunity or pathway.")
    resources = OPPORTUNITIES if kind == "opportunity" else PATHWAYS
    allowed = {row["id"] for row in resources}
    for case in cases:
        if (not isinstance(case, dict) or not isinstance(case.get("id"), str) or not case["id"].strip()
                or not isinstance(case.get("query"), str) or not case["query"].strip()):
            raise ValueError("Evaluation cases require string IDs.")
        ids.append(case["id"])
        for field in ("ranked", "relevant"):
            values = case.get(field)
            if (not isinstance(values, list) or any(not isinstance(value, str) for value in values)
                    or len(set(values)) != len(values)):
                raise ValueError("Recorded rankings and relevance must be unique string-ID lists.")
        if len(case["ranked"]) > 3:
            raise ValueError("Only top-three reports are comparable.")
        if not set(case["ranked"] + case["relevant"]) <= allowed:
            raise ValueError("Recorded cases must reference known fictional resources of their kind.")
        relevant, ranked = set(case["relevant"]), case["ranked"]
        hits = len(relevant & set(ranked))
        ideal = sum(1 / math.log2(i + 2) for i in range(min(3, len(relevant))))
        expected = {
            "recall_at_3": hits / len(relevant) if relevant else None,
            "precision_at_3": hits / 3 if relevant else None,
            "ndcg_at_3": sum(1 / math.log2(i + 2) for i, value in enumerate(ranked) if value in relevant) / ideal if ideal else None,
            "reciprocal_rank": next((1 / (i + 1) for i, value in enumerate(ranked) if value in relevant), 0) if relevant else None,
        }
        for metric, value in expected.items():
            actual = case.get(metric)
            if (value is None and actual is not None or value is not None
                    and (type(actual) not in (int, float) or not math.isfinite(actual)
                         or not math.isclose(actual, value, rel_tol=0, abs_tol=1e-12))):
                raise ValueError("Per-case evaluation metrics do not match recorded rankings.")
        abstention = case.get("correct_abstention")
        if relevant and abstention is not None or not relevant and (type(abstention) is not bool or abstention != (not ranked)):
            raise ValueError("Per-case abstention must match recorded negative rankings.")
        if "diagnostics" in case:
            diagnostic = case["diagnostics"]
            if (not isinstance(diagnostic, dict) or type(diagnostic.get("returned_count")) is not int
                    or diagnostic["returned_count"] != len(ranked)
                    or diagnostic.get("missed_relevant") != sorted(relevant - set(ranked))
                    or diagnostic.get("irrelevant_returned") != sorted(set(ranked) - relevant)):
                raise ValueError("Case diagnostics disagree with recorded retrievals.")
    if len(set(ids)) != len(ids) or report.get("held_out_cases") != len(cases):
        raise ValueError("Evaluation case counts or IDs are inconsistent.")
    benchmark = hashlib.sha256(json.dumps(
        [(row["id"], row["query"], sorted(row["relevant"])) for row in cases],
        ensure_ascii=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    if benchmark != report["benchmark_sha256"]:
        raise ValueError("Benchmark fingerprint does not describe recorded cases.")
    positive = [row for row in cases if row["relevant"]]
    negative = [row for row in cases if not row["relevant"]]
    if (not positive or not negative or report.get("positive_cases") != len(positive)
            or report.get("negative_cases") != len(negative)):
        raise ValueError("Positive and negative evaluation counts are inconsistent.")
    totals = dict.fromkeys(METRICS, 0)
    for row in positive:
        relevant, ranked = set(row["relevant"]), row["ranked"]
        hits = len(relevant & set(ranked))
        totals["mean_recall_at_3"] += hits / len(relevant)
        totals["mean_precision_at_3"] += hits / 3
        totals["mean_reciprocal_rank"] += next((1 / (i + 1) for i, item in enumerate(ranked) if item in relevant), 0)
        ideal = sum(1 / math.log2(i + 2) for i in range(min(3, len(relevant))))
        totals["mean_ndcg_at_3"] += sum(1 / math.log2(i + 2) for i, item in enumerate(ranked) if item in relevant) / ideal
    for metric in METRICS[:-1]:
        totals[metric] /= len(positive)
    totals["negative_abstention_rate"] = sum(not row["ranked"] for row in negative) / len(negative)
    if any(not math.isclose(report[metric], totals[metric], abs_tol=1e-12, rel_tol=0) for metric in METRICS):
        raise ValueError("Aggregate evaluation metrics do not match recorded rankings.")
    coverage = report.get("resource_coverage")
    if not isinstance(coverage, dict) or set(coverage) != allowed:
        raise ValueError("Resource coverage must enumerate the fictional catalogue for its kind.")
    for identifier in sorted(allowed):
        expected = {
            "relevant_cases": sum(identifier in row["relevant"] for row in cases),
            "retrieved_relevant_cases": sum(identifier in row["relevant"] and identifier in row["ranked"] for row in cases),
            "retrieved_irrelevant_cases": sum(identifier not in row["relevant"] and identifier in row["ranked"] for row in cases),
        }
        actual = coverage[identifier]
        if (not isinstance(actual, dict) or set(actual) != set(expected)
                or any(type(actual[key]) is not int or actual[key] != value for key, value in expected.items())):
            raise ValueError("Resource coverage counts disagree with recorded rankings.")
    return report


def read_report(path):
    with open(path, "rb") as stream:
        raw = stream.read(MAX_REPORT_BYTES + 1)
    if len(raw) > MAX_REPORT_BYTES:
        raise ValueError("Evaluation report exceeds one MiB.")
    try:
        report = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_fields)
    except (ValueError, UnicodeError, RecursionError) as error:
        raise ValueError("Use UTF-8 evaluation JSON without duplicate fields.") from error
    return validate_report(report)


def compare_reports(before, after):
    validate_report(before)
    validate_report(after)
    if before["benchmark_sha256"] != after["benchmark_sha256"]:
        raise ValueError("Benchmark fingerprints differ; metrics are not comparable.")
    old = {case["id"]: case for case in before["cases"]}
    new = {case["id"]: case for case in after["cases"]}
    if set(old) != set(new) or any(old[key]["relevant"] != new[key]["relevant"]
                                   or old[key].get("query") != new[key].get("query") for key in old):
        raise ValueError("Recorded queries or relevance labels differ despite benchmark provenance.")
    return {
        "synthetic": True, "human_review_required": True,
        "corpus_changed": before["corpus_sha256"] != after["corpus_sha256"],
        "benchmark_sha256": before["benchmark_sha256"],
        "metric_deltas": {metric: after[metric] - before[metric] for metric in METRICS},
        "changed_rankings": [
            {"id": key, "before": old[key]["ranked"], "after": new[key]["ranked"]}
            for key in sorted(old) if old[key]["ranked"] != new[key]["ranked"]
        ],
        "message": "Recorded synthetic retrieval differences only, not statistically established or real-user improvements.",
    }
