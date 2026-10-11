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


def skill_map():
    return {
        "synthetic": True, "human_review_required": True,
        "skills": [
            {
                "skill": skill, "terms": SKILLS[skill].split(),
                "opportunities": sorted(row["id"] for row in OPPORTUNITIES if skill in row["skills"]),
                "pathways": sorted(row["id"] for row in PATHWAYS if skill in row["skills"]),
                "evidence": sorted(row["id"] for row in EVIDENCE if row["skill"] == skill),
                "co_occurring_skills": sorted({
                    other for row in OPPORTUNITIES if skill in row["skills"]
                    for other in row["skills"] if other != skill
                }),
            } for skill in sorted(SKILLS)
        ],
        "message": "Coverage and co-occurrence describe this fictional catalogue, not demand or ability.",
    }


def related(identifier):
    source = detail(identifier)["resource"]
    source_skills = set(source["skills"])
    rows = []
    for candidate in OPPORTUNITIES + PATHWAYS:
        overlap = source_skills & set(candidate["skills"])
        if candidate["id"] != identifier and overlap:
            rows.append({
                "resource": deepcopy(candidate), "shared_skills": sorted(overlap),
                "additional_skills": sorted(set(candidate["skills"]) - source_skills),
            })
    return {
        "synthetic": True, "human_review_required": True, "source": source,
        "related": sorted(rows, key=lambda row: row["resource"]["id"]),
        "message": "Shared catalogue skills only; these are not recommendations or equivalence claims.",
    }


def review_plan(identifier, payload):
    from .model import validate

    skills, evidence = validate(payload)
    resource = detail(identifier)["resource"]
    rows = [
        {**deepcopy(row), "selected_skill": row["skill"] in skills,
         "simulated_sample_selected": row["id"] in evidence,
         "status": "Unverified simulation; human review required"}
        for row in EVIDENCE if row["skill"] in resource["skills"]
    ]
    return {
        "synthetic": True, "human_review_required": True,
        "resource": resource, "evidence_review": rows,
        "skills_to_explore": sorted(set(resource["skills"]) - set(skills)),
        "review_questions": [
            "What published criteria would a human assessor use?",
            "What consent and minimum disclosure are appropriate for a work sample?",
            "What recognition, accessibility, fees and appeal options can a provider confirm?",
        ],
        "message": "Optional discussion plan, not requirements, proof or an assessment decision.",
    }


def preview_additions(payload):
    from .model import Matcher, validate

    skills, evidence = validate(payload)
    matcher = Matcher()
    baseline = matcher.match({"skills": skills, "evidence": evidence}, 12)
    baseline_ids = {row["id"] for row in baseline["opportunities"]}
    return {
        "synthetic": True, "human_review_required": True,
        "baseline_opportunities": sorted(baseline_ids),
        "scenarios": [
            {
                "added_skill": skill,
                "ranked_opportunities": [row["id"] for row in result["opportunities"]],
                "newly_visible": sorted({row["id"] for row in result["opportunities"]} - baseline_ids),
                "no_longer_visible": sorted(baseline_ids - {row["id"] for row in result["opportunities"]}),
            }
            for skill in sorted(set(SKILLS) - set(skills))
            for result in [matcher.match({"skills": [*skills, skill], "evidence": evidence}, 12)]
        ],
        "message": "Hypothetical catalogue selections only, not learning advice, skill acquisition or outcomes.",
    }
