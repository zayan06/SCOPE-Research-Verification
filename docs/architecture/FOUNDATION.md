# SCOPE repository foundation

## Data flow

```text
PDF / DOCX ──parse_document──▶ EvidenceChunk[]
Draft text ──extract_claims──▶ AtomicClaim[]
EvidenceChunk[] ──build_index──▶ EvidenceIndex
AtomicClaim + RetrievalHit ──compare_claim_to_hit──▶ ComparisonResult
                         └── API / UI / evaluation consumers ──▶ researcher review
```

`ComparisonResult` records alignment between one claim and one passage. It is
not a finding about objective scientific truth. Retain exact source spans and
evidence quotes so researchers can inspect context.

## Module responsibilities

- `src/scopecheck/contracts.py`: canonical Pydantic v2 models, enums, validation,
  API DTOs, and explicit unknown scope values.
- `ingestion/`: parsing, chunk boundaries, and source provenance.
- `claims/`: atomic claim segmentation and source spans.
- `retrieval/`: index protocol, indexing, and ranked search adapters.
- `alignment/`: dimension-by-dimension comparison and relation assignment.
- `evaluation/`: benchmark loading, reproducible measures, and result writing.
- `pipeline.py`: orchestration across module interfaces; currently a stub.
- `api/`: HTTP boundary, request validation, services, and persistence adapters.
- `web/`: independent React + TypeScript client; implementation is outside this
  foundation workstream.
- `data/`: redistributable samples, benchmark manifests, and generated outputs.
- `docs/`: architecture, API, methodology, literature, experiment, and report
  records. Proposed work must be labeled as proposed until implemented/tested.

## Shared contracts and unknowns

All cross-module enums and models live in `scopecheck.contracts`. Scope fields
use `ScopeValue[T]`: `known` requires a value; `unknown` carries no value.
Missing scope is not a compatibility signal. Each comparison dimension uses
`compatible`, `incompatible`, `partially_compatible`, or `unknown`, with an
explanation.

`SourceSpan` offsets are zero-based, half-open character offsets in the parser's
canonical text. `page_number` is one-based when known. Unknown location fields
are `null`; parsers must not invent locations. `exact_text` preserves source
wording.

## Persistence plan

The baseline does not initialize a database. `api/database/` is an adapter
boundary. A later persistence proposal may add PostgreSQL and SQLAlchemy
migrations for workspaces, document metadata, chunk provenance, claims,
comparison runs, annotations, and evaluation records. Parsing, retrieval, and
contracts must remain usable without PostgreSQL. Local SQLite or in-memory
adapters must be explicit and must not imply production user isolation.

## Local-first and replaceable services

Required dependencies are FastAPI, Pydantic, and Uvicorn. Parsers, embeddings,
external LLMs, vector databases, and PostgreSQL drivers are optional extras or
adapters. Interfaces accept local Python values and return canonical contracts.
External services can replace adapters behind these interfaces. No paid API,
cloud service, or credentials are needed for baseline installation.

## Parallel ownership and integration

Each workstream owns its module and tests. Branches start from the foundation
commit. Do not change shared contracts independently. Propose contract changes
as reviewable updates with migration impact before integrating. Install the
package editable, implement exact signatures below, and run all contract tests.

```python
parse_document(path: str | Path, document_id: str) -> list[EvidenceChunk]
extract_claims(text: str, document_id: str) -> list[AtomicClaim]
build_index(chunks: Sequence[EvidenceChunk]) -> EvidenceIndex

class EvidenceIndex(Protocol):
    def search(
        self, query: str, k: int = 5,
        allowed_document_ids: Sequence[str] | None = None,
    ) -> list[RetrievalHit]: ...

compare_claim_to_hit(claim: AtomicClaim, hit: RetrievalHit) -> ComparisonResult
```

Interface stubs raise `NotImplementedError`; they do not imply product features
are implemented.
