# Backend workstream handoff

## Branch and commit

- Workstream: Agent 6, backend
- Branch: `feat/backend`
- Latest implementation commit at handoff: `a0b0b32491186bd9f2535ffc0751e989bab7577e`
- Commit message: `feat(backend): add persistent local API services`

## Files created or modified

- `api/main.py`
- `api/database/models.py`, `api/database/session.py`
- `api/routes/projects.py`, `api/routes/documents.py`, `api/routes/analysis.py`
- `api/schemas.py`
- `api/services/document_storage.py`, `api/services/analysis.py`
- `tests/test_api.py`
- `docs/API.md`, `docs/architecture/backend.md`
- `pyproject.toml` (added `python-multipart` to the existing `database` extra)

## Implemented API

- `GET /api/health`
- `POST /api/projects`, `GET /api/projects`, `GET /api/projects/{project_id}`, `PATCH /api/projects/{project_id}`
- `POST /api/documents`, `GET /api/documents`, `GET /api/documents/{document_id}`, `GET /api/documents/{document_id}/status`
- `POST /api/analyze`, `POST /api/analyze-corpus`
- `GET /api/analysis-runs/{run_id}`, `GET /api/analysis-runs/{run_id}/results`
- `GET /api/projects/{project_id}/analysis-runs`
- OpenAPI: `/api/openapi.json`; Swagger UI: `/api/docs`; ReDoc: `/api/redoc`

The foundation contract DTOs remain unchanged. Project, document-version, and
run-history response schemas are backend additions. See `docs/API.md` for
requests, examples, status codes, and error behavior.

## Persistence schema

SQLAlchemy models implement `projects`, `documents`, `document_versions`,
`evidence_chunks`, `atomic_claims`, `analysis_runs`, and `comparison_results`.
Relationships use foreign keys and deletion rules; query paths have indexes.
JSON columns preserve structured scope, source spans, metadata, corpus
selection, and complete canonical comparisons. SQLite is the default at
`data/scope.db`; PostgreSQL URLs are supported by SQLAlchemy's portable schema
but were not exercised against a live PostgreSQL server.

Uploads are versioned, checksummed, and stored under UUID-generated filenames
in `data/uploads/` by default. PDF and DOCX are accepted with a configurable
size limit. A stored document is reported as `uploaded`; its processing state
stays `pending` until the ingestion module is connected.

## Tests and verification

- Installed `.[dev,database]` into the provided Python 3.12 virtual environment.
- `.venv/bin/python -m pytest -q` — **19 passed**, one upstream Starlette/httpx deprecation warning.
- `.venv/bin/python -m compileall -q api` — passed.
- `git diff --check` — passed.
- Health route returned HTTP 200 with the foundation response.
- `/api/openapi.json` returned HTTP 200 and included `/api/analyze`.
- Tests use temporary SQLite databases and a mock pipeline only for adapter behavior.

## Dependencies

The existing optional `database` extra already contains SQLAlchemy and psycopg.
This work added `python-multipart` to that extra for FastAPI form uploads. Setup:

```sh
python -m pip install -e '.[dev,database]'
uvicorn api.main:app --reload
```

## Pipeline adapter contract and Agent 9 steps

`api.services.analysis.PipelineAdapter` is the boundary from API orchestration
to the integrated research pipeline:

```python
class ScopePipelineAdapter:
    algorithm_version: str

    def analyze(self, request: AnalyzeRequest,
                document_paths: list[tuple[str, str]]) -> AnalyzeResponse: ...
```

The pairs are ordered as `request.selected_document_ids`. `AnalyzeResponse`,
`ClaimAnalysis`, evidence, and comparisons must use the shared contracts. Keep
exact source text, source IDs, and provenance in returned values. During app
assembly, set `api.main.app.state.pipeline_adapter` to the integrated adapter.
The current default intentionally raises `PipelineUnavailable`; the API
persists a failed run and returns `503 pipeline_unavailable` with its run ID.

For corpus evaluation, implement an optional adapter method
`analyze_corpus(benchmark_id, document_ids) -> AnalyzeCorpusResponse`. Until
then `/api/analyze-corpus` persists and reports the unavailable condition. The
backend does not duplicate claim extraction, retrieval, alignment, or
evaluation algorithms.

## Limitations and integration notes

- Table creation uses SQLAlchemy `create_all`; Alembic migration files are not included.
- Analysis runs synchronously. There is no durable queue or worker process.
- Parsing is not run by upload. Uploaded files remain pending ingestion.
- No authentication, authorization, or multi-tenant isolation exists. This is a single-user local prototype.
- PostgreSQL compatibility is designed but not verified against a server.
- Configure `SCOPE_DATABASE_URL`, `SCOPE_STORAGE_DIR`, `SCOPE_MAX_UPLOAD_BYTES`, `SCOPE_CORS_ORIGINS`, and `SCOPE_MODE` through the environment.

The integration workstream can consume this branch after merging it into its
integration checkout; this branch was not merged into `main`.
