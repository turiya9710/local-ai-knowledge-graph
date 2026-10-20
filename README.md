# Local AI Knowledge Graph

A local contract-intelligence lab using Ollama/Qwen, Python, and Neo4j.

The pipeline extracts structured facts from synthetic contracts, validates
them against source evidence, resolves canonical sellers, and upserts
entities and relationships into Neo4j.

## Stack

- Windows 11 with WSL2 Ubuntu
- Docker Desktop with WSL integration
- Neo4j 5.26
- Python virtual environment
- Ollama with qwen3:8b

## Graph schema

- Contract → GOVERNS → Project
- Contract → SIGNED_BY → Seller
- Contract → HAS_DEADLINE → Deadline

Entities use unique IDs. Contract and deadline properties retain source
references and evidence quotes.

## Implemented

- Structured extraction through Ollama
- Required-field, ID, date, and source-quote validation
- Seller resolution using normalized names
- Blocking of missing or ambiguous seller matches
- Manual registration and retry for new sellers
- Transactional, repeatable Neo4j upserts
- Cross-contract traversal through shared sellers
- Explicit deadline-extension handling with original and effective dates

## Setup

Run commands in Bash from the repository root.

### 1. Start Neo4j

Choose a local password:

```bash
read -rsp "Neo4j password: " NEO4J_PASSWORD
echo
export NEO4J_PASSWORD

docker run -d \
  --name neo4j-kg \
  --restart unless-stopped \
  -p 127.0.0.1:7474:7474 \
  -p 127.0.0.1:7687:7687 \
  -e "NEO4J_AUTH=neo4j/$NEO4J_PASSWORD" \
  -v neo4j-kg-data:/data \
  neo4j:5.26
```

For an existing container:

```bash
docker start neo4j-kg
```

Use the password already configured for its database.
NEO4J_AUTH does not reset an existing database's password.

Neo4j Browser: http://localhost:7474  
Bolt connection: bolt://localhost:7687

### 2. Prepare Python

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install 'neo4j>=5.26,<6'
```

### 3. Prepare Ollama

On the machine running Ollama:

```bash
ollama pull qwen3:8b
```

From WSL, verify that the API is accessible:

```bash
curl --fail http://localhost:11434/api/tags
```

The current pipeline expects Ollama at localhost:11434.

### 4. Initialize the baseline

```bash
python seed_graph.py
```

This creates uniqueness constraints and the baseline graph, including
canonical seller S-001: ABC Land Holdings.

For the synthetic XYZ Land Partners example, register its canonical seller
in Neo4j Browser before ingestion:

```cypher
MERGE (s:Seller {id: 'S-002'})
ON CREATE SET s.name = 'XYZ Land Partners'
RETURN s;
```

### 5. Ingest a synthetic contract

```bash
python pipeline.py input/contract-006.txt
```

Expected stages:

1. Extract structured facts.
2. Validate source support.
3. Resolve the seller.
4. Save the graph in a transaction.

Unknown sellers stop ingestion before database writes.

## Example query

```cypher
MATCH (c:Contract)-[:SIGNED_BY]->(s:Seller),
      (c)-[:GOVERNS]->(p:Project),
      (c)-[:HAS_DEADLINE]->(d:Deadline)
RETURN c.id AS contract,
       s.name AS seller,
       p.name AS project,
       d.originalDueDate AS originalDate,
       d.dueDate AS effectiveDate,
       d.evidence AS evidence
ORDER BY contract;
```

## Validation performed

Manual lab checks demonstrated:

- Repeated upserts without duplicate relationships
- Case-insensitive resolution to an existing seller
- Unknown-seller rejection without partial writes
- Successful retry after canonical seller registration
- Rejection of a date that contradicted source evidence
- Extraction from varied sentence wording
- Preservation of original and extended deadline dates
- Continued support for single-date contracts

These are manual checks, not an automated regression suite.

## Limitations

- Educational prototype using synthetic text files
- One project, seller, and inspection deadline per input
- Validation supports selected wording and date formats
- Exact quotes and matching values do not prove semantic correctness
- Seller resolution does not handle legal aliases or fuzzy matching
- Source properties reflect the latest upsert, not immutable version history
- Original baseline contract C-1001 lacks source provenance
- No PDF/OCR ingestion, access controls, or GraphRAG answering yet

## Next milestone

Local GraphRAG: retrieve graph facts and supporting evidence, then generate
answers with source citations through Qwen.
