import json
import os
import re
import sys
import unicodedata
import urllib.request
from datetime import datetime
from pathlib import Path
from neo4j import GraphDatabase
from upsert_contract import save_contract

#source = """Contract C-1002 governs project P-102, named Willow Creek.
#The seller signing this contract is ABC Land Holdings.
#The inspection deadline is November 15, 2026."""
source_path = Path(sys.argv[1])
source = source_path.read_text(encoding="utf-8").strip()

fields = [
	"contract_id", "project_id", "project_name", "seller_name",
	"deadline_type", "due_date", "deadline_evidence",
	"contract_evidence", "project_evidence", "seller_evidence"
]

schema = {
    "type": "object",
    "properties": {key: {"type": "string"} for key in fields},
    "required": fields,
    "additionalProperties": False
}

payload = {
    "model": "qwen3:8b",
    "stream": False,
    "think": False,
    "format": schema,
    "options": {"temperature": 0},
    "prompt": (
	"Extract contract facts as JSON matching this schema:\n"
	+ json.dumps(schema)
	+ "\nUse YYYY-MM-DD for due_date. "
	"For every evidence field, copy an exact complete source sentence. "
	"contract_evidence must identify the contract; "
	"project_evidence must link that contract to its project; "
	"seller_evidence must identify the signing seller. "
	"deadline_evidence must state the inspection deadline. "
	"Use deadline_type='inspection deadline'. "
	"Preserve source spelling and casing for names. "
	"Use empty strings for missing facts; do not invent values.\n"
	"For project_evidence, copy the COMPLETE sentence containing "
	"contract_id, project_id, and project_name, including all text after commas. "
	"Every evidence quote must include the original sentence-ending punctuation. "
	"Never shorten evidence into fragments.\n"
	"SOURCE:\n" + source
    )
}

request = urllib.request.Request(
    "http://localhost:11434/api/generate",
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json"}
)

with urllib.request.urlopen(request, timeout=180) as response:
    result = json.load(response)

if not result.get("done"):
    raise ValueError("Extraction did not complete")

data = json.loads(result["response"])
print("1. Extracted:", json.dumps(data, indent=2))

# This validation deliberately supports only this sample's wording.
if not isinstance(data, dict) or set(data) != set(fields):
    raise ValueError("Unexpected or missing fields")

for key in fields:
    if not isinstance(data[key], str) or not data[key].strip():
        raise ValueError(f"{key}: expected a nonempty string")

for key, pattern in [
    ("contract_id", r"C-\d+"),
    ("project_id", r"P-\d+")
]:
    if not re.fullmatch(pattern, data[key]):
        raise ValueError(f"{key}: invalid ID")

def contains_value(quote, value):
    return re.search(
        rf"(?<!\w){re.escape(value)}(?!\w)", quote
    ) is not None


evidence_checks = {
    "contract_evidence": ["contract_id"],
    "project_evidence": ["contract_id", "project_id", "project_name"],
    "seller_evidence": ["seller_name"]
}

for evidence_field, value_fields in evidence_checks.items():
    quote = data[evidence_field]
    if quote not in source:
        raise ValueError(f"{evidence_field}: quote not found in source")
    for value_field in value_fields:
        if not contains_value(quote, data[value_field]):
            raise ValueError(f"{value_field}: absent from evidence quote")

evidence = data["deadline_evidence"]
if evidence not in source:
    raise ValueError("Deadline evidence is not an exact source quote")

if data["deadline_type"] != "inspection deadline":
    raise ValueError("Unsupported deadline type")

if not re.search(r"\binspection\b", evidence, re.IGNORECASE):
    raise ValueError("Deadline quote does not mention inspection")

# Accept one explicit date, written as ISO or an English month date.
date_tokens = re.findall(
    r"\b(?:\d{4}-\d{2}-\d{2}|"
    r"(?:January|February|March|April|May|June|July|August|"
    r"September|October|November|December) \d{1,2}, \d{4})\b",
    evidence
)

extension = re.fullmatch(
    r"Inspection was originally due on (\d{4}-\d{2}-\d{2}) "
    r"but was extended to (\d{4}-\d{2}-\d{2})\.",
    evidence
)

original_due_date = None

if extension:
    original = datetime.strptime(extension[1], "%Y-%m-%d").date()
    expected_date = datetime.strptime(extension[2], "%Y-%m-%d").date()

    if expected_date <= original:
        raise ValueError("Extended deadline must follow the original date")

    original_due_date = original.isoformat()
elif len(date_tokens) == 1:
    token = date_tokens[0]
    date_format = (
        "%Y-%m-%d"
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", token)
        else "%B %d, %Y"
    )
    expected_date = datetime.strptime(token, date_format).date()
else:
    raise ValueError("Deadline wording requires review")

if data["due_date"] != expected_date.isoformat():
    raise ValueError("Deadline date contradicts source evidence")

print("2. Validation passed")

def normalize(value):
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


with GraphDatabase.driver(
    "bolt://localhost:7687",
    auth=("neo4j", os.environ["NEO4J_PASSWORD"])
) as driver:
    with driver.session(database="neo4j") as session:
        sellers = session.run(
            "MATCH (s:Seller) RETURN s.id AS id, s.name AS name"
        ).data()

matches = [
    seller for seller in sellers
    if seller["name"]
    and normalize(seller["name"]) == normalize(data["seller_name"])
]
if len(matches) != 1 or not matches[0]["id"]:
    raise ValueError("Seller requires review: missing or ambiguous match")

print("3. Seller resolved:", matches[0]["id"])

record = {
    **data,
    "seller_id": matches[0]["id"],
    "deadline_id": f"{data['contract_id']}:inspection",
    #"source_id": "sample-contract-002",
    "source_id": source_path.name,
    "source_text": source,
    "original_due_date": original_due_date
}
# The existing Cypher query does not use this extraction-only field.
record.pop("seller_name")

print("4. Saved:", save_contract(record))
