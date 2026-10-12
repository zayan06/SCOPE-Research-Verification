# SCOPE

**Scope-Aware Claim–Evidence Alignment for Scientific Literature Verification**

SCOPE is a local research prototype that helps researchers inspect whether
selected literature passages support, contradict, qualify, or do not establish
claims in a draft. Its rule-based labels are review aids, not scientific truth
judgments or calibrated probabilities.

## Implemented in the core prototype

- TXT/Markdown ingestion with stable evidence IDs, canonical character offsets,
  section metadata, and exact source text. PDF uses optional Docling; DOCX uses
  optional `python-docx`.
- Offline atomic claim extraction with explicit unknown scope fields and exact
  source spans. A Gemini adapter is optional and is not needed locally.
- In-memory TF-IDF, BM25, and reciprocal-rank-fusion retrieval, with selected
  document filtering and verbatim source chunks. Dense retrieval is optional.
- Text-only and scope-aware claim–evidence comparison, including dimension
  explanations and exact evidence quotes.
- A unified pipeline for draft-text or direct-claim input, selected source
  documents, top-K results, comparator mode selection, and JSON serialization.
- Classification and retrieval metrics plus scripts for synthetic development
  checks.

## Architecture

`src/scopecheck/contracts.py` contains the shared Pydantic contracts.
`pipeline.py` connects ingestion → claim extraction → retrieval → alignment.
Each evidence hit preserves its document ID and source chunk. The draft is
processed separately and is excluded from the supporting corpus. Retrieval
uses an explicit allow-list of selected source document IDs.

## Install

Requires Python 3.11 or newer. Install the local package, development tools,
and scikit-learn for the TF-IDF baseline:

```sh
python -m pip install -e '.[dev]'
python -m pip install 'scikit-learn>=1.4,<2'
```

Optional adapters: install `.[ingestion]` for PDF parsing; install
`python-docx` separately for DOCX; install the declared `retrieval` extra only
when using the dense Sentence Transformers adapter (it also includes
scikit-learn). No paid service or credentials are required for the local
baseline.

## Run the demonstration

```sh
python scripts/run_demo.py
```

This parses `data/samples/development_demo.md`, accepts the documented draft
claim, retrieves passages, and runs both comparator modes. The source text is
explicitly synthetic and is not a finding or benchmark example. Structured
output is written to `data/outputs/development_demo.json`.

## Run tests and development evaluations

```sh
python -m pytest -q
python scripts/run_development_checks.py
```

The development-check script uses the six fabricated rows in
`data/benchmarks/development_fixtures.jsonl`. It evaluates both comparator
modes on the same claim–evidence pairs and evaluates TF-IDF and BM25 on the
same retrieval queries and judgments. Results are written to
`data/outputs/development_checks.json` and labeled synthetic development
checks. They are not scientific benchmark results.

## Current limitations

- Extraction, retrieval, and comparison use English lexical rules and have not
  been scientifically validated. Scope matching can miss aliases, paraphrases,
  and nuanced experimental context.
- Confidence values are heuristic, not calibrated. Retrieval scores are not
  probabilities. Human review against the original source remains necessary.
- Real PDF parsing, OCR, page-coordinate provenance, and representative DOCX
  behavior have not been verified here.
- There is no licensed, human-reviewed SCOPE benchmark or authentic scientific
  evaluation result. Benchmark evaluation remains pending.
- The full React/FastAPI application, persistence, authentication, and
  multi-user isolation are not part of this Stage A integration.

## Planned application integration

Stage B can call `scopecheck.pipeline.analyze` with an `AnalyzeRequest` and a
mapping from selected document IDs to local paths, then return its canonical
`AnalyzeResponse`. It should preserve source IDs and quotes, enforce selected
document access at its storage boundary, and keep the rule-based nature and
known limitations visible to researchers. The API and UI remain separate
workstreams and are not claimed complete here.
