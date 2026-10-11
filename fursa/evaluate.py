"""Held-out, manually labelled synthetic retrieval scenarios, never used to fit."""
import hashlib
import json
import math
from collections import Counter
from .catalog import OPPORTUNITIES, corpus
from .model import Tfidf, tokens

CASES = [
    ("q01", "timber furniture measuring assembly", {"o-timber"}),
    ("q02", "metal joints welding fabrication", {"o-metal"}),
    ("q03", "photovoltaic panels circuits wiring", {"o-solar"}),
    ("q04", "garments fabric sewing stitching", {"o-textile"}),
    ("q05", "cooking preparation hygiene kitchen", {"o-kitchen"}),
    ("q06", "invoices reconciliation bookkeeping formulas", {"o-accounts"}),
    ("q07", "warehouse dispatch delivery enquiries", {"o-dispatch"}),
    ("q08", "seedlings irrigation horticulture", {"o-nursery"}),
    ("q09", "pipes leaks plumbing fittings", {"o-water"}),
    ("q10", "furniture timber welding metal", {"o-timber", "o-metal"}),
    ("q11", "astronomy telescope galaxies", set()),
    ("q12", "xylophone sonatas oboe", set()),
    ("q13", "woodwork cabinetry dovetails sanding", {"o-timber"}),
    ("q14", "tailor clothing needle alteration", {"o-textile"}),
]


def evaluate():
    training = corpus()
    canonical = lambda text: tuple(sorted(Counter(tokens(text)).items()))
    if (not isinstance(CASES, (list, tuple)) or any(
            not isinstance(case, (list, tuple)) or len(case) != 3
            or not isinstance(case[0], str) or not case[0].strip()
            or not isinstance(case[1], str) or not tokens(case[1])
            or not isinstance(case[2], (set, frozenset))
            or any(not isinstance(identifier, str) for identifier in case[2])
            for case in CASES)):
        raise ValueError("Evaluation cases require an ID, usable query text and a set of resource IDs.")
    if not CASES or not any(relevant for _, _, relevant in CASES) or not any(not relevant for _, _, relevant in CASES):
        raise ValueError("Evaluation requires both relevant and unmatched queries.")
    ids = [identifier for identifier, _, _ in CASES]
    queries = [canonical(text) for _, text, _ in CASES]
    if len(set(ids)) != len(ids) or len(set(queries)) != len(queries):
        raise ValueError("Duplicate evaluation ID or query.")
    if set(queries) & {canonical(text) for text in training}:
        raise ValueError("Exact training/evaluation query overlap.")
    allowed = {row["id"] for row in OPPORTUNITIES}
    if any(not isinstance(relevant, (set, frozenset)) or not relevant <= allowed for _, _, relevant in CASES):
        raise ValueError("Evaluation relevance labels must reference catalogued opportunities.")
    model = Tfidf(training)
    rows = []
    for id, query, relevant in CASES:
        results = model.rank(query, OPPORTUNITIES)
        ranked = [row["id"] for row in results]
        hits = len(set(ranked) & relevant)
        dcg = sum(1 / math.log2(i + 2) for i, item in enumerate(ranked) if item in relevant)
        ideal = sum(1 / math.log2(i + 2) for i in range(min(3, len(relevant))))
        rows.append({
            "id": id, "query": query, "relevant": sorted(relevant), "ranked": ranked,
            "recall_at_3": hits / len(relevant) if relevant else None,
            "ndcg_at_3": dcg / ideal if ideal else None,
            "precision_at_3": hits / 3 if relevant else None,
            "reciprocal_rank": next((1 / (i + 1) for i, item in enumerate(ranked)
                                     if item in relevant), 0) if relevant else None,
            "correct_abstention": not ranked if not relevant else None,
            "diagnostics": {
                **model.diagnostics(query),
                "returned_count": len(ranked),
                "missed_relevant": sorted(relevant - set(ranked)),
                "irrelevant_returned": sorted(set(ranked) - relevant),
                "outcome": (
                    "correct_abstention" if not relevant and not ranked else
                    "false_positive" if not relevant else
                    "missed_relevant" if not hits else
                    "partial_recall" if hits < len(relevant) else "all_relevant_retrieved"
                ),
                "results": [{"id": row["id"], "similarity": row["similarity"],
                             "relevant": row["id"] in relevant, "shared_terms": row["shared_terms"]}
                            for row in results],
            },
        })
    positive = [row for row in rows if row["relevant"]]
    negative = [row for row in rows if not row["relevant"]]
    coverage = {
        identifier: {
            "relevant_cases": sum(identifier in row["relevant"] for row in rows),
            "retrieved_relevant_cases": sum(identifier in row["relevant"] and identifier in row["ranked"] for row in rows),
            "retrieved_irrelevant_cases": sum(identifier not in row["relevant"] and identifier in row["ranked"] for row in rows),
        } for identifier in sorted(allowed)
    }
    return {
        "fit_documents": model.document_count, "vocabulary_size": len(model.idf),
        "corpus_sha256": model.fingerprint, "held_out_cases": len(rows),
        "benchmark_sha256": hashlib.sha256(json.dumps(
            [(identifier, query, sorted(relevant)) for identifier, query, relevant in CASES],
            ensure_ascii=True, separators=(",", ":"),
        ).encode("utf-8")).hexdigest(),
        "positive_cases": len(positive), "negative_cases": len(negative),
        "mean_recall_at_3": sum(row["recall_at_3"] for row in positive) / len(positive),
        "mean_ndcg_at_3": sum(row["ndcg_at_3"] for row in positive) / len(positive),
        "mean_precision_at_3": sum(row["precision_at_3"] for row in positive) / len(positive),
        "mean_reciprocal_rank": sum(row["reciprocal_rank"] for row in positive) / len(positive),
        "negative_abstention_rate": sum(row["correct_abstention"] for row in negative) / len(negative),
        "cases": rows,
        "resource_coverage": coverage,
    }


def ranking_curves():
    baseline = evaluate()
    model = Tfidf(corpus())
    predictions = [(relevant, [row["id"] for row in model.rank(query, OPPORTUNITIES, len(OPPORTUNITIES))])
                   for _, query, relevant in CASES]
    positive = [(relevant, ranked) for relevant, ranked in predictions if relevant]
    curves = []
    for k in range(1, len(OPPORTUNITIES) + 1):
        recalls, precisions, gains = [], [], []
        for relevant, ranked in positive:
            hits = len(set(ranked[:k]) & relevant)
            recalls.append(hits / len(relevant))
            precisions.append(hits / k)
            ideal = sum(1 / math.log2(i + 2) for i in range(min(k, len(relevant))))
            gains.append(sum(1 / math.log2(i + 2) for i, identifier in enumerate(ranked[:k])
                             if identifier in relevant) / ideal)
        curves.append({
            "k": k, "mean_recall": sum(recalls) / len(recalls),
            "mean_precision": sum(precisions) / len(precisions),
            "mean_ndcg": sum(gains) / len(gains),
        })
    return {
        "synthetic": True, "human_review_required": True,
        "corpus_sha256": baseline["corpus_sha256"], "benchmark_sha256": baseline["benchmark_sha256"],
        "positive_cases": len(positive), "curves": curves,
        "message": "Synthetic positive-query depth diagnostics at the unchanged cutoff, not outcome estimates.",
    }
