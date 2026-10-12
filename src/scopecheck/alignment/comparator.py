"""Stable entrypoint for comparing one claim and one retrieved passage."""

from scopecheck.contracts import AtomicClaim, ComparisonResult, RetrievalHit


def compare_claim_to_hit(claim: AtomicClaim, hit: RetrievalHit) -> ComparisonResult:
    """Compare dimensions explicitly; unknown values must remain unknown."""
    raise NotImplementedError("claim-evidence comparator implementation is not installed")
