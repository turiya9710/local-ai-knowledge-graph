
import json
import urllib.request

text = """Contract C-1002 governs project P-102, named Willow Creek.
The seller signing this contract is ABC Land Holdings.
The inspection deadline is November 15, 2026."""

schema = {
    "type": "object",
    "properties": {
        key: {"type": "string"}
        for key in [
            "contract_id", "project_id", "project_name",
            "seller_name", "deadline_type", "due_date", "deadline_evidence"
        ]
    },
    "required": [
        "contract_id", "project_id", "project_name",
        "seller_name", "deadline_type", "due_date", "deadline_evidence"
    ],
    "additionalProperties": False
}

payload = {
    "model": "qwen3:8b",
    "stream": False,
    "think": False,
    "format": schema,
    "options": {"temperature": 0},
    "prompt": (
        "Extract contract facts from the source below. "
        "Return JSON matching this schema: " + json.dumps(schema) + "\n"
        "Use YYYY-MM-DD for due_date. "
        "Copy deadline_evidence verbatim from the source. "
        "Use an empty string for missing facts; do not invent values.\n"
        "SOURCE:\n" + text
    )
}

request = urllib.request.Request(
    "http://localhost:11434/api/generate",
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json"},
)

with urllib.request.urlopen(request, timeout=180) as response:
    result = json.load(response)

extracted = json.loads(result["response"])
print(json.dumps(extracted, indent=2))
