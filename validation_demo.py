import re
from datetime import date

source = """Contract C-1002 governs project P-102, named Willow Creek.
The seller signing this contract is ABC Land Holdings.
The inspection deadline is November 15, 2026."""

data = {
    "contract_id": "C-1002",
    "project_id": "P-102",
    "project_name": "Willow Creek",
    "seller_name": "ABC Land Holdings",
    "deadline_type": "inspection deadline",
    "due_date": "2026-11-15",
    "deadline_evidence": "The inspection deadline is November 15, 2026."
}

def validate(data, source):
    required = {
        "contract_id", "project_id", "project_name", "seller_name",
        "deadline_type", "due_date", "deadline_evidence"
    }
    if set(data) != required:
        raise ValueError("Unexpected or missing fields")

    for key in required:
        if not isinstance(data[key], str) or not data[key].strip():
            raise ValueError(f"{key}: expected a nonempty string")

    for key, pattern in [
        ("contract_id", r"C-\d+"),
        ("project_id", r"P-\d+")
    ]:
        if not re.fullmatch(pattern, data[key]):
            raise ValueError(f"{key}: invalid ID")
        if data[key] not in source:
            raise ValueError(f"{key}: missing source evidence")

    for key in ("project_name", "seller_name"):
        if data[key] not in source:
            raise ValueError(f"{key}: missing source evidence")

    if data["deadline_type"] != "inspection deadline":
        raise ValueError("Unsupported deadline type for this sample")

    due = date.fromisoformat(data["due_date"])
    if due.isoformat() != data["due_date"]:
        raise ValueError("due_date: expected YYYY-MM-DD")

    evidence = data["deadline_evidence"]
    if evidence not in source:
        raise ValueError("Deadline evidence is not an exact source quote")

    # Sample-specific semantic check against the source date.
    if "November 15, 2026" not in evidence or due != date(2026, 11, 15):
        raise ValueError("Deadline date does not match source evidence")

validate(data, source)
print("PASS: valid extraction accepted")

invalid = {**data, "due_date": "2026-11-16"}
try:
    validate(invalid, source)
except ValueError as error:
    print(f"PASS: incorrect date rejected — {error}")
else:
    raise RuntimeError("FAIL: incorrect date accepted")
