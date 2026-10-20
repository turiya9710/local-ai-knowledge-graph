import os
import unicodedata

from neo4j import GraphDatabase


def normalize(value):
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


extracted_name = "ABC Land Holdings"

with GraphDatabase.driver(
    "bolt://localhost:7687",
    auth=("neo4j", os.environ["NEO4J_PASSWORD"]),
) as driver:
    driver.verify_connectivity()

    with driver.session(database="neo4j") as session:
        sellers = session.run(
            "MATCH (s:Seller) RETURN s.id AS id, s.name AS name"
        ).data()

matches = [
    seller for seller in sellers
    if seller["name"]
    and normalize(seller["name"]) == normalize(extracted_name)
]

if not matches:
    raise ValueError("No matching seller; review before creating a new entity")

if len(matches) > 1:
    raise ValueError(f"Ambiguous seller matches: {matches}")

seller_id = matches[0]["id"]
if not seller_id:
    raise ValueError("Matched seller has no canonical ID")

print(f"Resolved: {extracted_name} -> {seller_id}")
