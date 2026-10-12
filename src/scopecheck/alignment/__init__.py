"""Claim-evidence alignment with local deterministic and baseline modes."""

from .comparator import (
    ComparatorConfig,
    ComparatorMode,
    compare_claim_to_hit,
    compare_claim_to_hit_with_config,
)

__all__ = [
    "ComparatorConfig",
    "ComparatorMode",
    "compare_claim_to_hit",
    "compare_claim_to_hit_with_config",
]
