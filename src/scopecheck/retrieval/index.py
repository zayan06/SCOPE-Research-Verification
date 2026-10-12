"""Stable retrieval interfaces shared by local and replaceable index backends."""

from collections.abc import Sequence
from typing import Protocol

from scopecheck.contracts import EvidenceChunk, RetrievalHit


class EvidenceIndex(Protocol):
    """Searchable evidence index. Implementations may be local or remote."""

    def search(
        self,
        query: str,
        k: int = 5,
        allowed_document_ids: Sequence[str] | None = None,
    ) -> list[RetrievalHit]:
        """Return at most k ranked hits, honoring document allow-lists."""
        ...


def build_index(chunks: Sequence[EvidenceChunk]) -> EvidenceIndex:
    """Build an index from evidence chunks using the configured adapter."""
    raise NotImplementedError("retrieval index implementation is not installed")
