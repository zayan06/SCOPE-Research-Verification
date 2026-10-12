"""Stable entrypoint for extracting source-grounded atomic claims."""

from scopecheck.contracts import AtomicClaim


def extract_claims(text: str, document_id: str) -> list[AtomicClaim]:
    """Return atomic claims with source spans and explicit unknown scope fields."""
    raise NotImplementedError("claim extractor implementation is not installed")
