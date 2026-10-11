"""Learned smoothed TF-IDF with L2-normalized cosine retrieval, stdlib only."""
import hashlib
import json
import math
import re
from copy import deepcopy
from collections import Counter
from types import MappingProxyType

from .catalog import EVIDENCE, OPPORTUNITIES, PATHWAYS, SKILLS, corpus, document, fingerprint, validate_catalog

TOKEN = re.compile(r"[a-z]+")
MIN_SIMILARITY = 0.08


class SelectionError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def tokens(text):
    return TOKEN.findall(text.lower())


class Tfidf:
    def __init__(self, documents):
        if (not isinstance(documents, (list, tuple)) or not documents
                or any(not isinstance(text, str) or not tokens(text) for text in documents)):
            raise ValueError("Training requires a nonempty sequence of documents with tokenizable text.")
        docs = [tokens(text) for text in documents]
        frequencies = Counter(term for doc in docs for term in set(doc))
        self.idf = {term: math.log((1 + len(docs)) / (1 + count)) + 1
                    for term, count in sorted(frequencies.items())}
        self.document_count = len(docs)
        self.document_frequencies = dict(sorted(frequencies.items()))
        self.fingerprint = hashlib.sha256(
            json.dumps(documents, ensure_ascii=True).encode()).hexdigest()

    def vector(self, text):
        if not isinstance(text, str):
            raise ValueError("Retrieval text must be a string.")
        values = {term: (1 + math.log(count)) * self.idf[term]
                  for term, count in Counter(tokens(text)).items() if term in self.idf}
        norm = math.sqrt(sum(value * value for value in values.values()))
        return {term: value / norm for term, value in values.items()} if norm else {}

    def diagnostics(self, text):
        if not isinstance(text, str):
            raise ValueError("Retrieval text must be a string.")
        terms = Counter(tokens(text))
        known = sorted(set(terms) & set(self.idf))
        unknown = sorted(set(terms) - set(self.idf))
        return {
            "token_count": sum(terms.values()), "unique_term_count": len(terms),
            "known_terms": known, "unknown_terms": unknown,
            "known_token_fraction": sum(terms[term] for term in known) / sum(terms.values()) if terms else 0,
            "has_vector": bool(known),
        }

    def rank(self, text, items, limit=3, *, candidate_vectors=None):
        if type(limit) is not int or limit < 1:
            raise ValueError("Retrieval limit must be a positive integer.")
        query = self.vector(text)
        scored = []
        for item in items:
            source = document(item)
            candidate = candidate_vectors.get(source) if candidate_vectors is not None else None
            if candidate is None:
                candidate = self.vector(source)
            contributions = {term: value * candidate.get(term, 0)
                             for term, value in query.items() if term in candidate}
            score = sum(contributions.values())
            if score >= MIN_SIMILARITY:
                scored.append((score, {**deepcopy(item), "similarity": round(score, 6),
                               "term_contributions": [
                                   {"term": term, "cosine_contribution": contributions[term],
                                    "query_weight": query[term], "resource_weight": candidate[term]}
                                   for term in sorted(contributions, key=lambda term: (-contributions[term], term))
                               ],
                               "shared_terms": sorted(contributions,
                                                      key=lambda term: (-contributions[term], term))[:6]}))
        return [row for _, row in sorted(scored, key=lambda item: (-item[0], item[1]["id"]))[:limit]]

    def audit(self, text, items):
        query = self.vector(text)
        scored = []
        for item in items:
            candidate = self.vector(document(item))
            score = sum(value * candidate.get(term, 0) for term, value in query.items())
            scored.append({"id": item["id"], "cosine": score, "passes_cutoff": score >= MIN_SIMILARITY,
                           "cutoff_margin": score - MIN_SIMILARITY})
        return sorted(scored, key=lambda row: (-row["cosine"], row["id"]))


def validate(payload):
    if not isinstance(payload, dict):
        raise SelectionError("selection_object_required", "Send an object containing skills and optional evidence.")
    if set(payload) - {"skills", "evidence"}:
        raise SelectionError("selection_unknown_fields", "Only skills and evidence are accepted. Do not submit personal or sensitive data.")
    skills = payload.get("skills")
    evidence = payload.get("evidence", [])
    if not isinstance(skills, list) or not 1 <= len(skills) <= len(SKILLS):
        raise SelectionError("selection_skill_count", "Choose at least one catalogued skill (maximum 13).")
    if any(not isinstance(s, str) or s not in SKILLS for s in skills):
        raise SelectionError("selection_unknown_skill", "Use exact catalogued skill names; free-text biographies are not accepted.")
    if len(set(skills)) != len(skills):
        raise SelectionError("selection_duplicate_skill", "Choose each skill only once.")
    allowed = {row["id"]: row["skill"] for row in EVIDENCE}
    if not isinstance(evidence, list) or len(evidence) > len(EVIDENCE):
        raise SelectionError("selection_evidence_list", "Evidence must be a list of simulated catalogued evidence IDs.")
    if any(not isinstance(e, str) or e not in allowed for e in evidence):
        raise SelectionError("selection_unknown_evidence", "Choose only simulated catalogued evidence IDs.")
    if len(set(evidence)) != len(evidence):
        raise SelectionError("selection_duplicate_evidence", "Select each evidence item once.")
    if any(allowed[e] not in skills for e in evidence):
        raise SelectionError("selection_cross_skill_evidence", "Choose evidence only for your selected skills.")
    return sorted(skills), sorted(evidence)


class Matcher:
    def __init__(self):
        validate_catalog()
        self.model = Tfidf(corpus())
        self._resource_vectors = MappingProxyType({
            document(row): MappingProxyType(self.model.vector(document(row)))
            for row in OPPORTUNITIES + PATHWAYS
        })

    def inspect(self):
        return {
            "synthetic": True, "human_review_required": True,
            "method": "smoothed-tfidf-logtf-l2", "corpus_sha256": self.model.fingerprint,
            "fit_documents": self.model.document_count, "vocabulary_size": len(self.model.idf),
            "terms": [
                {"term": term, "idf": weight,
                 "document_frequency": self.model.document_frequencies[term]}
                for term, weight in self.model.idf.items()
            ],
            "resources": [
                {"id": row["id"], "kind": row["kind"],
                 "vector_terms": len(vector), "squared_norm": sum(value * value for value in vector.values())}
                for row in sorted(OPPORTUNITIES + PATHWAYS, key=lambda row: row["id"])
                for vector in [self.model.vector(document(row))]
            ],
            "message": "Inspect fitted fictional lexical statistics, not measured human performance.",
        }

    def inspect_term(self, term):
        if not isinstance(term, str) or term not in self.model.idf:
            raise ValueError("Use one exact fitted vocabulary term from inspect.")
        sources = [(row["id"], document(row)) for row in OPPORTUNITIES + PATHWAYS]
        sources += [("skill:" + skill, text) for skill, text in SKILLS.items()]
        return {
            "synthetic": True, "human_review_required": True,
            "term": term, "idf": self.model.idf[term],
            "document_frequency": self.model.document_frequencies[term],
            "sources": [
                {"id": identifier, "term_count": count,
                 "normalized_weight": self.model.vector(text)[term]}
                for identifier, text in sorted(sources)
                for count in [tokens(text).count(term)] if count
            ],
            "message": "Fictional fit-text occurrences and weights, not real-world skill importance.",
        }

    def sensitivity(self, payload):
        skills, _ = validate(payload)
        baseline = self.match(payload)
        old_ids = {row["id"] for row in baseline["opportunities"]}
        scenarios = []
        for omitted in skills:
            remaining = [skill for skill in skills if skill != omitted]
            query = " ".join(SKILLS[skill] for skill in remaining)
            rows = self.model.rank(query, OPPORTUNITIES) if remaining else []
            new_ids = {row["id"] for row in rows}
            scenarios.append({
                "omitted_skill": omitted, "remaining_skills": remaining,
                "empty_selection": not remaining,
                "ranked": [row["id"] for row in rows],
                "no_longer_returned": sorted(old_ids - new_ids),
                "newly_returned": sorted(new_ids - old_ids),
                "result_set_jaccard": len(old_ids & new_ids) / len(old_ids | new_ids) if old_ids | new_ids else 1,
            })
        return {
            "synthetic": True, "human_review_required": True,
            "baseline": [row["id"] for row in baseline["opportunities"]],
            "scenarios": scenarios,
            "message": "Leave-one-selection-out lexical sensitivity, not causal skill value or ability.",
        }

    def audit(self, payload):
        skills, _ = validate(payload)
        query = " ".join(SKILLS[skill] for skill in skills)
        return {
            "synthetic": True, "human_review_required": True,
            "minimum_similarity": MIN_SIMILARITY,
            "opportunities": self.model.audit(query, OPPORTUNITIES),
            "pathways": self.model.audit(query, PATHWAYS),
            "message": "All fictional resource cosines, including rejected results; not suitability or confidence.",
        }

    def batch(self, selections):
        if not isinstance(selections, list) or not 1 <= len(selections) <= 16:
            raise ValueError("Batch discovery requires one to sixteen synthetic selection objects.")
        for selection in selections:
            validate(selection)
        return {
            "synthetic": True, "human_review_required": True,
            "results": [{"index": index, "result": self.match(selection)}
                        for index, selection in enumerate(selections)],
            "message": "Bounded synthetic scenarios, not a batch of personal profiles or comparative ability scores.",
        }

    def evidence_audit(self, payload):
        skills, evidence = validate(payload)
        baseline = self.match(payload)
        signature = lambda result: {
            kind: [(row["id"], row["similarity"], row["term_contributions"]) for row in result[kind]]
            for kind in ("opportunities", "pathways")
        }
        scenarios = []
        for sample in EVIDENCE:
            if sample["skill"] not in skills:
                continue
            toggled = sorted(set(evidence) ^ {sample["id"]})
            changed = self.match({"skills": skills, "evidence": toggled})
            before = {row["id"]: row["evidence_gaps"] for row in baseline["opportunities"]}
            after = {row["id"]: row["evidence_gaps"] for row in changed["opportunities"]}
            scenarios.append({
                "sample": sample["id"], "selected_before": sample["id"] in evidence,
                "selected_after": sample["id"] in toggled,
                "ranking_unchanged": signature(baseline) == signature(changed),
                "gap_changes": [
                    {"resource": identifier, "before": before[identifier], "after": after.get(identifier)}
                    for identifier in sorted(before) if before[identifier] != after.get(identifier)
                ],
            })
        return {
            "synthetic": True, "human_review_required": True,
            "all_rankings_unchanged": all(row["ranking_unchanged"] for row in scenarios),
            "scenarios": scenarios,
            "message": "Synthetic evidence-toggle invariance audit. Gap changes never verify evidence or competence.",
        }

    def overlap_review(self, payload):
        skills, _ = validate(payload)
        result = self.match(payload)
        query = " ".join(SKILLS[skill] for skill in skills)
        reviews = {}
        for kind, resources in (("opportunities", OPPORTUNITIES), ("pathways", PATHWAYS)):
            visible = {row["id"] for row in result[kind]}
            scores = {row["id"]: row for row in self.model.audit(query, resources)}
            reviews[kind] = {
                "lexical_only_returned": sorted(row["id"] for row in result[kind] if not row["shared_skills"]),
                "declared_overlap": [
                    {"id": row["id"], "shared_skills": sorted(set(skills) & set(row["skills"])),
                     "returned": row["id"] in visible,
                     "not_returned_reason": None if row["id"] in visible else
                         "outside_top_three" if scores[row["id"]]["passes_cutoff"] else "below_lexical_cutoff"}
                    for row in sorted(resources, key=lambda row: row["id"]) if set(skills) & set(row["skills"])
                ],
            }
        return {
            "synthetic": True, "human_review_required": True, "reviews": reviews,
            "message": "Declared catalogue overlap versus lexical retrieval, not relevance ground truth, verified skill or eligibility.",
        }

    def match(self, payload, limit=3):
        from .passport import export_passport

        if type(limit) is not int or not 1 <= limit <= 12:
            raise ValueError("Discovery limit must be an integer from 1 to 12.")
        skills, evidence = validate(payload)
        query = " ".join(SKILLS[skill] for skill in skills)
        matches = self.model.rank(query, OPPORTUNITIES, limit, candidate_vectors=self._resource_vectors)
        pathways = self.model.rank(query, PATHWAYS, limit, candidate_vectors=self._resource_vectors)
        for row in matches + pathways:
            row["shared_skills"] = sorted(set(skills) & set(row["skills"]))
            row["skills_to_explore"] = sorted(set(row["skills"]) - set(skills))
            row["evidence_gaps"] = [e["title"] for e in EVIDENCE
                                    if e["skill"] in row["skills"] and e["id"] not in evidence]
        return {
            "synthetic": True, "human_review_required": True,
            "provenance": {
                "method": "smoothed-tfidf-logtf-l2", "corpus_sha256": self.model.fingerprint,
                "catalog_sha256": fingerprint(), "minimum_similarity": MIN_SIMILARITY,
                "limit": limit, "tie_break": "full-precision cosine descending, then resource ID ascending",
                "query_sha256": hashlib.sha256(query.encode("utf-8")).hexdigest(),
            },
            "passport": {"skills": skills, "evidence": evidence, "verification": "Unverified synthetic selections"},
            "portable_passport": export_passport({"skills": skills, "evidence": evidence}),
            "opportunities": matches,
            "pathways": pathways,
            "message": "Discovery only. Similarities are not probabilities, employability scores or hiring decisions.",
            "no_match": not matches,
            "diagnostics": {
                **self.model.diagnostics(query),
                "skills_without_opportunities": sorted(
                    skill for skill in skills if not any(skill in row["skills"] for row in OPPORTUNITIES)),
                "skills_without_pathways": sorted(
                    skill for skill in skills if not any(skill in row["skills"] for row in PATHWAYS)),
                "no_match_reason": "No catalogue opportunity met the lexical cutoff." if not matches else None,
            },
        }
