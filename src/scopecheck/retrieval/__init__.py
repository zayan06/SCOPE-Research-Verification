"""Evidence indexing and retrieval interfaces."""

from .index import (
    DenseEncoder,
    LocalEvidenceIndex,
    RetrievalSettings,
    SentenceTransformerEncoder,
    build_index,
    normalize_query,
)

__all__ = [
    "DenseEncoder", "LocalEvidenceIndex", "RetrievalSettings",
    "SentenceTransformerEncoder", "build_index", "normalize_query",
]
