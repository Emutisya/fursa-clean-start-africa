"""Inspect model audit files; never load them as runtime weights."""
import math

from .catalog import fingerprint
from .model import Matcher, MIN_SIMILARITY


def model_snapshot():
    model = Matcher().model
    return {
        "schema": "fursa.tfidf-audit.v1", "synthetic": True, "human_review_required": True,
        "method": "smoothed-tfidf-logtf-l2", "tokenizer": "lowercase-ascii-alphabetic",
        "document_count": model.document_count, "corpus_sha256": model.fingerprint,
        "catalog_sha256": fingerprint(), "minimum_similarity": MIN_SIMILARITY,
        "idf": dict(model.idf), "document_frequencies": dict(model.document_frequencies),
    }


def verify_snapshot(snapshot):
    expected = model_snapshot()
    if not isinstance(snapshot, dict) or set(snapshot) != set(expected):
        raise ValueError("Use the exact versioned synthetic model audit schema.")
    for field in set(expected) - {"idf", "document_frequencies"}:
        if type(snapshot[field]) is not type(expected[field]) or snapshot[field] != expected[field]:
            raise ValueError("Model audit provenance/settings differ from the current synthetic catalogue.")
    if not isinstance(snapshot["idf"], dict) or set(snapshot["idf"]) != set(expected["idf"]):
        raise ValueError("Model audit vocabulary differs from the current fitted vocabulary.")
    for term, weight in snapshot["idf"].items():
        if (type(weight) not in (int, float) or not math.isfinite(weight)
                or not math.isclose(weight, expected["idf"][term], rel_tol=0, abs_tol=1e-12)):
            raise ValueError("Model audit IDF weights do not match a current deterministic fit.")
    frequencies = snapshot["document_frequencies"]
    if (not isinstance(frequencies, dict) or set(frequencies) != set(expected["document_frequencies"])
            or any(type(count) is not int or count != expected["document_frequencies"][term]
                   for term, count in frequencies.items())):
        raise ValueError("Model audit document frequencies do not match the current fit.")
    return {
        "synthetic": True, "human_review_required": True, "matches_current_fit": True,
        "corpus_sha256": expected["corpus_sha256"], "catalog_sha256": expected["catalog_sha256"],
        "message": "Current-fit audit consistency only, not a signature, credential or runtime weight import.",
    }
