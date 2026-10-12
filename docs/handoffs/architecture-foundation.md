# Integration handoff: architecture and shared foundation

## 1. Branch name

`main`

## 2. Commit hash

Foundation source commit: `1a83379cde1599466f27e43b37559c0a5914a97e`.
This handoff record is committed immediately afterward on the same `main`
branch. Use the final `main` tip reported by the project owner as the exact
branch point when including this handoff record in downstream branches.

## 3. Files created/modified

Created in the foundation source commit:

- Root: `.env.example`, `.gitignore`, `CONTRIBUTING.md`, `README.md`,
  `pyproject.toml`.
- API: `api/__init__.py`, `api/main.py`, `api/routes/__init__.py`,
  `api/services/__init__.py`, `api/database/__init__.py`.
- Core: `src/scopecheck/__init__.py`, `src/scopecheck/contracts.py`,
  `src/scopecheck/pipeline.py`, `src/scopecheck/ingestion/__init__.py`,
  `src/scopecheck/ingestion/parser.py`, `src/scopecheck/claims/__init__.py`,
  `src/scopecheck/claims/extractor.py`, `src/scopecheck/retrieval/__init__.py`,
  `src/scopecheck/retrieval/index.py`, `src/scopecheck/alignment/__init__.py`,
  `src/scopecheck/alignment/comparator.py`,
  `src/scopecheck/evaluation/__init__.py`.
- Data/web/scripts: `data/samples/README.md`, `data/benchmarks/README.md`,
  `data/outputs/.gitkeep`, `web/README.md`, `scripts/README.md`.
- Docs: `docs/API.md`, `docs/architecture/FOUNDATION.md`,
  `docs/architecture/REPOSITORY_WORKFLOW.md`,
  `docs/literature/README.md`, `docs/methodology/README.md`,
  `docs/experiments/README.md`, `docs/report/README.md`.
- Tests: `tests/test_contracts.py`, `tests/test_api.py`.

Added after that source commit: `docs/handoffs/architecture-foundation.md`.

## 4. Public functions and interfaces

Canonical types are defined in `src/scopecheck/contracts.py`:

- `SourceSpan`, `EvidenceChunk`, `ScientificScope`, `AtomicClaim`,
  `RetrievalHit`, `DimensionComparison`, `ComparisonResult`.
- `Relation`: `support`, `contradict`, `qualify`, `scope_mismatch`,
  `insufficient_evidence`, `unrelated`.
- `DimensionStatus`: `compatible`, `incompatible`, `partially_compatible`,
  `unknown`.
- `ScopeValue[T]` explicitly stores either a known value or an unknown value;
  absent scientific scope is never treated as agreement.
- API DTOs: `DocumentSummary`, `DocumentUploadResponse`, `AnalyzeRequest`,
  `ClaimAnalysis`, `AnalyzeResponse`, `AnalyzeCorpusRequest`,
  `AnalyzeCorpusResponse`, `HealthResponse`.

Implementation entrypoints (stubs intentionally raise `NotImplementedError`):

```python
parse_document(path: str | Path, document_id: str) -> list[EvidenceChunk]
extract_claims(text: str, document_id: str) -> list[AtomicClaim]
build_index(chunks: Sequence[EvidenceChunk]) -> EvidenceIndex

EvidenceIndex.search(
    query: str,
    k: int = 5,
    allowed_document_ids: Sequence[str] | None = None,
) -> list[RetrievalHit]

compare_claim_to_hit(claim: AtomicClaim, hit: RetrievalHit) -> ComparisonResult
```

`GET /api/health` is implemented. The document and analysis routes are specified
in `docs/API.md` but not implemented.

## 5. Dependencies added

Required: `fastapi>=0.110,<1`, `pydantic>=2.6,<3`, and `uvicorn>=0.27,<1`.
Development extra: `pytest>=8,<9`, `httpx>=0.27,<1`.
Optional extras: `docling` for ingestion, `scikit-learn` and
`sentence-transformers` for retrieval experiments, and `psycopg` plus
`sqlalchemy` for a future database adapter. No service credentials are needed.

## 6–7. Tests executed and results

Using bundled Python `3.12.14`:

- `python -m pip install -e '.[dev]'` — succeeded.
- `python -m pytest -q` — **8 passed**.
- Direct FastAPI `TestClient` request to `/api/health` — **HTTP 200** with
  `{"status":"ok","version":"0.1.0","mode":"local_development"}`.

The test run emitted one `StarletteDeprecationWarning` about its current
`httpx` test-client integration. No test failed. The system Python was 3.9.6,
below the declared minimum; validation used the bundled Python 3.12 runtime.

## 8. Example usage

From the repository root:

```sh
python -m pip install -e '.[dev]'
uvicorn api.main:app --reload
curl http://127.0.0.1:8000/api/health
```

The verified response is `{"status":"ok","version":"0.1.0","mode":"local_development"}`.
The documented parser, extraction, retrieval, and comparison signatures are
integration contracts, not working product functionality yet.

## 9. Known limitations

- Only the health route runs. Document upload/listing and both analysis routes
  remain API specifications.
- Parsing, extraction, retrieval, alignment, evaluation, persistence, and web
  behavior are not implemented.
- There is no authentication or multi-user data isolation; health's mode field
  is explicitly development-only.
- No benchmark data, scientific results, or model performance are included.
- Scope `conditions` and `numerical_values` currently use text lists; richer
  structured units/inequalities can be proposed through a coordinated contract
  revision if downstream owners need them.

## 10. Required integration steps

1. Start from the final `main` tip containing this handoff file.
2. Each workstream implements only its owned module and tests, preserving
   `scopecheck.contracts` as the canonical boundary.
3. Install editable with the module's optional extra only when needed.
4. Preserve IDs, exact evidence text, and source offsets. Represent unavailable
   scope as `ScopeValue(status="unknown")`.
5. Run `pytest` and document actual behavior before integrating.
6. Coordinate any contract or shared dependency change before merging.

## 11. Next recommended improvements

- Assign module owners and branch each workstream from the final baseline tip.
- Review whether source offsets should be character or byte offsets before a
  parser lands; this baseline defines them as zero-based half-open character
  offsets over canonical parser text.
- Add one first-party parser and local retrieval adapter behind the published
  interfaces, then implement the comparison module and API services.
- Add versioned persistence and user/workspace authorization only after the
  single-user local workflow is validated.
- Replace the current Starlette test-client dependency combination with a
  compatible pinned stack or supported async test client in a coordinated
  dependency update.
