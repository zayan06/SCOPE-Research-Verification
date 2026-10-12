# SCOPE — Scope-Aware Claim–Evidence Alignment

SCOPE is a local-first research workspace foundation for examining whether
passages in selected academic literature support, contradict, qualify, or
insufficiently address claims in a research draft. It is decision support and
does not determine objective scientific truth.

## Repository status

This baseline establishes shared contracts, package metadata, one health
endpoint, module interfaces, tests, and architecture/API documentation.
Document parsing, claim extraction, retrieval, scope comparison, corpus
analysis, persistence, and frontend logic are not implemented here. Interface
functions explicitly raise `NotImplementedError` until their workstreams land.

## Local setup

Requires Python 3.11 or newer.

```sh
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
pytest
uvicorn api.main:app --reload
```

The only live route in this foundation is
`GET http://127.0.0.1:8000/api/health`. The OpenAPI UI is at `/docs`. Other API
routes are specified in `docs/API.md` but are not yet implemented.

Optional integrations are isolated as extras: `.[ingestion]`, `.[retrieval]`,
and `.[database]`. No paid API, cloud service, PostgreSQL server, Firebase,
Pinecone, or external credentials are needed for the foundation.

## Core integration interfaces

Canonical typed models and enums are in `src/scopecheck/contracts.py`.
Workstreams implement these signatures without changing their contracts:

```python
parse_document(path: str | Path, document_id: str) -> list[EvidenceChunk]
extract_claims(text: str, document_id: str) -> list[AtomicClaim]
build_index(chunks: Sequence[EvidenceChunk]) -> EvidenceIndex
compare_claim_to_hit(claim: AtomicClaim, hit: RetrievalHit) -> ComparisonResult
```

`EvidenceIndex.search(query, k=5, allowed_document_ids=None)` returns
`list[RetrievalHit]`. See `docs/architecture/FOUNDATION.md` and
`CONTRIBUTING.md` for ownership and integration instructions.

## Research integrity and AI assistance

The repository structure, contracts, documentation scaffolding, and contract
tests were generated with OpenAI Codex from the user-provided project brief. No
sources, experimental results, evaluation metrics, or student contributions are
fabricated. Maintain this record as additional tools are used.
