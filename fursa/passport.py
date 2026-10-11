"""Portable selections are synthetic simulations, never credentials."""
import hashlib
import json

from .catalog import fingerprint
from .model import validate

SCHEMA = "fursa.synthetic-passport.v1"
VERIFICATION = "Unverified synthetic selections"


def checksum(body):
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=True,
                                    separators=(",", ":")).encode("utf-8")).hexdigest()


def export_passport(payload):
    skills, evidence = validate(payload)
    body = {
        "schema": SCHEMA, "synthetic": True, "human_review_required": True,
        "verification": VERIFICATION, "catalog_sha256": fingerprint(),
        "skills": skills, "evidence": evidence,
    }
    return {**body, "content_sha256": checksum(body)}
