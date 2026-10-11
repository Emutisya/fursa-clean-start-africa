"""Bounded UTF-8 JSON reading shared by local document consumers."""
import json


def unique_fields(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON fields are not accepted.")
        result[key] = value
    return result


def read_json(path, limit):
    with open(path, "rb") as stream:
        raw = stream.read(limit + 1)
    if not 0 < len(raw) <= limit:
        raise ValueError(f"JSON file must contain 1 to {limit} bytes.")
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=unique_fields)
    except (ValueError, UnicodeError, RecursionError) as error:
        raise ValueError("Use bounded UTF-8 JSON without duplicate fields.") from error
