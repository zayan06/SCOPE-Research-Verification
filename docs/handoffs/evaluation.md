# Evaluation workstream handoff

## Workstream and branch

- Workstream: Agent 5, machine-learning evaluation and experimental research
- Branch: `feat/evaluation`
- Implementation/test commit: `7ac6a16c0e74f3ef802e68878f63b47e1bcd6c5e`

## Files changed

- `src/scopecheck/evaluation/__init__.py`
- `src/scopecheck/evaluation/metrics.py`
- `src/scopecheck/evaluation/schema.py`
- `data/benchmarks/development_fixtures.jsonl`
- `data/benchmarks/README.md`
- `scripts/run_evaluation.py`
- `scripts/run_retrieval_baselines.py`
- `tests/test_evaluation.py`
- `docs/experiments/README.md`
- `docs/handoffs/evaluation.md`

## Implemented behavior and public interfaces

- `classification_metrics(gold, predicted, labels=None)` returns accuracy,
  macro-F1, per-class precision/recall/F1/support, class distribution, and a
  gold-row/prediction-column confusion matrix. Default label order is the six
  canonical `Relation` values. Empty data, length mismatch, duplicate class
  definitions, and invalid labels raise `ValueError`.
- `retrieval_metrics(relevant_ids, ranked_ids, ks=(1, 5, 10))` returns macro
  Recall@K, MRR, and query count. Missing result lists score as misses; a query
  with no relevance judgments is invalid.
- `BenchmarkPair` and `validate_pairs` validate the normalized benchmark
  records and unique pair IDs without changing `scopecheck.contracts`.
- `scripts/run_evaluation.py` scores supplied CSV predictions and emits
  predictions, metrics, confusion matrix, error analysis, and reproducibility
  metadata. It fails clearly on missing/extra/duplicate IDs and invalid labels.
- `scripts/run_retrieval_baselines.py` runs deterministic TF-IDF cosine and
  BM25 (k1=1.5, b=0.75) over caller-supplied documents and relevance judgments.
  It emits ranked predictions, metrics, and metadata.
- Six fabricated fixtures cover all SCOPE relations and numerical, negation,
  population, dataset, methodology, outcome, and unrelated-content cases.
  They are explicitly synthetic development fixtures and are not research
  evaluation data.
- Exact quote accuracy is only computed when exact predictions are supplied;
  confidence calibration is not emitted because no held-out prediction set is
  available to support it.

## Dataset research and acquisition

- SciFact is publicly available from the AllenAI release. Its source labels
  support/contradict evidence rationales and a claim-level not-enough-info
  verdict; they do not define SCOPE's six pair relations. The official release
  currently states claim/evidence annotations use CC BY 4.0 and corpus
  abstracts use S2ORC's ODC-By 1.0.
- SciFact-Open is publicly described with citation and pooled evidence
  provenance. Citation evidence highlights are expert-annotated; pooled
  highlights are predictions. The inspected repository did not expose a clear
  data license, so terms need confirmation before acquisition or redistribution.
- Neither dataset was downloaded in this workstream. The mapping/annotation
  protocol is documented in `data/benchmarks/README.md`. No real labels were
  created or mapped, and no ground truth was invented.

## Experiments and actual results

- Experiments 2–6 were not executed because the alignment implementation and/or
  valid human-reviewed pair judgments are unavailable. Experiment 4 has fixture
  coverage only; that is development testing, not robustness evaluation.
- Experiment 1 has an executable TF-IDF/BM25 baseline runner, but was not run:
  no valid frozen retrieval corpus and gold relevance judgments were supplied.
- No model performance metrics or research results are claimed. Metric outputs
  are verified by hand-calculable unit tests and serialization tests only.

## Dependencies

No dependencies were added. The evaluator and retrieval baselines use the
Python standard library and existing Pydantic contracts.

## Tests

Executed with the bundled Python 3.12 runtime:

```text
python -m pytest -q
16 passed, 1 warning
```

The warning is the pre-existing Starlette deprecation warning about its
`httpx` test-client integration. Evaluation tests cover hand-calculated
accuracy, precision, recall, F1, macro-F1, confusion matrix, Recall@K, MRR,
empty datasets, invalid labels, duplicate IDs, missing predictions, class
imbalance, retrieval misses, artifact serialization, and a deterministic
synthetic TF-IDF/BM25 smoke run.

## Integration instructions and limitations

Keep this evaluator independent from retrieval/alignment modules. Feed
human-reviewed pair-level gold labels and model predictions to
`run_evaluation.py`; do not transform SciFact's three-way task labels into six
SCOPE labels. Use `run_retrieval_baselines.py` only with source-verified
relevance judgments and record tokenizer/cutoff/data version. For scope-aware
experiments, freeze data splits by source document, use the same retrieval
candidates across comparators, and report retrieval performance separately.

Current limits: no real dataset is locally acquired; no SCOPE human-reviewed
pair labels exist; alignment and production retrieval are still stubs in this
worktree; no text-only/scope-aware/ablation/robustness comparison ran. Strong
claims require licensed data, adjudicated six-way labels, source-grouped held-
out splits, functional algorithms, uncertainty analysis, and the threat
controls documented in `docs/experiments/README.md`.
