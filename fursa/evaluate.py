"""Held-out, manually labelled synthetic retrieval scenarios, never used to fit."""
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
    canonical = lambda text: tuple(tokens(text))
    assert len({canonical(text) for _, text, _ in CASES}) == len(CASES)
    assert not {canonical(text) for _, text, _ in CASES} & {canonical(text) for text in training}
    model = Tfidf(training)
    rows = []
    for id, query, relevant in CASES:
        ranked = [row["id"] for row in model.rank(query, OPPORTUNITIES)]
        hits = len(set(ranked) & relevant)
        rows.append({
            "id": id, "query": query, "relevant": sorted(relevant), "ranked": ranked,
            "recall_at_3": hits / len(relevant) if relevant else None,
            "precision_at_3": hits / 3 if relevant else None,
            "reciprocal_rank": next((1 / (i + 1) for i, item in enumerate(ranked)
                                     if item in relevant), 0) if relevant else None,
            "correct_abstention": not ranked if not relevant else None,
        })
    positive = [row for row in rows if row["relevant"]]
    negative = [row for row in rows if not row["relevant"]]
    return {
        "fit_documents": model.document_count, "vocabulary_size": len(model.idf),
        "corpus_sha256": model.fingerprint, "held_out_cases": len(rows),
        "positive_cases": len(positive), "negative_cases": len(negative),
        "mean_recall_at_3": sum(row["recall_at_3"] for row in positive) / len(positive),
        "mean_precision_at_3": sum(row["precision_at_3"] for row in positive) / len(positive),
        "mean_reciprocal_rank": sum(row["reciprocal_rank"] for row in positive) / len(positive),
        "negative_abstention_rate": sum(row["correct_abstention"] for row in negative) / len(negative),
        "cases": rows,
    }
