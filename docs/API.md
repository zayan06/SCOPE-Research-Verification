# HTTP API contract (v1 foundation)

Base path: `/api`. JSON fields use the shared Pydantic models in
`src/scopecheck/contracts.py`; enums serialize as their listed string values.
The product routes below are **specified but not implemented** in the
foundation commit. Only `GET /api/health` is live. This status distinction is
intentional.

## `GET /api/health` — implemented

Returns `HealthResponse`:

```json
{"status":"ok","version":"0.1.0","mode":"local_development"}
```

This reports process responsiveness only. It is not authentication,
authorization, or a production security signal.

## `POST /api/documents` — specified

- Request: `multipart/form-data`, field `file` containing one supported PDF or
  DOCX. Original filename is metadata, not a storage path.
- Success: `201 DocumentUploadResponse` (`document_id`, `filename`, `status`,
  `message`). Parse failures must return a clear error and must not register a
  partial document as ready.
- Initial contract does not define user identity; do not infer multi-user
  isolation from this development API.

## `GET /api/documents` — specified

- Query: optional `status` filter and bounded `limit` (default 50, max 200).
- Success: `200 list[DocumentSummary]`.
- Ordering is newest first; cursor pagination is deferred until persistence.

## `POST /api/analyze` — specified

- Request: `AnalyzeRequest` with `draft_text` and non-empty
  `selected_document_ids`.
- Success: `200 AnalyzeResponse`, containing `ClaimAnalysis` objects. Each
  comparison retains claim and evidence IDs and the exact evidence quote.
- Unknown scope fields remain explicit unknowns in serialized claims.

## `POST /api/analyze-corpus` — specified

- Request: `AnalyzeCorpusRequest` with `benchmark_id` and non-empty
  `corpus_document_ids`.
- Success: `202 AnalyzeCorpusResponse` when queued, or `200` for a synchronous
  local run. Response includes status and an output path when available. It
  must never return fabricated metrics.
- Benchmark manifests must provide provenance, license, schema, and version.

## Error envelope

When routes are implemented, use FastAPI's standard validation response for
invalid request bodies and a stable JSON error object with `code`, `message`,
and optional `details` for domain errors. Do not expose secrets, raw filesystem
paths, or full document contents in errors.
