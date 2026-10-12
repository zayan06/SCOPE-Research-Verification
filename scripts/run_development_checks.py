#!/usr/bin/env python3
"""Run synthetic development checks for comparators and retrieval baselines."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scopecheck.alignment import ComparatorConfig, ComparatorMode, compare_claim_to_hit_with_config
from scopecheck.claims import extract_claims
from scopecheck.contracts import (
    AtomicClaim,
    ClaimType,
    EvidenceChunk,
    ExtractionMethod,
    RetrievalHit,
    RetrievalMethod,
    ScientificScope,
    SourceSpan,
)
from scopecheck.evaluation.metrics import classification_metrics, retrieval_metrics
from scopecheck.retrieval import build_index

ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / "data/benchmarks/development_fixtures.jsonl"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "data/outputs/development_checks.json",
    )
    args = parser.parse_args()
    pairs = [
        json.loads(line)
        for line in BENCHMARK.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    chunks = [
        EvidenceChunk(
            id=row["pair_id"], document_id=row["source_document_id"], text=row["evidence"]
        )
        for row in pairs
    ]
    labels = [row["gold_label"] for row in pairs]
    predictions: dict[str, list[dict[str, str]]] = {}
    comparator_metrics: dict[str, object] = {}
    for mode in (ComparatorMode.TEXT_ONLY, ComparatorMode.SCOPE_AWARE):
        rows: list[dict[str, str]] = []
        for pair, chunk in zip(pairs, chunks):
            document_id = f"draft-{pair['pair_id']}"
            claims = extract_claims(pair["claim"], document_id=document_id)
            claim_text = claims[0] if claims else AtomicClaim(
                id=f"{document_id}:claim-0",
                text=pair["claim"],
                document_id=document_id,
                claim_type=ClaimType.UNKNOWN,
                scope=ScientificScope(),
                source_span=SourceSpan(
                    document_id=document_id,
                    start_offset=0,
                    end_offset=len(pair["claim"]),
                    exact_text=pair["claim"],
                ),
                extraction_method=ExtractionMethod.UNKNOWN,
            )
            hit = RetrievalHit(
                chunk=chunk,
                score=1.0,
                rank=1,
                retrieval_method=RetrievalMethod.UNKNOWN,
            )
            result = compare_claim_to_hit_with_config(
                claim_text, hit, ComparatorConfig(mode=mode)
            )
            rows.append({"pair_id": pair["pair_id"], "predicted_label": result.relation.value})
        predictions[mode.value] = rows
        comparator_metrics[mode.value] = classification_metrics(
            labels, [row["predicted_label"] for row in rows]
        )

    retrieval: dict[str, object] = {}
    relevance = {row["pair_id"]: [row["pair_id"]] for row in pairs}
    for method in (RetrievalMethod.TFIDF, RetrievalMethod.BM25):
        index = build_index(chunks, method=method)
        ranked: dict[str, list[str]] = {}
        for row in pairs:
            hits = index.search(row["claim"], k=len(chunks), method=method)
            ranked[row["pair_id"]] = [hit.chunk.id for hit in hits]
        retrieval[method.value] = {
            "metrics": retrieval_metrics(relevance, ranked, ks=(1, 3, len(chunks))),
            "ranked_ids": ranked,
        }

    artifact = {
        "evaluation_type": "synthetic_development_check",
        "benchmark_fixture": BENCHMARK.relative_to(ROOT).as_posix(),
        "sample_count": len(pairs),
        "warning": "Fabricated fixtures; these metrics are software development checks, not scientific evaluation results.",
        "comparator_predictions": predictions,
        "comparator_metrics": comparator_metrics,
        "retrieval_baselines": retrieval,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Ran {len(pairs)} synthetic pairs; wrote development checks to {args.output}")
    for mode, metrics in comparator_metrics.items():
        print(f"{mode}: accuracy={metrics['accuracy']:.3f}, macro_f1={metrics['macro_f1']:.3f}")
    for method, values in retrieval.items():
        metrics = values["metrics"]
        print(f"{method}: MRR={metrics['mrr']:.3f}, Recall@1={metrics['recall@1']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
