import os
from neo4j import GraphDatabase

# Values verified in Checkpoints 2–4.
data = {
    "contract_id": "C-1002",
    "project_id": "P-102",
    "project_name": "Willow Creek",
    "seller_id": "S-001",
    "deadline_id": "C-1002:inspection",
    "deadline_type": "inspection deadline",
    "due_date": "2026-11-15",
    "original_due_date": None,
    "deadline_evidence": "The inspection deadline is November 15, 2026.",
    "source_id": "sample-contract-002",
    "source_text": """Contract C-1002 governs project P-102, named Willow Creek.
The seller signing this contract is ABC Land Holdings.
The inspection deadline is November 15, 2026.""",
    "contract_evidenc": "Contract C-1002 governs project P-102, named Willow Creek.",
    "project_evidence": "Contract C-1002 governs project P-102, named Willow Creek.",
    "seller_evidence": "The seller signing this contract is ABC Land Holdings.",
}

query = """
MATCH (s:Seller {id: $seller_id})
MERGE (c:Contract {id: $contract_id})
SET c.sourceId = $source_id,
    c.sourceText = $source_text,
    c.contractEvidence = $contract_evidence,
    c.projectEvidence = $project_evidence,
    c.sellerEvidence = $seller_evidence
MERGE (p:Project {id: $project_id})
SET p.name = $project_name
MERGE (d:Deadline {id: $deadline_id})
SET d.type = $deadline_type,
    d.dueDate = date($due_date),
    d.originalDueDate = date($original_due_date),
    d.sourceId = $source_id,
    d.evidence = $deadline_evidence
MERGE (c)-[:GOVERNS]->(p)
MERGE (c)-[:SIGNED_BY]->(s)
MERGE (c)-[:HAS_DEADLINE]->(d)
RETURN c.id AS contract, p.id AS project,
       s.id AS seller, d.id AS deadline
"""

def save_contract(contract):
    def write(tx):
        record = tx.run(query, **contract).single()
        if record is None:
            raise ValueError("Canonical seller missing; transaction rolled back")
        return record.data()

    with GraphDatabase.driver(
        "bolt://localhost:7687",
        auth=("neo4j", os.environ["NEO4J_PASSWORD"]),
    ) as driver:
        with driver.session(database="neo4j") as session:
            return session.execute_write(write)


if __name__ == "__main__":
    print(save_contract(data))


