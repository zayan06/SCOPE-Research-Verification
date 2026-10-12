# Ingestion workstream handoff

## Workstream and branch

- Workstream: scientific document ingestion and evidence chunking
- Branch: `feat/ingestion`
- Implementation commit: to be recorded after the code-and-test commit

## Implemented features

- Built-in UTF-8 parsing for TXT and Markdown variants, with Markdown ATX
  headings, section paths, captions, and simple table block identification.
- Optional Docling PDF conversion and optional python-docx DOCX conversion.
- Structure-aware chunking with configurable target/overlap, long paragraph
  splitting at sentence boundaries, and stable document-scoped IDs.
- Validated `EvidenceChunk` construction, canonical character offsets,
  metadata, source-slice traceability, and JSON serialization.
- Clear errors for unsupported formats, invalid UTF-8, missing inputs, bad PDF
  signatures, and unavailable parser dependencies. Empty supported files
  return an empty list.

## Public interfaces

```python
parse_document(path: str | Path, document_id: str) -> list[EvidenceChunk]
chunks_to_json(chunks: Iterable[EvidenceChunk], *, indent: int = 2) -> str
```

They are exported from `scopecheck.ingestion`. Chunk-size defaults are 650
word-like tokens and 80 overlap tokens, configurable with
`SCOPECHECK_CHUNK_TOKENS` and `SCOPECHECK_CHUNK_OVERLAP`.

## Files changed

- `src/scopecheck/ingestion/parser.py`
- `src/scopecheck/ingestion/__init__.py`
- `tests/test_ingestion.py`
- `tests/fixtures/ingestion/sample.md`
- `tests/fixtures/ingestion/sample.txt`
- `docs/architecture/ingestion.md`
- `docs/handoffs/ingestion.md`

The chunk-boundary test writes its generated multi-paragraph input to pytest's
temporary directory; it does not add a generated fixture to the repository.

## Dependencies

- No new required/shared dependencies.
- TXT/Markdown use only the Python standard library and existing Pydantic
  contract.
- PDF uses the already-declared optional `docling` ingestion extra.
- DOCX uses optional `python-docx`, which is not currently declared in the
  shared project configuration; install it separately to enable DOCX.

## Tests and actual results

Executed with the bundled Python 3.12 runtime, with this worktree's `src`
explicitly first on `PYTHONPATH` because the environment's editable package
otherwise resolves to the base checkout:

```sh
PYTHONPATH=src /Users/zayan/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest -q tests/test_ingestion.py
```

Result: **9 passed**. The focused tests cover TXT scientific text and provenance,
Markdown structure/values/negation/tables/captions, chunk boundaries and
overlap, reproducible IDs, empty files, invalid inputs, and PDF dispatch.
Docling is not installed in this environment. The successful PDF adapter test
uses a mocked Docling converter; a real scientific PDF has not been parsed or
quality-checked here. A separate test verifies the explicit missing-Docling
message.

Full-suite command:

```sh
PYTHONPATH=src /Users/zayan/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest -q
```

Result: **17 passed, 1 warning**. The warning is a Starlette deprecation
warning for its current httpx TestClient integration. `git diff --check` also
completed without errors.

## Example usage

```python
from pathlib import Path
from scopecheck.ingestion import chunks_to_json, parse_document

chunks = parse_document(Path("paper.md"), document_id="paper-01")
print(chunks[0].section_name)
print(chunks_to_json(chunks))
```

## Known limitations

- Chunk sizing uses a deterministic word approximation rather than a model's
  tokenizer; the target is approximate.
- Current PDF export does not recover per-chunk page numbers or coordinates;
  those remain null. PDF offsets refer to Docling's exported canonical text.
- No built-in OCR is provided for scanned PDFs.
- DOCX tables are represented as text rows; image/figure extraction is not
  implemented. DOCX conversion requires separately installed python-docx.
- Markdown parsing recognizes ATX headings and simple table/caption patterns,
  not the complete CommonMark syntax.
- Actual Docling parsing behavior remains unverified until tested with Docling
  installed and representative PDFs.

## Integration instructions

1. Merge this branch through the integration workstream; do not change the
   shared contract.
2. Import `parse_document` from `scopecheck.ingestion` and pass its returned
   chunks to `scopecheck.retrieval.build_index`.
3. Use `document_id`, `section_name`, offsets, page number, and metadata to
   preserve source identity when storing retrieval results.
4. Install `.[ingestion]` for PDF. Install `python-docx` separately for DOCX.
5. For converted formats, interpret offsets against the canonical parser text,
   not offsets in the binary file.

## Commit hash

The code-and-test commit hash will be added before this handoff is finalized.
