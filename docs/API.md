# SCOPE HTTP API

Base path: `/api`. The canonical analysis DTOs and document upload summaries
come from `scopecheck.contracts`; project, version, and run-history DTOs are
backend additions. OpenAPI is served at `/api/openapi.json`, Swagger UI at
`/api/docs`, and ReDoc at `/api/redoc`.

## Local setup

```sh
python -m pip install -e '.[dev,database]'
uvicorn api.main:app --reload
```

The default SQLite database is `data/scope.db`; uploaded files go to
`data/uploads/`. Configure `SCOPE_DATABASE_URL`, `SCOPE_STORAGE_DIR`,
`SCOPE_MAX_UPLOAD_BYTES` (default 25 MiB), `SCOPE_CORS_ORIGINS` (comma-separated
origins), and `SCOPE_MODE` through the environment. Database tables are created
on startup. The prototype has no schema migration runner yet; back up the local
database before changing the schema.

## Health

`GET /api/health` returns process status only:

```json
{"status":"ok","version":"0.1.0","mode":"local_development"}
```

## Projects

`POST /api/projects` creates a project (`201`). `GET /api/projects?limit=50`
lists newest first; `limit` is 1–200. `GET /api/projects/{project_id}` reads a
project and `PATCH /api/projects/{project_id}` updates a supplied `name` or
`description`.

Request example:

```json
{"name":"Replication review","description":"Draft claims for review"}
```

All return the project fields `id`, `name`, `description`, `created_at`, and
`updated_at`. A nonexistent project returns `404 project_not_found`.

## Documents

`POST /api/documents` accepts `multipart/form-data`: required `file` and
`project_id`; optional `title` and `document_id`. Omit `document_id` to create a
document; supply it to append a version. PDF and DOCX are accepted. Uploads are
size limited, empty uploads are rejected, and the original filename is never
used as a storage path. Each version records a SHA-256 checksum.

```sh
curl -F project_id=PROJECT_ID -F file=@paper.pdf http://127.0.0.1:8000/api/documents
```

Success returns `201 DocumentUploadResponse`, for example:

```json
{"document_id":"UUID","filename":"paper.pdf","status":"uploaded","message":"Stored version 1; document parsing is pending integration."}
```

`uploaded` means the bytes and metadata are stored. It does not mean parsing
succeeded. The version's processing state remains `pending` until an ingestion
adapter updates it.

`GET /api/documents?project_id=UUID&status=uploaded&limit=50` lists documents
newest first (`limit` 1–200). `GET /api/documents/{document_id}` includes all
versions. `GET /api/documents/{document_id}/status` returns the latest version
state and failure reason. Invalid type is `415`, empty file is `400`, size limit
is `413`, and missing project/document is `404`.

## Analysis

`POST /api/analyze` accepts the canonical `AnalyzeRequest`:

```json
{"draft_text":"The intervention improves the outcome.","selected_document_ids":["DOCUMENT_UUID"]}
```

The selected documents must exist, have uploaded versions, and belong to one
project. A connected adapter returns canonical `AnalyzeResponse`; comparisons
are stored with exact evidence quotes and structured comparison JSON. The
current default adapter is deliberately unavailable, so this route returns
`503 pipeline_unavailable` and persists a failed run rather than inventing
claims or predictions. The error includes `analysis_run_id` for status lookup.

`POST /api/analyze-corpus` accepts the foundation `AnalyzeCorpusRequest`. It
validates the corpus and persists a run. Corpus execution returns `503` until
an adapter with `analyze_corpus(benchmark_id, document_ids)` is connected.
There is no benchmark output or fabricated metric in this backend.

`GET /api/analysis-runs/{run_id}` reads status and timestamps;
`GET /api/analysis-runs/{run_id}/results` returns stored comparisons. Project
history is available at `GET /api/projects/{project_id}/analysis-runs?limit=50`.
Statuses are `pending`, `processing`, `completed`, or `failed`.

## Errors

Domain errors use a stable JSON envelope:

```json
{"code":"document_not_found","message":"Document not found."}
```

Some errors include a `details` object. FastAPI's standard `422` validation
body is retained for malformed request bodies. Responses do not expose local
storage paths or document contents.

## Security and deployment limits

This is a single-user local prototype. It has no authentication, authorization,
or tenant isolation; do not expose it as a production multi-user service.
Configure CORS to the frontend origin. Before production use, add authenticated
principal ownership to every project/document/run query, managed secrets,
upload malware/content checks, and operational controls.

SQLite is the local default. PostgreSQL compatibility uses SQLAlchemy's
portable types and `SCOPE_DATABASE_URL`; install the existing `database` extra
for SQLAlchemy and psycopg. Move to Alembic migrations and review JSON/index
behavior before production migration.
