# SCOPE

**Scope-Aware Claim–Evidence Alignment for Scientific Literature Verification**

## Overview

SCOPE is a research prototype for helping researchers inspect whether selected
literature passages support, contradict, qualify, or insufficiently address
claims in a draft. It reports evidence alignment for human review; it does not
determine objective scientific truth.

## Problem statement and research objective

Semantic retrieval can find passages about the same topic without establishing
that they address the same conclusion under compatible populations, datasets,
methods, outcomes, metrics, or experimental conditions. For example, evidence
that a method improved accuracy on one dataset does not by itself establish a
draft claim that it improves accuracy across all datasets.

The research objective is to make those scope dimensions explicit in the
claim–evidence comparison and preserve traceability to source passages. The
central hypothesis is that explicit scope modeling may help distinguish direct
contradictions from claims that differ in experimental context. This hypothesis
has not yet been evaluated.

## Proposed methodology

The planned pipeline parses scientific documents into source-addressable
evidence chunks, extracts atomic claims and scope fields, retrieves candidate
passages, compares claims and passages across explicit dimensions, and
evaluates results against documented benchmarks. Missing scope is represented
as unknown rather than treated as agreement. Research design and literature
drafts are being developed on the dedicated literature workstream branch and
require review before integration.

## Architecture

The Python package under `src/scopecheck/` defines shared Pydantic contracts
and module interfaces. `api/` contains the minimal FastAPI application;
`web/` is reserved for the React client. Integration boundaries and planned
data flow are documented in
[`docs/architecture/FOUNDATION.md`](docs/architecture/FOUNDATION.md).

## Current implementation

The foundation currently provides:

- Installable Python package metadata and typed shared contracts.
- Contract validation tests.
- `GET /api/health` in FastAPI.
- Interface stubs for ingestion, claim extraction, retrieval, comparison, and
  pipeline orchestration.
- API specifications and research/architecture documentation scaffolding.

Document parsing, claim extraction, evidence retrieval, scope comparison,
corpus evaluation, persistence, and frontend behavior are not implemented.
Research and literature documents are drafts and require source verification.

## Installation and running

Requires Python 3.11 or newer.

```sh
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
pytest
uvicorn api.main:app --reload
```

The health endpoint is `http://127.0.0.1:8000/api/health`; FastAPI docs are at
`http://127.0.0.1:8000/docs`. Optional dependency groups are available for
ingestion, retrieval experiments, and database adapters. The foundation does
not require paid APIs, cloud services, PostgreSQL, Pinecone, or external
credentials.

## Evaluation status

No scientific benchmark or model evaluation has been run. The current tests
validate data contracts and the health route; they are software checks, not
evidence for the research hypothesis. Benchmark data must include provenance,
license, annotation schema, and version before results are reported.

## Limitations and future work

The product pipeline is not implemented, the API has no authentication or
multi-user isolation, and no persistence layer is configured. Next workstreams
will implement ingestion, claim extraction, retrieval, alignment, evaluation,
backend, frontend, and verified literature research behind the shared
contracts.

## References

Bibliographic details and source claims must be checked against primary sources
before academic submission. No literature citations are asserted in this
README.
