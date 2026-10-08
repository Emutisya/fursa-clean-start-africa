"""Small, deliberately fictional catalogue. No scraped or personal data."""

SKILLS = {
    "carpentry": "carpentry timber joinery furniture assembly measuring",
    "welding": "welding metal fabrication joints workshop",
    "electrical": "electrical circuits wiring maintenance safety",
    "solar": "solar photovoltaic panels installation energy",
    "sewing": "sewing tailoring garments stitching fabric",
    "food preparation": "food preparation cooking kitchen hygiene",
    "bookkeeping": "bookkeeping accounts invoices reconciliation ledger",
    "spreadsheets": "spreadsheets tables formulas inventory records",
    "customer service": "customer service communication enquiries support",
    "logistics": "logistics dispatch deliveries inventory warehouse",
    "horticulture": "horticulture seedlings cultivation irrigation nursery",
    "plumbing": "plumbing pipes leaks fittings water repairs",
    "astronomy": "astronomy constellations telescope galaxies",
}


def opportunity(id, title, skills, description, setting):
    return {
        "id": id, "kind": "opportunity", "title": title, "skills": skills,
        "description": description, "setting": setting,
        "synthetic": True, "human_review_required": True,
    }


OPPORTUNITIES = [
    opportunity("o-timber", "Timber workshop practice placement",
                ["carpentry"], "Build furniture using timber joinery and measuring.", "Fictional Nairobi workshop"),
    opportunity("o-metal", "Metal fabrication practice placement",
                ["welding"], "Practice welding metal joints in a supervised workshop.", "Fictional Accra workshop"),
    opportunity("o-solar", "Solar maintenance learning placement",
                ["solar", "electrical"], "Assist photovoltaic installation and electrical wiring safety.", "Fictional Kigali energy hub"),
    opportunity("o-textile", "Textile production practice placement",
                ["sewing"], "Prepare garments with fabric cutting and stitching.", "Fictional Kampala textile hub"),
    opportunity("o-kitchen", "Community kitchen practice placement",
                ["food preparation"], "Practice cooking and kitchen hygiene.", "Fictional Lusaka kitchen"),
    opportunity("o-accounts", "Small enterprise accounts practice",
                ["bookkeeping", "spreadsheets"], "Reconcile invoices and ledger records with tables and formulas.", "Fictional Dakar enterprise hub"),
    opportunity("o-dispatch", "Dispatch and customer support practice",
                ["logistics", "customer service", "spreadsheets"], "Maintain warehouse inventory records and answer delivery enquiries.", "Fictional Mombasa logistics hub"),
    opportunity("o-nursery", "Seedling nursery practice placement",
                ["horticulture"], "Support seedlings, irrigation and cultivation.", "Fictional Addis Ababa nursery"),
    opportunity("o-water", "Water repair learning placement",
                ["plumbing"], "Practice pipe fittings and leak repairs under supervision.", "Fictional Dar es Salaam repair hub"),
]

EVIDENCE = [
    {"id": "e-" + skill.replace(" ", "-"), "skill": skill,
     "title": "Synthetic " + skill + " work sample",
     "description": "A simulated demonstration, not verified or certified."}
    for skill in SKILLS if skill != "astronomy"
]
PATHWAYS = [
    {"id": "p-" + skill.replace(" ", "-"), "kind": "pathway",
     "title": skill.title() + " evidence review pathway", "skills": [skill],
     "description": SKILLS[skill] + " demonstration portfolio assessment",
     "steps": ["Prepare a consent-based work sample.",
               "Request a human assessor's review against published criteria.",
               "Ask a locally recognized provider whether prior learning can be assessed.",
               "Confirm recognition, fees, accessibility and appeal options directly."],
     "synthetic": True, "human_review_required": True,
     "status": "Simulated only. No provider agreement or credential issued."}
    for skill in SKILLS if skill != "astronomy"
]


def document(item):
    return item["description"] + " " + " ".join(SKILLS[s] for s in item["skills"])


def corpus():
    return [document(item) for item in OPPORTUNITIES + PATHWAYS] + list(SKILLS.values())
