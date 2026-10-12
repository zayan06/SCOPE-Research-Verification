# Submission checkpoint

- **Submission date:** Not yet submitted. Snapshot prepared 2026-10-12.
- **Submitted commit:** Not identified. No submission tag has been created.
- **Current development state:** Stage A scientific pipeline and Stage B local
  FastAPI backend are integrated on `integrate/scope`; the frontend workstream
  has not yet been merged.

## Implemented functionality

- Shared scientific contracts and TXT/Markdown ingestion with source offsets;
  optional Docling PDF and python-docx DOCX adapters.
- Deterministic atomic claim extraction and explicit unknown scope fields.
- TF-IDF/BM25/hybrid retrieval with document filtering.
- Text-only and scope-aware rule-based comparisons with exact evidence quotes.
- Local pipeline and FastAPI project/document/upload/analyze/run-history flow.
- SQLite persistence for projects, versions, parsed evidence chunks, runs, and
  structured comparison results.
- Literature review scaffold with 30 unique source-checked publication
  records, critical synthesis, prior-art comparison, and proposed research
  design. Bibliographic/abstract verification is not exhaustive full-text
  appraisal.

## Validation and research status

- Python tests are software checks; run the exact full suite at report freeze
  and record the commit and actual count.
- Synthetic fixture metrics in `data/outputs/development_checks.json` are
  development checks only, not scientific evaluation.
- **Completed:** local end-to-end software workflow and reproducible synthetic
  checks.
- **Pending:** licensed scientific benchmark acquisition, human-reviewed SCOPE
  labels, source-grouped evaluation splits, ablations, calibration/abstention
  analysis, error analysis on authentic examples, and researcher usability
  study.

## Known limitations

The algorithms are English lexical/rule-based heuristics with no scientific
validation. PDF parsing quality and real PDF provenance were not verified.
The backend is synchronous and single-user, has no authentication or
authorization, and has no schema migration runner. The React frontend is not
integrated in this Stage B snapshot. This repository must not be presented as
having demonstrated the research hypotheses or as determining scientific
truth.
