# Evaluation and experiment protocol

## Evaluation runner

The dependency-free metrics module implements classification accuracy,
macro-F1, per-class precision/recall/F1/support, confusion matrices,
Recall@1/5/10 (or caller-selected K), and MRR. Classification rejects empty
inputs, invalid labels, and length mismatch. Retrieval rejects empty queries,
empty relevance sets, and invalid K values; a missing retrieval result is
scored as a miss. Precision/recall/F1 with a zero denominator are zero.
Confusion-matrix rows are gold classes and columns are predicted classes.

After a real system has produced one prediction per fixture pair, evaluate it
and write all five result artifacts:

```sh
python scripts/run_evaluation.py \
  --benchmark data/benchmarks/development_fixtures.jsonl \
  --predictions /path/to/predictions.csv \
  --output-dir /path/to/run \
  --dataset-version synthetic-fixtures-v1 \
  --algorithm-version <implementation-version> \
  --experiment-id <experiment-id> \
  --config '{"setting":"record exact parameters here"}'
```

Prediction input is CSV with required `pair_id,predicted_label`; optional
columns are `predicted_quote,confidence`. Missing, extra, or duplicate IDs fail
with an actionable error. Outputs: `predictions.csv`, `metrics.json`,
`confusion_matrix.csv`, `error_analysis.csv`, and `experiment_metadata.json`.
Metadata records the input SHA-256, sample/class counts, configuration, seed,
git commit, and UTC execution time. Exact quote accuracy is reported only when
quotes were supplied and exact passage text is present; it is not a semantic
evidence-quality metric. Confidence calibration is intentionally omitted until
there are enough independently labeled predictions and confidence values to
support it.

## Planned experiments and run gates

| Experiment | Comparison and required inputs | Status in this branch |
| --- | --- | --- |
| 1. TF-IDF vs BM25 | Same frozen corpus, queries, relevant document IDs, tokenization, and cutoff; execute both retrievers and report Recall@K/MRR. | Pending: retrieval implementation and real query/relevance data are unavailable. |
| 2. Text-only vs scope-aware | Same claims/evidence, split, candidate set, and classifier budget; only scope features differ. | Pending: alignment implementation and human-reviewed six-way labels unavailable. |
| 3. Scope-dimension ablation | Full model against leave-one-dimension-out variants; record all configuration changes. | Pending for the same missing alignment and annotation inputs. |
| 4. Numerical/negation robustness | Paired examples stratified by numerical and negation phenomena; report per-stratum classification metrics and paired errors. | Synthetic fixture coverage exists; no robust experiment is claimed because there is no implemented classifier. |
| 5. Mismatch error analysis | Human-reviewed errors grouped by population, dataset, methodology, and outcome mismatch. | Pending real labels and predictions. |
| 6. Retrieval sensitivity | Evaluate the same alignment classifier on top-k sets from each retriever / retrieval cutoff; distinguish oracle evidence from retrieved evidence. | Pending retriever and alignment implementations plus judgments. |

Experiment 1 has a standalone deterministic baseline runner. It needs a frozen
JSONL document corpus (`doc_id`, `text`) and JSONL queries (`query_id`, `text`,
`relevant_doc_ids`); the retrieval judgments must be supplied by the dataset,
not generated from model predictions:

```sh
python scripts/run_retrieval_baselines.py \
  --documents /path/to/documents.jsonl \
  --queries /path/to/queries-with-relevance.jsonl \
  --output-dir /path/to/run \
  --dataset-version <version> --k 10
```

It writes `predictions.csv`, `metrics.json`, and `experiment_metadata.json`.
The TF-IDF and BM25 implementations use the same lowercased alphanumeric
tokenizer and deterministic document-ID tie-break; TF-IDF uses cosine similarity
with smoothed IDF, and BM25 uses k1=1.5, b=0.75. This is a research baseline,
not the product retrieval index. Do not claim SciFact performance until actual
licensed corpus and relevance judgments are acquired and the command runs on
those files.

Do not run or report an experiment until its inputs are valid. The `scripts/run_evaluation.py`
runner scores supplied predictions; it does not implement a retrieval or
alignment model. The evaluator itself has no model-specific dependency.

## Reproducibility controls

For every run, retain dataset name/version, source license, dataset checksum,
sample count, class distribution, algorithm/model version, full configuration,
random seed when applicable, source commit, command, environment/dependencies,
and actual metric values. Keep source-document groups and near-duplicate
documents in a single split. Tune only on development data; freeze all choices
before held-out evaluation. Report retrieval failures separately from
alignment failures and do not use oracle evidence as a retrieval result.

## Threats to validity

- **Small samples:** six synthetic cases are metric smoke tests, not a useful
  estimate of generalization; confidence intervals need a much larger held-out
  sample and appropriate resampling by document/claim group.
- **Annotation subjectivity:** qualification, mismatch, and insufficiency can
  overlap. A written rubric, independent annotation, agreement reporting, and
  adjudication are required.
- **Domain imbalance:** SciFact is biomedical; results may not transfer across
  scientific fields, methods, or study types.
- **Label mismatch:** existing datasets do not define SCOPE's six classes.
  Direct label mapping would confound verdict, evidence relevance, and scope.
- **Retrieval errors:** a classifier cannot evaluate absent evidence. Report
  retrieval recall and conditional classification separately.
- **Model stochasticity and prompt sensitivity:** repeat stochastic runs with
  recorded seeds/settings and assess prompt variants before general claims.
- **Overfitting:** synthetic fixtures are visible and tiny; they must not be
  training/evaluation data for research claims. Keep a source-grouped locked
  test split.
- **Dataset leakage:** identify claim-source overlap, duplicated abstracts,
  citation leakage, and model-training contamination where possible.
- **Uncalibrated confidence:** confidence values are not probabilities unless
  calibration is evaluated on adequate held-out labels. No calibration result
  is currently produced.

Strong claims require real licensed data acquisition, human-reviewed pair-level
SCOPE labels, source-grouped train/dev/test partitions, functioning retrieval
and alignment implementations, preregistered comparison settings, repeated
runs where stochastic, uncertainty estimates, and documented error analysis.
