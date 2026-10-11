"""Portable selections are synthetic simulations, never credentials."""
import hashlib
import json

from .catalog import fingerprint
from .model import validate
from .server import unique_fields

SCHEMA = "fursa.synthetic-passport.v1"
VERIFICATION = "Unverified synthetic selections"
MAX_PASSPORT_BYTES = 16384


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


def import_passport(raw):
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_PASSPORT_BYTES:
        raise ValueError("Passport must be a UTF-8 JSON file of 1 to 16384 bytes.")
    try:
        body = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_fields)
    except (ValueError, UnicodeError, RecursionError) as error:
        raise ValueError("Passport must contain valid UTF-8 JSON without duplicate fields.") from error
    fields = {"schema", "synthetic", "human_review_required", "verification",
              "catalog_sha256", "skills", "evidence", "content_sha256"}
    if not isinstance(body, dict) or set(body) != fields:
        raise ValueError("Use only the versioned synthetic passport schema; personal data is not accepted.")
    if (body["schema"] != SCHEMA or body["synthetic"] is not True
            or body["human_review_required"] is not True or body["verification"] != VERIFICATION):
        raise ValueError("Passport must be an unverified synthetic v1 simulation requiring human review.")
    skills, evidence = validate({"skills": body["skills"], "evidence": body["evidence"]})
    if skills != body["skills"] or evidence != body["evidence"]:
        raise ValueError("Passport selections must be canonically sorted.")
    if body["content_sha256"] != checksum({key: value for key, value in body.items() if key != "content_sha256"}):
        raise ValueError("Passport content checksum mismatch; re-export the intended synthetic selections.")
    if body["catalog_sha256"] != fingerprint():
        raise ValueError("Passport catalogue differs; review current catalog and re-export selections.")
    return {"skills": skills, "evidence": evidence}


def read_passport(path):
    with open(path, "rb") as stream:
        return import_passport(stream.read(MAX_PASSPORT_BYTES + 1))
