# Backend architecture

## Data model

`api/database/models.py` defines projects, documents, numbered document
versions, evidence chunks, atomic claims, analysis runs, and comparison
results. Foreign keys and indexes preserve project/version/run relationships.
JSON columns retain scope, source spans, chunk metadata, corpus selection, and
complete comparison contracts. SQLite is the local default; PostgreSQL support
is designed but was not exercised. `create_all` initializes new databases;
there is no schema migration runner.

## API structure

`api/main.py` configures FastAPI, CORS, health, OpenAPI, routes, and the real
`ScopePipelineAdapter`. Project, document, and analysis routes are separated
under `api/routes/`. Canonical claim and comparison DTOs remain in
`scopecheck.contracts`; project/version/history response DTOs live in
`api/schemas.py`. The endpoint contract and request examples are in
[`docs/API.md`](../API.md).

## Upload and ingestion

`api/services/document_storage.py` accepts PDF, DOCX, TXT, Markdown, and
`.markdown` files; it applies the upload size limit, stores under a generated
UUID filename, records a SHA-256 checksum, and never uses the submitted name as
a storage path. `api/services/ingestion.py` parses each version immediately
and persists its `EvidenceChunk` text, page/section, offsets, and metadata under
that version. Successful uploads report `ready`; parse failures roll back the
document/version and remove the just-written file. TXT/Markdown work offline;
PDF needs Docling and DOCX needs `python-docx`.

## Analysis pipeline

`api/services/analysis.py` validates the selected corpus, creates an analysis
run, invokes the adapter, and persists returned comparisons. The default
`ScopePipelineAdapter` calls `scopecheck.pipeline.analyze` with the selected
document ID/path mapping. That pipeline extracts draft claims, builds the local
TF-IDF index, retrieves only selected-document evidence, and applies the
scope-aware comparator. Draft text is not indexed as evidence. Mixed-project
selection is rejected. The API preserves document/chunk IDs, filename,
offsets, exact quotations, and comparison dimensions while omitting internal
storage paths from responses.

Analysis is synchronous. Tests can inject a fake adapter to isolate route
behavior, but the application default performs real local analysis. Corpus
benchmark execution remains unavailable until a validated evaluation adapter
is supplied.

## Run state, failure handling, and security

Document versions report `ready` or `failed`; analysis runs report
`processing`, `completed`, or `failed`. Domain errors use stable codes and
messages. The current service is a single-user local prototype with no
authentication or authorization. Project membership constrains each analysis
corpus, but project IDs are not user credentials. Do not expose this backend as
a multi-user service without principal-based record authorization, private
storage, upload controls, managed secrets, and reviewed deployment settings.

## Local execution

Install with `python -m pip install -e '.[dev,database]'`, then install
`scikit-learn>=1.4,<2` for TF-IDF retrieval. Run `uvicorn api.main:app --reload`.
SQLite data defaults to `data/scope.db`; uploads default to
`data/uploads/`. Configure `SCOPE_DATABASE_URL`, `SCOPE_STORAGE_DIR`,
`SCOPE_MAX_UPLOAD_BYTES`, `SCOPE_CORS_ORIGINS`, and `SCOPE_MODE` as needed.
Adopt Alembic migrations before evolving a deployed database.
