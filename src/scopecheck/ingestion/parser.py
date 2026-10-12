"""Structure-aware, local-first parsing for scientific source documents.

Text offsets are zero-based, half-open character offsets in the parser's
canonical text representation. For TXT and Markdown that is the decoded file;
for converted formats it is the backend's exported text.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from scopecheck.contracts import EvidenceChunk

_WORD_RE = re.compile(r"\S+")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_CAPTION_RE = re.compile(r"^(?:fig(?:ure)?|table)\s+[\w.-]+\s*[:.]", re.I)


@dataclass
class _Block:
    start: int
    end: int
    text: str
    kind: str = "paragraph"
    page_number: int | None = None
    section_name: str | None = None


@dataclass
class _ParsedDocument:
    text: str
    blocks: list[_Block]
    parser_name: str
    metadata: dict[str, Any] = field(default_factory=dict)


def parse_document(path: str | Path, document_id: str) -> list[EvidenceChunk]:
    """Parse TXT, Markdown, PDF, or DOCX into traceable evidence chunks.

    Empty supported files produce an empty list. Unsupported extensions,
    unreadable files, and unavailable optional parsers raise clear exceptions.
    Chunk size and overlap can be adjusted with ``SCOPECHECK_CHUNK_TOKENS`` and
    ``SCOPECHECK_CHUNK_OVERLAP`` environment variables.
    """
    source = Path(path)
    if not document_id.strip():
        raise ValueError("document_id must not be empty")
    suffix = source.suffix.lower()
    if suffix in {".txt", ".md", ".markdown", ".mdown"}:
        parsed = _parse_text_file(source, suffix)
    elif suffix == ".pdf":
        parsed = _parse_pdf(source)
    elif suffix == ".docx":
        parsed = _parse_docx(source)
    else:
        raise ValueError(f"unsupported document format: {suffix or '(no extension)'}")
    if not parsed.text.strip():
        return []
    target = _positive_env_int("SCOPECHECK_CHUNK_TOKENS", 650)
    overlap = _nonnegative_env_int("SCOPECHECK_CHUNK_OVERLAP", 80)
    if overlap >= target:
        raise ValueError("SCOPECHECK_CHUNK_OVERLAP must be smaller than chunk target")
    return _chunk_document(parsed, document_id.strip(), source, target, overlap)


def chunks_to_json(chunks: Iterable[EvidenceChunk], *, indent: int = 2) -> str:
    """Serialize evidence chunks as a JSON array for inspection/debugging."""
    return json.dumps([chunk.model_dump(mode="json") for chunk in chunks], ensure_ascii=False, indent=indent)


def _parse_text_file(path: Path, suffix: str) -> _ParsedDocument:
    raw = _read_bytes(path)
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{path}: expected UTF-8 text; decoding failed at byte {exc.start}") from exc
    return _from_text(text, "markdown" if suffix != ".txt" else "text", path.name)


def _parse_pdf(path: Path) -> _ParsedDocument:
    raw = _read_bytes(path)
    if not raw.startswith(b"%PDF-"):
        raise ValueError(f"{path}: file does not have a valid PDF signature")
    try:
        converter_mod = importlib.import_module("docling.document_converter")
    except ImportError as exc:
        raise RuntimeError(
            "PDF parsing requires the optional Docling dependency. Install with `pip install '.[ingestion]'`."
        ) from exc
    try:
        converter = converter_mod.DocumentConverter()
        result = converter.convert(str(path))
        document = result.document
        markdown = document.export_to_markdown()
    except Exception as exc:  # backend failures vary by input and Docling version
        raise ValueError(f"{path}: Docling could not parse this PDF: {exc}") from exc
    if not isinstance(markdown, str):
        raise ValueError(f"{path}: Docling returned no text for this PDF")
    metadata: dict[str, Any] = {"backend": "docling"}
    for key in ("name", "title", "authors", "created", "modified"):
        value = getattr(document, key, None)
        if value:
            metadata[key] = str(value)
    return _from_text(markdown, "docling", path.name, metadata)


def _parse_docx(path: Path) -> _ParsedDocument:
    _read_bytes(path)  # check existence/readability before importing the backend
    try:
        docx = importlib.import_module("docx")
    except ImportError as exc:
        raise RuntimeError(
            "DOCX parsing requires python-docx. Install it in the environment to enable DOCX support."
        ) from exc
    try:
        document = docx.Document(str(path))
        pieces: list[str] = []
        for paragraph in document.paragraphs:
            pieces.append(paragraph.text)
        for table_index, table in enumerate(document.tables, start=1):
            pieces.append(f"Table {table_index}")
            pieces.extend(" | ".join(cell.text for cell in row.cells) for row in table.rows)
        text = "\n\n".join(piece for piece in pieces if piece)
        metadata = {"backend": "python-docx"}
        core = document.core_properties
        for key in ("title", "subject", "author", "keywords", "created", "modified"):
            value = getattr(core, key, None)
            if value:
                metadata[key] = str(value)
    except Exception as exc:
        raise ValueError(f"{path}: python-docx could not parse this document: {exc}") from exc
    return _from_text(text, "python-docx", path.name, metadata)


def _read_bytes(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:
        raise ValueError(f"cannot read document {path}: {exc}") from exc


def _from_text(text: str, parser_name: str, filename: str, metadata: dict[str, Any] | None = None) -> _ParsedDocument:
    blocks = _split_oversized_blocks(_extract_blocks(text))
    return _ParsedDocument(
        text=text,
        blocks=blocks,
        parser_name=parser_name,
        metadata={"filename": filename, **(metadata or {})},
    )


def _extract_blocks(text: str) -> list[_Block]:
    """Identify paragraphs and Markdown headings without rewriting source text."""
    blocks: list[_Block] = []
    headings: list[tuple[int, str]] = []
    # Blank-line delimited units retain their exact offsets into canonical text.
    for match in re.finditer(r"\S(?:.*?\S)?(?=(?:\r?\n[ \t]*){2,}|\s*\Z)", text, re.S):
        value = match.group(0)
        if not value.strip():
            continue
        line = value.splitlines()[0].strip()
        heading = _HEADING_RE.match(line)
        kind = "paragraph"
        if heading:
            level, title = len(heading.group(1)), heading.group(2).strip()
            headings = [(depth, name) for depth, name in headings if depth < level]
            headings.append((level, title))
            kind = "heading"
        section = " > ".join(name for _, name in headings) or None
        if kind == "paragraph" and _CAPTION_RE.match(line):
            kind = "caption"
        elif kind == "paragraph" and line.startswith("|"):
            kind = "table"
        # The canonical contract strips outer whitespace from model strings;
        # end at the final source character so offsets still describe text exactly.
        blocks.append(_Block(match.start(), match.end(), value, kind, section_name=section))
    return blocks


def _split_oversized_blocks(blocks: list[_Block]) -> list[_Block]:
    """Split very long paragraphs at sentence boundaries, retaining exact spans."""
    result: list[_Block] = []
    for block in blocks:
        if _token_count(block.text) <= 760:
            result.append(block)
            continue
        boundaries = [match.end() for match in re.finditer(r"(?<=[.!?])\s+", block.text)]
        part_start = 0
        for boundary in boundaries:
            if _token_count(block.text[part_start:boundary]) >= 600:
                result.append(_Block(
                    block.start + part_start,
                    block.start + boundary,
                    block.text[part_start:boundary],
                    block.kind,
                    block.page_number,
                    block.section_name,
                ))
                part_start = boundary
        if part_start < len(block.text):
            result.append(_Block(
                block.start + part_start, block.end, block.text[part_start:],
                block.kind, block.page_number, block.section_name,
            ))
    return result


def _chunk_document(parsed: _ParsedDocument, document_id: str, source: Path, target: int, overlap: int) -> list[EvidenceChunk]:
    groups: list[list[_Block]] = []
    current: list[_Block] = []
    token_count = 0
    section: str | None = None
    for block in parsed.blocks:
        count = _token_count(block.text)
        # A new section starts a new chunk where feasible; keep its heading with content.
        if current and block.section_name != section:
            groups.append(current)
            current, token_count = [], 0
        if current and token_count + count > target:
            groups.append(current)
            carry = _overlap_blocks(current, overlap)
            current = carry
            token_count = sum(_token_count(item.text) for item in current)
        current.append(block)
        token_count += count
        section = block.section_name
    if current:
        groups.append(current)

    chunks: list[EvidenceChunk] = []
    seen: set[tuple[int, int]] = set()
    for group in groups:
        start, end = group[0].start, group[-1].end
        if (start, end) in seen:
            continue
        seen.add((start, end))
        exact_text = parsed.text[start:end]
        if not exact_text.strip():
            continue
        pages = {block.page_number for block in group if block.page_number is not None}
        page = next(iter(pages)) if len(pages) == 1 else None
        section_name = next((block.section_name for block in reversed(group) if block.section_name), None)
        digest = hashlib.sha256(
            f"{document_id}\0{start}\0{end}\0{exact_text}".encode("utf-8")
        ).hexdigest()[:20]
        chunks.append(EvidenceChunk(
            id=f"{document_id}:{digest}",
            document_id=document_id,
            text=exact_text,
            section_name=section_name,
            page_number=page,
            start_offset=start,
            end_offset=end,
            metadata={
                "source_path": str(source),
                "source_filename": source.name,
                "parser": parsed.parser_name,
                "section_path": section_name,
                "block_types": list(dict.fromkeys(block.kind for block in group)),
                "document_metadata": parsed.metadata,
                "canonical_text_offsets": True,
            },
        ))
    return chunks


def _overlap_blocks(blocks: list[_Block], overlap: int) -> list[_Block]:
    if overlap <= 0:
        return []
    carried: list[_Block] = []
    count = 0
    for block in reversed(blocks):
        size = _token_count(block.text)
        if not carried and size > overlap:
            break
        if carried and count + size > overlap:
            break
        carried.insert(0, block)
        count += size
        if count >= overlap:
            break
    return carried


def _token_count(text: str) -> int:
    """Fast deterministic word-token approximation used only for chunk sizing."""
    return len(_WORD_RE.findall(text))


def _positive_env_int(name: str, default: int) -> int:
    value = _nonnegative_env_int(name, default)
    if value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _nonnegative_env_int(name: str, default: int) -> int:
    import os
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if value < 0:
        raise ValueError(f"{name} must be nonnegative")
    return value
