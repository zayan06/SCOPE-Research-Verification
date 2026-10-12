"""Stable entrypoint for parsing supported scientific documents."""

from pathlib import Path

from scopecheck.contracts import EvidenceChunk


def parse_document(path: str | Path, document_id: str) -> list[EvidenceChunk]:
    """Parse a document into source-addressable evidence chunks.

    Implementations must preserve exact text and page/offset provenance when
    available. Unsupported formats and parse failures must raise explicit
    exceptions; parsers must not silently return fabricated or empty content.
    """
    raise NotImplementedError("document parser implementation is not installed")
