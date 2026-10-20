import os
from datetime import date, timedelta

from neo4j import GraphDatabase

constraints = [
    "CREATE CONSTRAINT contract_id IF NOT EXISTS "
    "FOR (n:Contract) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT project_id IF NOT EXISTS "
    "FOR (n:Project) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT seller_id IF NOT EXISTS "
    "FOR (n:Seller) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT deadline_id IF NOT EXISTS "
    "FOR (n:Deadline) REQUIRE n.id IS UNIQUE",
]

query = """
MERGE (c:Contract {id: $contract_id})
MERGE (p:Project {id: $project_id})
MERGE (s:Seller {id: $seller_id})
SET s.name = $seller_name
MERGE (d:Deadline {id: $deadline_id})
SET d.dueDate = date($due_date)
MERGE (c)-[:GOVERNS]->(p)
MERGE (c)-[:SIGNED_BY]->(s)
MERGE (c)-[:HAS_DEADLINE]->(d)
"""

with GraphDatabase.driver(
    "bolt://localhost:7687",
    auth=("neo4j", os.environ["NEO4J_PASSWORD"]),
) as driver:
    driver.verify_connectivity()

    with driver.session(database="neo4j") as session:
        for statement in constraints:
            session.run(statement).consume()

        session.run(
            query,
            contract_id="C-1001",
            project_id="P-101",
            seller_id="S-001",
            seller_name="ABC Land Holdings",
            deadline_id="D-101",
            due_date=(date.today() + timedelta(days=15)).isoformat(),
        ).consume()

print("Graph created successfully.")
