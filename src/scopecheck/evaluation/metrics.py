"""Dependency-free evaluation metrics with explicit class ordering."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from scopecheck.contracts import Relation


def classification_metrics(
    gold: Sequence[str], predicted: Sequence[str],
    labels: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Return accuracy, macro/per-class P/R/F1 and confusion matrix.

    Confusion rows are gold labels and columns are predictions. Undefined
    precision/recall/F1 are zero. Empty inputs and unknown labels are errors.
    """
    if not gold:
        raise ValueError("classification evaluation requires at least one example")
    if len(gold) != len(predicted):
        raise ValueError(f"gold/prediction length mismatch: {len(gold)} != {len(predicted)}")
    order = list(labels) if labels is not None else [r.value for r in Relation]
    if len(order) != len(set(order)):
        raise ValueError("labels must be unique")
    invalid = (set(gold) | set(predicted)) - set(order)
    if invalid:
        raise ValueError(f"invalid labels: {', '.join(sorted(invalid))}")
    matrix = {g: {p: 0 for p in order} for g in order}
    for actual, guess in zip(gold, predicted):
        matrix[actual][guess] += 1
    per_class: dict[str, dict[str, float]] = {}
    for label in order:
        tp = matrix[label][label]
        fp = sum(matrix[g][label] for g in order if g != label)
        fn = sum(matrix[label][p] for p in order if p != label)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[label] = {"precision": precision, "recall": recall, "f1": f1,
                            "support": sum(matrix[label].values())}
    return {
        "sample_count": len(gold),
        "accuracy": sum(a == p for a, p in zip(gold, predicted)) / len(gold),
        "macro_f1": sum(v["f1"] for v in per_class.values()) / len(order),
        "per_class": per_class,
        "confusion_matrix": matrix,
        "class_distribution": dict(Counter(gold)),
    }


def retrieval_metrics(
    relevant_ids: Mapping[str, Sequence[str]],
    ranked_ids: Mapping[str, Sequence[str]],
    ks: Sequence[int] = (1, 5, 10),
) -> dict[str, float | int]:
    """Compute macro Recall@K over queries with at least one relevant item and MRR.

    A query with no relevant ids is rejected rather than silently changing the
    denominator. Missing ranked queries count as an empty result list.
    """
    if not relevant_ids:
        raise ValueError("retrieval evaluation requires at least one query")
    if any(k <= 0 for k in ks) or len(set(ks)) != len(ks):
        raise ValueError("k values must be unique positive integers")
    if any(not values for values in relevant_ids.values()):
        raise ValueError("every retrieval query must have at least one relevant item")
    recalls = {k: [] for k in ks}
    reciprocal_ranks = []
    for query, relevant in relevant_ids.items():
        rel = set(relevant)
        ranked = list(ranked_ids.get(query, ()))
        first_rank = next((i for i, item in enumerate(ranked, 1) if item in rel), None)
        reciprocal_ranks.append(1.0 / first_rank if first_rank else 0.0)
        for k in ks:
            recalls[k].append(len(rel.intersection(ranked[:k])) / len(rel))
    return {**{f"recall@{k}": sum(v) / len(v) for k, v in recalls.items()},
            "mrr": sum(reciprocal_ranks) / len(reciprocal_ranks),
            "query_count": len(relevant_ids)}
