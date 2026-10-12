#!/usr/bin/env python3
"""Evaluate supplied predictions against normalized benchmark JSONL records."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError
from scopecheck.evaluation.metrics import classification_metrics
from scopecheck.evaluation.schema import BenchmarkPair, validate_pairs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True, help="CSV with pair_id,predicted_label; optional predicted_quote,confidence")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--dataset-version", required=True)
    parser.add_argument("--algorithm-version", required=True)
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--config", default="{}", help="JSON object describing experiment settings")
    args = parser.parse_args()
    try:
        cfg = json.loads(args.config)
        if not isinstance(cfg, dict):
            raise ValueError("--config must be a JSON object")
        raw = args.benchmark.read_bytes()
        rows = validate_pairs(BenchmarkPair.model_validate_json(line) for line in raw.splitlines() if line.strip())
        if not rows:
            raise ValueError("benchmark is empty")
        with args.predictions.open(newline="", encoding="utf-8") as handle:
            predictions = list(csv.DictReader(handle))
        pred_ids = [r.get("pair_id", "") for r in predictions]
        if len(pred_ids) != len(set(pred_ids)):
            raise ValueError("duplicate prediction pair_id values")
        expected = {row.pair_id for row in rows}
        provided = set(pred_ids)
        if expected - provided:
            raise ValueError(f"missing predictions for pair IDs: {', '.join(sorted(expected-provided))}")
        if provided - expected:
            raise ValueError(f"prediction IDs absent from benchmark: {', '.join(sorted(provided-expected))}")
        pred_by_id = {r["pair_id"]: r for r in predictions}
        gold = [row.gold_label for row in rows]
        guesses = [pred_by_id[row.pair_id].get("predicted_label", "") for row in rows]
        result = classification_metrics(gold, guesses)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        merged = []
        errors = []
        quote_checked = []
        for row, guess in zip(rows, guesses):
            p = pred_by_id[row.pair_id]
            item = {**row.model_dump(), "predicted_label": guess,
                    "predicted_quote": p.get("predicted_quote", ""), "confidence": p.get("confidence", "")}
            merged.append(item)
            if guess != row.gold_label:
                errors.append({"pair_id": row.pair_id, "gold_label": row.gold_label,
                               "predicted_label": guess, "claim": row.claim, "evidence": row.evidence,
                               "notes": row.notes or ""})
            if p.get("predicted_quote") and row.source_location:
                quote_checked.append(p["predicted_quote"].strip() == row.evidence.strip())
        with (args.output_dir / "predictions.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(merged[0]))
            writer.writeheader(); writer.writerows(merged)
        with (args.output_dir / "confusion_matrix.csv").open("w", newline="", encoding="utf-8") as handle:
            labels = list(result["confusion_matrix"])
            writer = csv.writer(handle); writer.writerow(["gold\\predicted", *labels])
            for label in labels: writer.writerow([label, *[result["confusion_matrix"][label][p] for p in labels]])
        with (args.output_dir / "error_analysis.csv").open("w", newline="", encoding="utf-8") as handle:
            fields = ["pair_id", "gold_label", "predicted_label", "claim", "evidence", "notes"]
            writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(errors)
        result["exact_quote_accuracy"] = (sum(quote_checked) / len(quote_checked) if quote_checked else None)
        result["exact_quote_evaluated_count"] = len(quote_checked)
        (args.output_dir / "metrics.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        try:
            commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=Path.cwd(), text=True).strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            commit = None
        metadata = {
            "experiment_id": args.experiment_id, "dataset_name": rows[0].dataset_category,
            "dataset_version": args.dataset_version, "dataset_sha256": hashlib.sha256(raw).hexdigest(),
            "sample_count": len(rows), "class_distribution": dict(Counter(gold)),
            "algorithm_version": args.algorithm_version, "configuration": cfg,
            "random_seed": args.seed, "git_commit": commit,
            "execution_timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "inputs": {"benchmark": str(args.benchmark), "predictions": str(args.predictions)},
        }
        (args.output_dir / "experiment_metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, ValueError, ValidationError, json.JSONDecodeError) as exc:
        print(f"evaluation error: {exc}", file=sys.stderr)
        return 2
    print(f"Evaluated {len(rows)} pairs; wrote artifacts to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
