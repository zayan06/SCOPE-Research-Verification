# Backend architecture

## Data model

`api/database/models.py` defines seven SQLAlchemy tables: projects own
documents; documents own numbered document versions; versions own extracted
evidence chunks and atomic claims; projects own analysis runs; runs own
structured comparison results. Foreign keys use cascade deletion for document
versions and run results, and indexes cover project chronology, version order,
and run/result lookup. UUID strings are used for generated record IDs; canonical
pipeline IDs are retained for claims and evidence chunks. JSON columns preserve
scope, source spans, chunk metadata, corpus selection, and the full comparison
contract. The schema uses portable SQLAlchemy types for SQLite and PostgreSQL.

`api/database/session.py` reads `SCOPE_DATABASE_URL`, defaults to local SQLite,
enables SQLite foreign keys, and provides request-scoped sessions. Tables are
created at application startup for this prototype. Alembic migrations are not
included; adopt migrations before evolving deployed data.

## API structure

`api/main.py` configures FastAPI, CORS, health, OpenAPI, and route registration.
Route modules separate project, document, and analysis operations. Canonical
scientific request/response DTOs remain in `scopecheck.contracts`; additional
project/version/history responses live in `api/schemas.py`. The public
specification and examples are in `docs/API.md`.

## File storage

`api/services/document_storage.py` accepts only PDF and DOCX extensions, reads
uploads in bounded chunks, enforces `SCOPE_MAX_UPLOAD_BYTES`, rejects empty
files, and writes to a UUID-generated name under `SCOPE_STORAGE_DIR`. The
original filename remains metadata. A SHA-256 checksum and numbered version
record are committed with each upload. If database work fails, the just-written
file is removed. Parsing stays behind the ingestion integration boundary;
stored bytes report `uploaded`, while the document version remains `pending`.

## Analysis orchestration and adapters

`api/services/analysis.py` owns the flow from selection validation through run
creation, adapter invocation, and result persistence. `PipelineAdapter` accepts
the canonical `AnalyzeRequest` plus ordered `(document_id, local_path)` pairs
and returns `AnalyzeResponse`. The default `UnavailablePipelineAdapter` raises
`PipelineUnavailable`. The API records the failed run and reports an explicit
503; it does not produce synthetic scientific output. On success, claim/evidence
records with a matching uploaded document are stored with their source version,
and each comparison is stored as structured JSON with its relation, confidence,
IDs, and explanation.

Agent 9 should provide an adapter implementing:

```python
class ScopePipelineAdapter:
    algorithm_version: str

    def analyze(self, request: AnalyzeRequest,
                document_paths: list[tuple[str, str]]) -> AnalyzeResponse: ...
```

Set `app.state.pipeline_adapter` to an instance during app assembly. The
adapter should map the selected stored files to integrated parser/retrieval
inputs, preserve canonical source IDs and exact quotes, and return the shared
Pydantic response. For corpus work, add `analyze_corpus(benchmark_id,
document_ids)` returning `AnalyzeCorpusResponse`; the backend checks for this
optional method and currently reports unavailable when absent. Do not import
the scientific modules into route code.

## Processing and failures

Document versions and analysis runs store `pending`, `processing`, `completed`,
or `failed`; runs also store completion time and a sanitized failure reason.
Uploads remain pending for ingestion. Run status and results have read routes.
The current analysis request executes synchronously. A future worker should
claim a committed pending run, update it to processing, commit durable results,
and write failure time/reason on errors. FastAPI in-process background tasks
would not provide durable queue semantics; use a database-backed job claim or
proper queue when work becomes asynchronous.

Domain errors use a stable `code` and `message`; validation errors retain
FastAPI's standard 422 response. Raw filesystem paths, credentials, and full
source documents are not returned.

## Security limits

The local API has no login, user ownership, or tenant isolation. Project IDs
are not authorization. CORS defaults to local frontend origins and can be
configured with `SCOPE_CORS_ORIGINS`; no secret is hardcoded. Treat the service
as a single-user local prototype. Production requires authentication and
per-record authorization, private storage, managed secrets, and reviewed upload
controls.

## Local execution and PostgreSQL

Install with `python -m pip install -e '.[dev,database]'`, then run
`uvicorn api.main:app --reload`. SQLite data is stored at `data/scope.db`, and
uploads under `data/uploads/`. Set `SCOPE_DATABASE_URL` to a PostgreSQL SQLAlchemy
URL and configure a private `SCOPE_STORAGE_DIR` to select those adapters. The
schema avoids SQLite-only types, but PostgreSQL operation has not been tested in
this local workstream. Add Alembic migrations and integration checks as part of
deployment preparation.
