"""Learned smoothed TF-IDF with L2-normalized cosine retrieval, stdlib only."""
import hashlib
import json
import math
import re
from collections import Counter

from .catalog import EVIDENCE, OPPORTUNITIES, PATHWAYS, SKILLS, corpus, document

TOKEN = re.compile(r"[a-z]+")
MIN_SIMILARITY = 0.08


def tokens(text):
    return TOKEN.findall(text.lower())


class Tfidf:
    def __init__(self, documents):
        docs = [tokens(text) for text in documents]
        frequencies = Counter(term for doc in docs for term in set(doc))
        self.idf = {term: math.log((1 + len(docs)) / (1 + count)) + 1
                    for term, count in sorted(frequencies.items())}
        self.document_count = len(docs)
        self.fingerprint = hashlib.sha256(
            json.dumps(documents, ensure_ascii=True).encode()).hexdigest()

    def vector(self, text):
        values = {term: (1 + math.log(count)) * self.idf[term]
                  for term, count in Counter(tokens(text)).items() if term in self.idf}
        norm = math.sqrt(sum(value * value for value in values.values()))
        return {term: value / norm for term, value in values.items()} if norm else {}

    def rank(self, text, items, limit=3):
        query = self.vector(text)
        scored = []
        for item in items:
            candidate = self.vector(document(item))
            contributions = {term: value * candidate.get(term, 0)
                             for term, value in query.items() if term in candidate}
            score = sum(contributions.values())
            if score >= MIN_SIMILARITY:
                scored.append({**item, "similarity": round(score, 6),
                               "shared_terms": sorted(contributions,
                                                      key=lambda term: (-contributions[term], term))[:6]})
        return sorted(scored, key=lambda row: (-row["similarity"], row["id"]))[:limit]


def validate(payload):
    if not isinstance(payload, dict):
        raise ValueError("Send an object containing skills and optional evidence.")
    if set(payload) - {"skills", "evidence"}:
        raise ValueError("Only skills and evidence are accepted. Do not submit personal or sensitive data.")
    skills = payload.get("skills")
    evidence = payload.get("evidence", [])
    if not isinstance(skills, list) or not 1 <= len(skills) <= len(SKILLS):
        raise ValueError("Choose at least one catalogued skill (maximum 13).")
    if any(not isinstance(s, str) or s not in SKILLS for s in skills):
        raise ValueError("Use exact catalogued skill names; free-text biographies are not accepted.")
    if len(set(skills)) != len(skills):
        raise ValueError("Choose each skill only once.")
    allowed = {row["id"]: row["skill"] for row in EVIDENCE}
    if not isinstance(evidence, list) or len(evidence) > len(EVIDENCE):
        raise ValueError("Evidence must be a list of simulated catalogued evidence IDs.")
    if any(not isinstance(e, str) or e not in allowed for e in evidence):
        raise ValueError("Choose only simulated catalogued evidence IDs.")
    if len(set(evidence)) != len(evidence) or any(allowed[e] not in skills for e in evidence):
        raise ValueError("Select each evidence item once and only for your selected skills.")
    return sorted(skills), sorted(evidence)


class Matcher:
    def __init__(self):
        self.model = Tfidf(corpus())

    def match(self, payload):
        skills, evidence = validate(payload)
        query = " ".join(SKILLS[skill] for skill in skills)
        matches = self.model.rank(query, OPPORTUNITIES)
        for row in matches:
            row["shared_skills"] = sorted(set(skills) & set(row["skills"]))
            row["skills_to_explore"] = sorted(set(row["skills"]) - set(skills))
            row["evidence_gaps"] = [e["title"] for e in EVIDENCE
                                    if e["skill"] in row["skills"] and e["id"] not in evidence]
        return {
            "synthetic": True, "human_review_required": True,
            "passport": {"skills": skills, "evidence": evidence, "verification": "Unverified synthetic selections"},
            "opportunities": matches,
            "pathways": self.model.rank(query, PATHWAYS),
            "message": "Discovery only. Similarities are not probabilities, employability scores or hiring decisions.",
            "no_match": not matches,
        }
