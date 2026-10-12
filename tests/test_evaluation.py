import csv
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from scopecheck.evaluation.metrics import classification_metrics, retrieval_metrics
from scopecheck.evaluation.schema import BenchmarkPair, validate_pairs


def test_classification_metrics_hand_calculated():
    result = classification_metrics(["support", "support", "contradict"],
                                    ["support", "contradict", "contradict"],
                                    labels=["support", "contradict"])
    assert result["accuracy"] == pytest.approx(2 / 3)
    assert result["per_class"]["support"]["precision"] == pytest.approx(1)
    assert result["per_class"]["support"]["recall"] == pytest.approx(1 / 2)
    assert result["per_class"]["support"]["f1"] == pytest.approx(2 / 3)
    assert result["macro_f1"] == pytest.approx(2 / 3)
    assert result["confusion_matrix"] == {"support": {"support": 1, "contradict": 1},
                                          "contradict": {"support": 0, "contradict": 1}}


def test_classification_empty_invalid_and_length_mismatch():
    with pytest.raises(ValueError, match="at least one"):
        classification_metrics([], [])
    with pytest.raises(ValueError, match="invalid labels"):
        classification_metrics(["alien"], ["support"])
    with pytest.raises(ValueError, match="length mismatch"):
        classification_metrics(["support"], [])


def test_macro_f1_class_imbalance_includes_zero_support_classes():
    result = classification_metrics(["support", "support"], ["support", "support"],
                                    labels=["support", "contradict"])
    assert result["accuracy"] == 1
    assert result["macro_f1"] == pytest.approx(0.5)


def test_retrieval_metrics_hand_calculated():
    result = retrieval_metrics({"q1": ["a"], "q2": ["b", "c"]},
                               {"q1": ["x", "a"], "q2": ["c", "z"]}, ks=(1, 2))
    assert result["recall@1"] == pytest.approx(0.25)
    assert result["recall@2"] == pytest.approx(0.75)
    assert result["mrr"] == pytest.approx(0.75)
    assert result["query_count"] == 2


def test_retrieval_invalid_inputs_and_empty_prediction():
    with pytest.raises(ValueError, match="at least one query"):
        retrieval_metrics({}, {})
    with pytest.raises(ValueError, match="at least one relevant"):
        retrieval_metrics({"q": []}, {})
    result = retrieval_metrics({"q": ["gold"]}, {})
    assert result["recall@1"] == 0 and result["mrr"] == 0


def test_duplicate_pair_ids_and_invalid_gold_label():
    fixture = json.loads(Path("data/benchmarks/development_fixtures.jsonl").read_text().splitlines()[0])
    a = BenchmarkPair.model_validate(fixture)
    with pytest.raises(ValueError, match="duplicate pair_id"):
        validate_pairs([a, a])
    fixture["gold_label"] = "maybe"
    with pytest.raises(ValueError, match="invalid SCOPE gold_label"):
        validate_pairs([BenchmarkPair.model_validate(fixture)])


def test_cli_serializes_all_required_artifacts(tmp_path):
    root = Path.cwd()
    pred = tmp_path / "pred.csv"
    with pred.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["pair_id", "predicted_label"])
        writer.writeheader(); writer.writerow({"pair_id": "syn-001", "predicted_label": "support"})
    out = tmp_path / "results"
    proc = subprocess.run([sys.executable, "scripts/run_evaluation.py", "--benchmark",
                           "data/benchmarks/development_fixtures.jsonl", "--predictions", str(pred),
                           "--output-dir", str(out), "--dataset-version", "synthetic-v1",
                           "--algorithm-version", "toy", "--experiment-id", "serialization"],
                          cwd=root, text=True, capture_output=True,
                          env={**os.environ, "PYTHONPATH": str(root / "src")})
    assert proc.returncode == 2  # Deliberately requires a prediction for every fixture pair.
    pred.write_text("pair_id,predicted_label\n" + "".join(f"syn-{i:03d},support\n" for i in range(1, 7)))
    proc = subprocess.run([sys.executable, "scripts/run_evaluation.py", "--benchmark",
                           "data/benchmarks/development_fixtures.jsonl", "--predictions", str(pred),
                           "--output-dir", str(out), "--dataset-version", "synthetic-v1",
                           "--algorithm-version", "toy", "--experiment-id", "serialization"],
                          cwd=root, text=True, capture_output=True,
                          env={**os.environ, "PYTHONPATH": str(root / "src")})
    assert proc.returncode == 0, proc.stderr
    assert {p.name for p in out.iterdir()} == {"predictions.csv", "metrics.json", "confusion_matrix.csv",
                                               "error_analysis.csv", "experiment_metadata.json"}
    assert json.loads((out / "metrics.json").read_text())["sample_count"] == 6
