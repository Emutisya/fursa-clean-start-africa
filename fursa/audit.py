"""Inspect model audit files; never load them as runtime weights."""
import math
import re

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
    validate_snapshot(snapshot)
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


def validate_snapshot(snapshot):
    expected = model_snapshot()
    if not isinstance(snapshot, dict) or set(snapshot) != set(expected):
        raise ValueError("Use the exact versioned synthetic model audit schema.")
    for field in ("schema", "synthetic", "human_review_required", "method", "tokenizer"):
        if type(snapshot[field]) is not type(expected[field]) or snapshot[field] != expected[field]:
            raise ValueError("Only the unverified synthetic TF-IDF audit method is supported.")
    count = snapshot["document_count"]
    cutoff = snapshot["minimum_similarity"]
    if type(count) is not int or not 1 <= count <= 1024:
        raise ValueError("Audit document count must be an integer from 1 through 1024.")
    if type(cutoff) not in (int, float) or not math.isfinite(cutoff) or not 0 < cutoff <= 1:
        raise ValueError("Audit cutoff must be a finite positive cosine bound.")
    for field in ("corpus_sha256", "catalog_sha256"):
        value = snapshot[field]
        if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
            raise ValueError("Audit provenance must contain SHA-256 hex fingerprints.")
    idf, frequencies = snapshot["idf"], snapshot["document_frequencies"]
    if (not isinstance(idf, dict) or not 1 <= len(idf) <= 4096
            or not isinstance(frequencies, dict) or set(idf) != set(frequencies)):
        raise ValueError("Audit vocabulary and frequencies must have identical bounded term sets.")
    for term, weight in idf.items():
        frequency = frequencies[term]
        if (not isinstance(term, str) or re.fullmatch(r"[a-z]+", term) is None
                or type(frequency) is not int or not 1 <= frequency <= count
                or type(weight) not in (int, float) or not math.isfinite(weight)
                or not math.isclose(weight, math.log((1 + count) / (1 + frequency)) + 1,
                                    rel_tol=0, abs_tol=1e-12)):
            raise ValueError("Audit terms, frequencies and smoothed IDF weights are inconsistent.")


def compare_snapshots(before, after):
    validate_snapshot(before)
    validate_snapshot(after)
    old, new = before["idf"], after["idf"]
    common = sorted(set(old) & set(new))
    return {
        "synthetic": True, "human_review_required": True,
        "corpus_changed": before["corpus_sha256"] != after["corpus_sha256"],
        "catalog_changed": before["catalog_sha256"] != after["catalog_sha256"],
        "document_count_delta": after["document_count"] - before["document_count"],
        "cutoff_before": before["minimum_similarity"], "cutoff_after": after["minimum_similarity"],
        "added_terms": sorted(set(new) - set(old)), "removed_terms": sorted(set(old) - set(new)),
        "changed_terms": [
            {"term": term, "idf_delta": new[term] - old[term],
             "frequency_before": before["document_frequencies"][term],
             "frequency_after": after["document_frequencies"][term]}
            for term in common if new[term] != old[term]
            or before["document_frequencies"][term] != after["document_frequencies"][term]
        ],
        "message": "Recorded lexical fit-statistic differences only; historical provenance is not authenticated and no weights are loaded.",
    }
