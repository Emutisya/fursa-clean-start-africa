"""Compare recorded synthetic reports without inventing outcome improvements."""
import json
import math
import hashlib

from .jsonio import unique_fields

METRICS = ("mean_recall_at_3", "mean_ndcg_at_3", "mean_precision_at_3",
           "mean_reciprocal_rank", "negative_abstention_rate")
MAX_REPORT_BYTES = 1048576


def validate_report(report):
    if not isinstance(report, dict):
        raise ValueError("Evaluation report must be an object.")
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
    for case in cases:
        if (not isinstance(case, dict) or not isinstance(case.get("id"), str)
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
