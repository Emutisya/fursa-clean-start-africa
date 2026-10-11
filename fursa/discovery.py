"""Bounded fictional catalogue exploration, independent of retrieval scores."""
from copy import deepcopy

from .catalog import OPPORTUNITIES, PATHWAYS, SKILLS


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
