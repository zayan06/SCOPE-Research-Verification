"""Reproducible metrics and artifact writing for SCOPE experiments.

The evaluator is intentionally independent of retrieval and alignment
implementations. Callers provide gold labels and predictions explicitly.
"""

from .metrics import classification_metrics, retrieval_metrics
from .schema import BenchmarkPair, validate_pairs

__all__ = ["BenchmarkPair", "classification_metrics", "retrieval_metrics", "validate_pairs"]
