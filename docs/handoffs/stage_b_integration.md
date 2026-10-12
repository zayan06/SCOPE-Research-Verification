# Stage B backend and literature integration handoff

## Branches and commits

Integrated on `integrate/scope`:

| Branch | Integrated source commit | Merge commit |
| --- | --- | --- |
| `feat/backend` | `662db6763118518185bc8b86d469951a6ec33cd8` | `ced6a3614ac075276a2d6d5bef0374e70ba292ef` |
| `docs/literature` | `8ab38d76c36e3d494cd65293bdf18fa1c437fcc6` | `4d0f71eb72bd40eb9c6dd26b7a7d05d103e64b17` |
| `feat/frontend` | `711eddeefbc89c103acd7af42220168a4a5c461d` | `492e7dd` |

Stage A was already integrated at `975cb74631536d6aa4e655ea63139fa58999cdbb`.
The Stage B backend connection, ingestion persistence, API tests, runnable
demo, and status/documentation updates are committed as
`4c376e84ea24e7266b6ec3b13baf2cc977ff2d4b` on `integrate/scope`.
Frontend integration and final application checks are recorded in the
follow-on section below. No changes were pushed.

## Integrated backend workflow

The default `api.main.app.state.pipeline_adapter` is now
`ScopePipelineAdapter`, which calls the Stage A `scopecheck.pipeline.analyze`
implementation. The API performs real local claim extraction, selected-source
parsing, TF-IDF retrieval, and scope-aware comparisons.

1. Create a project with `POST /api/projects`.
2. Upload PDF, DOCX, TXT, Markdown, or `.markdown` using `POST /api/documents`.
   TXT/Markdown are built in. PDF needs Docling; DOCX needs `python-docx`.
3. Upload is parsed before success. Canonical evidence text, page/section,
   offsets, filename, and canonical chunk ID are stored under the document
   version. Success reports `ready`; malformed documents fail without leaving
   a partial document/version row.
4. Submit draft text plus selected document IDs to `POST /api/analyze`.
   Draft claims are extracted separately and never included in the evidence
   index.
5. The API requires selected documents to exist, have ready versions, and
   belong to one project. Retrieval receives only those selected IDs. The
   service additionally checks pipeline hits against the selected set and
   verifies each exact quote occurs in its cited source passage.
6. Analysis runs and canonical comparison JSON are stored. The POST response
   returns claims, ranked hits, dimensions, exact quotes, and relationships;
   run status/results are available through the read endpoints below.

The API strips internal upload filesystem paths from returned metadata and
restores the submitted source filename for attribution.

## Frontend integration follow-on

`feat/frontend` is merged. Its live client now reads and creates projects,
lists documents within the active project, uploads using the required
`project_id` form field, and submits selected-document analysis to the real
pipeline API. Live mode never falls back to synthetic examples. The picker
accepts the backend's PDF, DOCX, TXT, and Markdown formats. The core package
dependencies now include SQLAlchemy and `python-multipart`, both required to
load the upload routes in a clean install.

Frontend checks passed after integration: TypeScript typecheck, 10 Vitest tests,
and the production Vite build. `npm ci` reports 13 advisories in development
dependencies (5 moderate, 6 high, 2 critical); the frontend handoff notes that
resolving them requires major-version upgrades. Review annotations remain
session-only; project list summaries do not yet include document/run counts.

## Working endpoints

- `GET /api/health`
- `POST /api/projects`, `GET /api/projects`, `GET /api/projects/{project_id}`,
  `PATCH /api/projects/{project_id}`
- `POST /api/documents`, `GET /api/documents`,
  `GET /api/documents/{document_id}`,
  `GET /api/documents/{document_id}/status`
- `POST /api/analyze`
- `GET /api/analysis-runs/{run_id}`
- `GET /api/analysis-runs/{run_id}/results`
- `GET /api/projects/{project_id}/analysis-runs`
- OpenAPI at `/api/openapi.json`; Swagger UI at `/api/docs`; ReDoc at `/api/redoc`

`POST /api/analyze-corpus` validates and records requests but still returns
`503` because no benchmark execution adapter is connected. It does not invent
evaluation results.

## Tests and checks

Using the prepared Python 3.13 environment with `.[dev]` and
`scikit-learn>=1.4,<2` installed:

- `python -m pytest -q` — **101 passed, 0 failed**, one upstream Starlette/httpx
  deprecation warning.
- `python -m compileall -q api src scripts/run_backend_demo.py` — passed.
- `git diff --check` — passed.
- Literature consistency check — **30 unique matrix records**, **30 unique
  corresponding APA references**, canonical URL/DOI populated for all records.
- End-to-end API tests use temporary SQLite databases and include an actual
  `ScopePipelineAdapter` case covering project creation, parsed upload,
  persisted evidence chunks, selected-document filtering, exact source offsets
  and quotes, real comparison, stored results, and cross-project rejection.

The Starlette warning concerns the installed `httpx` TestClient integration;
no test failed.

## Runnable request/response demonstration

From the repository root:

```sh
python -m pip install -e '.[dev,database]'
python -m pip install 'scikit-learn>=1.4,<2'
python scripts/run_backend_demo.py
```

The script exercises real HTTP requests in FastAPI's `TestClient`, uses a
temporary SQLite database and upload directory, and invokes the real
`ScopePipelineAdapter` (no response mocks). It saves request and response JSON
to `data/outputs/backend_demo.json`. Its one source passage is explicitly
synthetic demonstration text, not scientific evidence or benchmark data. The
observed upload status was `ready`, analysis status `completed`, relationship
`support`, and the returned/stored evidence quote exactly matched the source.

Live-server setup, cURL examples, request DTOs, and error behavior are in
[`docs/API.md`](../API.md).

## Literature and methodology integration

Merged the 30-paper review matrix, APA-style references, critical synthesis,
prior-art comparison, proposed research design, report outline, contribution
template, and AI-assistance log. Status language was reconciled with the
implemented prototype: the computational pipeline and API are implemented,
while the hypotheses remain unvalidated. The review is metadata/abstract
checked with selective full-text appraisal, not an exhaustive systematic
review. Students still need to read and verify the papers and write their own
final academic analysis.

## Frontend integration contract

Frontend work can now use the published OpenAPI schema and the project,
document, analyze, and run-history endpoints. A standard flow is create
project → upload and wait for `ready` → retain returned document ID → submit
`AnalyzeRequest` with the selected IDs → render `AnalyzeResponse` → optionally
refresh the run and stored comparisons. Preserve relation labels, dimension
statuses, source IDs, exact quotes, and explicit insufficient-evidence states.
Do not display confidence as calibrated probability. Keep the local,
single-user security limitation visible and do not imply backend authorization.

## Remaining limitations

- English rule-based extraction, retrieval, and comparison have not been
  validated against an authentic scientific benchmark. Confidence is heuristic.
- The demo and development metrics use synthetic fixtures only. Licensed
  scientific data, human-reviewed labels, benchmark results, ablations, and
  researcher usability results remain pending.
- Real PDF parsing quality, OCR, page-coordinate provenance, and representative
  DOCX parsing have not been verified. Parser extras are optional.
- Analysis is synchronous. There is no durable job queue or database migration
  runner.
- This is a single-user local prototype with no authentication or
  authorization. Project-level checks prevent mixed-project analysis, but IDs
  are not security credentials.
- The React frontend remains unmerged. Corpus benchmark execution remains
  unavailable until a validated adapter is implemented.

## Latest Stage B commit

Implementation commit: `4c376e84ea24e7266b6ec3b13baf2cc977ff2d4b`.
The documentation-only commit containing this handoff follows it on
`integrate/scope`.
