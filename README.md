# SCOPE

**Scope-Aware Claim–Evidence Alignment for Scientific Literature Verification**

SCOPE is a local research prototype that helps researchers inspect whether
selected literature passages support, contradict, qualify, or do not establish
claims in a draft. Its heuristic labels support human review; they do not
establish scientific truth or calibrated probabilities.

## Current implementation

Stage A integrates the following Python components:

- TXT/Markdown ingestion with stable chunk IDs, exact text, offsets, and
  section metadata. PDF parsing is optional through Docling; DOCX parsing
  requires `python-docx`.
- Offline atomic claim extraction with explicit unknown scope fields.
- In-memory TF-IDF, BM25, and hybrid retrieval with selected-document filters.
- Text-only and scope-aware rule comparators that preserve exact evidence
  quotes and dimension explanations.
- A pipeline for draft text or supplied claims, source selection, top-K
  retrieval, mode choice, and canonical JSON serialization.

Stage B adds a FastAPI backend for project creation, versioned document upload,
parsing and evidence storage, real pipeline analysis, and persisted run/result
history. SQLite is the local database. Upload supports PDF, DOCX, TXT,
Markdown, and `.markdown`; TXT/Markdown parsing works without optional parser
packages. The React frontend is still a separate workstream and has not been
merged.

The repository also contains a 30-paper literature review scaffold and a
proposed research design. The bibliography has metadata/abstract checks and
selective full-text appraisal; it is not an exhaustive systematic review.

## Install and run the API

Requires Python 3.11 or newer.

```sh
python -m pip install -e '.[dev,database]'
python -m pip install 'scikit-learn>=1.4,<2'
uvicorn api.main:app --reload
```

The API defaults to SQLite at `data/scope.db` and uploads at `data/uploads/`.
OpenAPI is at `http://127.0.0.1:8000/api/openapi.json`, Swagger UI at
`http://127.0.0.1:8000/api/docs`, and health at `/api/health`.

Configure `SCOPE_DATABASE_URL`, `SCOPE_STORAGE_DIR`,
`SCOPE_MAX_UPLOAD_BYTES`, `SCOPE_CORS_ORIGINS`, and `SCOPE_MODE` as needed.
Install `.[ingestion]` for PDF support and `python-docx` separately for DOCX.
Gemini and dense retrieval are optional and not required for local analysis.

## API workflow

Create a project, upload a source, and analyze draft text against selected
documents:

```sh
curl -H 'Content-Type: application/json' \
  -d '{"name":"Literature review"}' \
  http://127.0.0.1:8000/api/projects

curl -F project_id=PROJECT_ID -F file=@paper.md \
  http://127.0.0.1:8000/api/documents

curl -H 'Content-Type: application/json' \
  -d '{"draft_text":"The intervention improves the outcome.","selected_document_ids":["DOCUMENT_ID"]}' \
  http://127.0.0.1:8000/api/analyze
```

`POST /api/documents` parses and stores evidence chunks before reporting
`ready`. `POST /api/analyze` extracts claims, retrieves only selected source
documents, runs the scope-aware comparator, and stores comparisons with exact
quotes. Mixed-project corpus selections are rejected. Project, document,
analysis-run, and stored-result read endpoints are documented in
[`docs/API.md`](docs/API.md).

## Runnable end-to-end API demonstration

```sh
python scripts/run_backend_demo.py
```

This executes real project, upload, parse, analyze, and stored-result requests
against a temporary SQLite database using the integrated algorithms. It uses
the clearly labeled synthetic development passage in
`data/samples/development_demo.md`; it is not scientific evidence. Actual
request and response bodies are saved in
`data/outputs/backend_demo.json`.

The lower-level pipeline demonstration is `python scripts/run_demo.py`.
Synthetic comparator and retrieval development checks run with
`python scripts/run_development_checks.py`; their generated metrics are not
scientific benchmark results.

## Tests and evaluation status

Run the complete software suite with:

```sh
python -m pytest -q
```

Tests cover contracts, ingestion, extraction, retrieval, alignment, evaluation,
the unified pipeline, and end-to-end API workflows on temporary SQLite
databases. Synthetic fixtures validate software behavior only. Authentic
scientific benchmark evaluation remains pending because there is no
licensed, human-reviewed SCOPE claim–evidence set.

## Literature and methodology

- [30-paper review matrix](docs/literature/review_matrix.csv)
- [Critical synthesis](docs/literature/critical_synthesis.md)
- [Prior-art comparison](docs/literature/prior_art_comparison.md)
- [Proposed research design](docs/methodology/research_design.md)
- [Report outline and readiness notes](docs/report/report_outline.md)

These materials identify substantial overlap with prior scientific claim
verification. They frame scope-aware comparison as a hypothesis to test, not a
novelty or performance finding. Students should read the full papers, verify
interpretations, and write their own final academic analysis.

## Limitations and frontend readiness

The extractor, retriever, and comparator are English lexical/rule-based
heuristics; confidence values are not calibrated. Real PDF parsing quality,
OCR, and page-coordinate provenance have not been verified. Corpus evaluation
has no connected benchmark adapter. The backend is synchronous and has no
authentication, authorization, multi-user isolation, or schema migration
runner; keep it local and single-user. Frontend integration can use the
documented OpenAPI contract and the project/document/analyze/run-history
endpoints, but must retain the single-user deployment boundary and show the
heuristic and evidence-review status clearly.
