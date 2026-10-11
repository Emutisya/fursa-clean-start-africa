"""Bounded fictional catalogue exploration, independent of retrieval scores."""
from copy import deepcopy

from .catalog import EVIDENCE, OPPORTUNITIES, PATHWAYS, SKILLS


def browse(kind="opportunity", skills=None):
    if kind not in {"opportunity", "pathway"}:
        raise ValueError("Kind must be opportunity or pathway.")
    if skills is None:
        skills = []
    if (not isinstance(skills, list)
            or any(not isinstance(skill, str) or skill not in SKILLS for skill in skills)
            or len(set(skills)) != len(skills)):
        raise ValueError("Filters must be unique exact catalogued skill names.")
    rows = OPPORTUNITIES if kind == "opportunity" else PATHWAYS
    return {
        "synthetic": True, "human_review_required": True,
        "kind": kind, "filters": sorted(skills),
        "items": deepcopy(sorted(
            (row for row in rows if set(skills) <= set(row["skills"])),
            key=lambda row: row["id"])),
        "message": "Fictional catalogue browsing, not live openings or eligibility advice.",
    }


def detail(identifier):
    if not isinstance(identifier, str):
        raise ValueError("Use an exact fictional resource ID from browse.")
    row = next((row for row in OPPORTUNITIES + PATHWAYS if row["id"] == identifier), None)
    if row is None:
        raise ValueError("Unknown resource ID; use browse to list fictional resources.")
    return {
        "synthetic": True, "human_review_required": True,
        "resource": deepcopy(row),
        "evidence_options": deepcopy([item for item in EVIDENCE if item["skill"] in row["skills"]]),
        "related_pathways": deepcopy([item for item in PATHWAYS if set(item["skills"]) & set(row["skills"])]),
        "message": "Evidence options are simulations, not requirements or proof of competence.",
    }


def compare(identifiers):
    if (not isinstance(identifiers, list) or not 2 <= len(identifiers) <= 4
            or any(not isinstance(identifier, str) for identifier in identifiers)
            or len(set(identifiers)) != len(identifiers)):
        raise ValueError("Compare two to four distinct fictional resource IDs.")
    rows = [detail(identifier)["resource"] for identifier in sorted(identifiers)]
    shared = set(rows[0]["skills"]).intersection(*(set(row["skills"]) for row in rows[1:]))
    return {
        "synthetic": True, "human_review_required": True,
        "resources": rows, "common_skills": sorted(shared),
        "skill_matrix": {
            skill: [row["id"] for row in rows if skill in row["skills"]]
            for skill in sorted({skill for row in rows for skill in row["skills"]})
        },
        "message": "Catalogue similarities only; no preferred option, eligibility or outcome prediction.",
    }
