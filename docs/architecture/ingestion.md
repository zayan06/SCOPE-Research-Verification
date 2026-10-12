# Scientific document ingestion

## Pipeline

`scopecheck.ingestion.parse_document(path, document_id)` dispatches by file
extension and returns validated `EvidenceChunk` models. TXT and Markdown are
decoded locally as UTF-8 (an optional UTF-8 BOM is accepted). PDF is converted
with Docling when its optional package is installed. DOCX is converted with
`python-docx` when installed. Parser-specific output is normalized to a small
internal representation of ordered text blocks, headings, section paths,
block kinds, and any known page numbers. The public contract remains the shared
`EvidenceChunk`; no contract changes are needed by retrieval.

Markdown ATX headings (`#` through `######`) build section paths. Blank-line
paragraph boundaries, simple pipe-table rows, and `Figure`/`Table` caption
prefixes are identified without rewriting source wording. DOCX paragraph and
table cell text is emitted in document order where available. Docling's
Markdown export is used for PDF content, including tables/captions it recognizes.
Input order is retained.

## Chunking choice

Chunking groups complete structural blocks until the deterministic word-token
estimate reaches 650 tokens. A new section begins a fresh chunk, and headings
stay with the content in their block. A block larger than 760 words is divided
near sentence boundaries around 600 words. Up to 80 words of prior blocks are
carried into the next chunk by default. Configure the target and overlap with
`SCOPECHECK_CHUNK_TOKENS` and `SCOPECHECK_CHUNK_OVERLAP`; overlap must be smaller
than the target. The estimator is intentionally dependency-free and is not a
model tokenizer, so chunks are approximate rather than strict token limits.

## Source locations and IDs

TXT and Markdown offsets are zero-based, half-open character offsets into the
decoded file text. Converted formats use offsets into the parser's canonical
exported text (Docling Markdown or the generated DOCX text), never byte offsets
into the PDF/DOCX container. Chunk text is the exact canonical source slice;
outer whitespace is excluded to match the shared Pydantic contract's string
normalization. Page numbers are one-based only when a parser supplies reliable
page provenance. The current Docling Markdown path does not map each exported
block back to a page, so PDF page numbers remain null. Unknown values are not
guessed.

Each ID is `document_id` plus a truncated SHA-256 digest over the document ID,
start/end offsets, and exact chunk text. Repeated parsing of the same canonical
document with the same ID yields stable IDs. Different document IDs produce
different IDs for otherwise identical text.

The `metadata` object includes the source filename/path, parser name, section
path, block kinds, document metadata available from the backend, and a flag
that offsets refer to canonical parser text. `chunks_to_json(chunks)` provides
an indented JSON array for debugging.

## Supported formats and limitations

| Format | Behavior |
| --- | --- |
| `.txt` | Built-in UTF-8 text parsing; no external service/dependency. |
| `.md`, `.markdown`, `.mdown` | Built-in text parsing and ATX heading extraction. |
| `.pdf` | Docling optional extra; without it, raises an install-guidance error. |
| `.docx` | Optional `python-docx`; without it, raises an install-guidance error. |

Empty supported documents return `[]`. Unsupported extensions, missing or
unreadable paths, invalid UTF-8, malformed PDF signatures, and parser failures
raise explicit `ValueError` or `RuntimeError` exceptions. The implementation
does not OCR scanned PDFs itself. PDF extraction quality depends on Docling and
the source layout; PDF per-page coordinates are not yet preserved. DOCX table
structure is rendered as text rows, and images/figure relationships are not
extracted. Markdown support intentionally recognizes ATX headings but does not
implement the complete CommonMark grammar. Python-docx is an optional runtime
dependency not declared in the repository's shared dependency file.

## Downstream retrieval

Pass returned chunks directly to `scopecheck.retrieval.build_index(chunks)`.
Retrieval hits retain the same chunk ID, document ID, text, and provenance
metadata. Consumers should use `metadata.source_path`, `section_name`, offsets,
and page number when available to reopen and inspect the original document.
Offsets in converted formats address the canonical parser export, not the
binary document.

## Executable example

Run from the repository root after installing the package (the TXT/Markdown
example requires no optional parser):

```python
from pathlib import Path

from scopecheck.ingestion import chunks_to_json, parse_document

document_path = Path("tests/fixtures/ingestion/sample.md")
chunks = parse_document(document_path, document_id="helios-paper")

# Sections are visible as chunk section paths; the JSON keeps text and source
# metadata together for inspection or handoff to retrieval.
for chunk in chunks:
    print(chunk.section_name, chunk.text[:80])
print(chunks_to_json(chunks))
```
