# Claim–evidence alignment algorithm

## Status and purpose

This document describes the deterministic development comparator in
`scopecheck.alignment`. It is a researcher review aid. It does not establish
scientific truth, and the heuristic confidence field is not a calibrated
probability. The synthetic tests are development fixtures, not a benchmark.
No novelty claim is made; this implementation has not been preceded by a
systematic literature review.

## Problem formulation

Given an atomic claim `c` and a retrieved passage `e`, return one of the shared
relations `support`, `contradict`, `qualify`, `scope_mismatch`,
`insufficient_evidence`, or `unrelated`, with dimension-level comparisons and
an exact quotation from the retrieved passage. Textual similarity alone does
not establish that two scientific statements refer to the same population,
dataset, method, outcome, metric, time period, domain, conditions, or level of
certainty.

The implementation uses the existing `AtomicClaim`, `RetrievalHit`,
`ScientificScope`, `DimensionComparison`, and `ComparisonResult` contracts.
Unknown scope remains `ScopeValue(status="unknown")`. Because the shared result
contract has no numeric score field, the numeric scope score is exposed through
the explanation and `weighted_scope_score` helper; the contract's
`scope_compatibility` field remains categorical.

## Evidence structuring and comparison dimensions

`extract_evidence_scope` is an isolated adapter. It first validates
`hit.chunk.metadata["scope"]` as a `ScientificScope` or serialized mapping. If
that is absent or invalid, local regular-expression rules extract only a small
set of explicit cues. `extract_claim_scope` uses explicit claim fields first
and fills only unknown fields from the claim text. No Agent 2 implementation,
remote service, or credential is required.

The rules compare population, dataset, methodology, intervention, outcome,
metric, time period, domain, conditions, certainty, direction, and numeric
values. The shared contract groups some of these under the available enum
members: outcome and metric share `OUTCOME_METRIC_COMPATIBILITY`; time period,
domain, and conditions share `EXPERIMENTAL_CONDITION_COMPATIBILITY`; and
intervention uses `SEMANTIC_AGREEMENT`. Each comparison explanation names the
underlying field. Status is `compatible`, `incompatible`, `partially_compatible`,
or `unknown`. Text overlap can yield partial compatibility for string values.
Unknown pairs are never interpreted as agreement.

## Score and weight selection

For the set `K` of paired, known dimensions, the implementation computes

\[
S_{scope} = \frac{\sum_{i\in K} w_i s_i}{\sum_{i\in K} w_i},
\qquad s_i=\begin{cases}1 & compatible\\0.5 & partially\ compatible\\0 & incompatible.\end{cases}
\]

Unknown dimensions are excluded from both sums. If no dimension is known, the
score is unavailable (`None`) and categorical compatibility is `unknown`.
Default weights are explicit heuristic priorities: population, outcome/metric,
direction, and numbers receive weight 1.5; entity/intervention receives 1.25;
dataset, method, and experimental conditions receive 1.0; certainty receives
0.75. The scope-aware calculation uses scientific scope comparisons; lexical
agreement is used for relevance but is not scored as scope agreement. A claim-type multiplier increases number weight for quantitative
claims, direction weight for comparative claims, methodology weight for causal
claims, and population/certainty weights for generalization claims.

These values were selected as transparent starting assumptions, not learned
from annotations or optimized on data. They are configurable through
`ComparatorConfig(weights=...)`; a future evaluation should pre-register or
train weight selection on a development set and assess it on held-out annotated
data. Multiple fields map to one contract enum and therefore use that enum's
weight for each known field pair.

The categorical score mapping is `compatible` at 0.85 or above,
`incompatible` at 0.15 or below, `partially_compatible` between those cutoffs,
and `unknown` when unavailable. This aggregate is descriptive. Classification
also considers explicit material incompatibilities directly so a low average
does not manufacture a contradiction.

## Factual alignment and classification policy

Local factual rules inspect lexical relevance, negation around directional
verbs, increase/decrease or improvement/reduction direction, matching numeric
values and units, conditional wording, universal quantifiers, causal versus
correlational language, and uncertainty markers. Numeric equality uses a 1%
relative tolerance when units match. Numbers with different or missing units
remain incomparable. This is a narrow parser, not general natural-language
inference.

Decision order:

1. If there is no substantive content-word overlap, return `unrelated`.
2. If a material known scope dimension conflicts (population, dataset,
   method, outcome/metric, or experimental conditions), return
   `scope_mismatch`. This result does not assert that the propositions are
   false or contradictory.
3. If directions oppose or comparable extracted numeric values disagree,
   and no material scope conflict is known, return `contradict` with a
   researcher-check action. Missing scope by itself does not prove a conflict.
4. If the passage is conditional, uncertain, narrower than a universal claim,
   or correlational where the claim is causal, return `qualify` when it is
   directionally consistent.
5. Matching outcome direction or matching numeric values can return
   `support`; otherwise, a relevant passage returns `insufficient_evidence`.

The comparator intentionally uses `scope_mismatch` when opposite directions
occur under explicitly different conditions. Contradiction is reserved for
opposite factual claims without an identified material scope conflict.
Recommendations direct the researcher to review context, narrow a claim,
search for evidence, or inspect apparently contradictory evidence.

`ComparisonResult.evidence_quote` is the complete `hit.chunk.text` value. This
preserves a verbatim substring and avoids synthesized quotations. Document,
page, and offset provenance remain on the input `EvidenceChunk`; the current
result contract does not carry those provenance fields forward.

## Text-only baseline

Use `ComparatorConfig(mode=ComparatorMode.TEXT_ONLY)` to select the stable
text-only baseline. It uses the same conservative relevance, direction,
negation, number, and qualification cues, but does not extract or compare
structured scope fields and reports categorical scope compatibility as
unknown. This keeps the baseline independently selectable without making it
artificially weaker. The default `scope_aware` mode adds explicit dimension
comparisons and uses material mismatches to prevent unsupported direct
comparisons. Both modes share the underlying lexical rules, so the ablation
isolates structured scope comparison rather than unrelated implementation
differences.

```python
from scopecheck.alignment import ComparatorConfig, ComparatorMode
from scopecheck.alignment import compare_claim_to_hit_with_config

baseline = compare_claim_to_hit_with_config(
    claim, hit, ComparatorConfig(mode=ComparatorMode.TEXT_ONLY)
)
scope_aware = compare_claim_to_hit_with_config(
    claim, hit, ComparatorConfig(mode=ComparatorMode.SCOPE_AWARE)
)
```

## Pseudocode

```text
compare(claim, hit, config):
    if scope-aware:
        evidence_scope = validated_metadata_scope(hit) or local_extract(hit.text)
        claim_scope = explicit_claim_scope_with_text_fallback(claim)
        dimensions = compare_each_known_field(claim_scope, evidence_scope)
        score = weighted_mean(known dimensions only)
    else:
        dimensions = unknown baseline observations
        score = unavailable

    facts = detect relevance, negation, direction, numbers/units,
            conditions, quantifiers, causality/correlation, certainty
    if unrelated: relation = unrelated
    else if material_scope_conflict: relation = scope_mismatch
    else if opposite_direction_or_number_conflict: relation = contradict
    else if narrower_or_weaker_consistent_evidence: relation = qualify
    else if direction_or_number_agrees: relation = support
    else: relation = insufficient_evidence

    return shared ComparisonResult with exact retrieved passage as quote
```

## Example structured predictions

The following are examples from deterministic synthetic fixtures, not
benchmark predictions. For brevity, dimension arrays are summarized; the
returned objects contain individual field explanations.

```json
[
  {
    "claim_id": "claim-1",
    "evidence_chunk_id": "evidence-1",
    "relation": "support",
    "confidence": 0.90,
    "scope_compatibility": "compatible",
    "dimension_comparisons": [
      {"dimension": "outcome_metric_compatibility", "status": "compatible", "explanation": "Outcome: claim=mortality; evidence=mortality."},
      {"dimension": "outcome_metric_compatibility", "status": "compatible", "explanation": "Metric: claim=mortality; evidence=mortality."},
      {"dimension": "relation_direction_agreement", "status": "compatible", "explanation": "Direction: claim=negative; evidence=negative."}
    ],
    "explanation": "Same direction; score=1.000 over known weighted dimensions. The label is heuristic, not calibrated.",
    "evidence_quote": "Drug A reduced mortality in the trial.",
    "recommended_action": "no_automated_recommendation",
    "model_version": "rules/0.1.0:scope_aware"
  },
  {
    "claim_id": "claim-1",
    "evidence_chunk_id": "evidence-1",
    "relation": "scope_mismatch",
    "confidence": 0.82,
    "scope_compatibility": "partially_compatible",
    "dimension_comparisons": [
      {"dimension": "dataset_compatibility", "status": "incompatible", "explanation": "Dataset: claim=ImageNet; evidence=CIFAR-10."},
      {"dimension": "outcome_metric_compatibility", "status": "compatible", "explanation": "Outcome: claim=accuracy; evidence=accuracy."},
      {"dimension": "outcome_metric_compatibility", "status": "compatible", "explanation": "Metric: claim=accuracy; evidence=accuracy."},
      {"dimension": "relation_direction_agreement", "status": "compatible", "explanation": "Direction: claim=positive; evidence=positive."}
    ],
    "explanation": "Material dataset mismatch prevents direct comparison; score=0.818 over known weighted dimensions.",
    "evidence_quote": "Model X improves accuracy on CIFAR-10.",
    "recommended_action": "review_source_context",
    "model_version": "rules/0.1.0:scope_aware"
  },
  {
    "claim_id": "claim-1",
    "evidence_chunk_id": "evidence-1",
    "relation": "contradict",
    "confidence": 0.76,
    "scope_compatibility": "partially_compatible",
    "dimension_comparisons": [
      {"dimension": "population_compatibility", "status": "compatible", "explanation": "Population: claim=adults; evidence=adults."},
      {"dimension": "outcome_metric_compatibility", "status": "compatible", "explanation": "Outcome: claim=mortality; evidence=mortality."},
      {"dimension": "outcome_metric_compatibility", "status": "compatible", "explanation": "Metric: claim=mortality; evidence=mortality."},
      {"dimension": "relation_direction_agreement", "status": "incompatible", "explanation": "Direction: claim=negative; evidence=positive."}
    ],
    "explanation": "Opposite directions with no material scope mismatch; score=0.750 over known weighted dimensions.",
    "evidence_quote": "Drug A increases mortality in adults.",
    "recommended_action": "check_contradictory_evidence",
    "model_version": "rules/0.1.0:scope_aware"
  }
]
```

For readability, these examples include only known comparisons; the returned
objects include the unknown field comparisons as well.

## Complexity

For claim length `n`, passage length `m`, and `d` fixed scope fields, token
extraction and the bounded regex passes are linear in text length for these
patterns, set overlap is expected `O(n + m)`, and dimension comparison is
`O(d)` (here `d=12`). Memory use is `O(n + m + d)` for token sets and outputs.
This excludes retrieval and any upstream parsing.

## Assumptions and failure cases

- Direction verbs map to a coarse positive/negative polarity without knowing
  whether higher values are desirable for a particular metric.
- String scope matching is lexical. Synonyms, nested populations, dataset
  aliases, intervention identity, and methodological equivalence are not
  resolved.
- The local extractor recognizes a limited English pattern set; abstracts,
  tables, multi-sentence claims, complex negation, and coreference can defeat
  it.
- Numeric extraction does not robustly understand confidence intervals,
  denominators, comparator baselines, percentage points versus percent,
  inequality signs, multiple endpoints, or numbers with unmatched units.
- A causal phrase detector can misread cautious or indirect causal language.
- A text overlap threshold can mark unrelated passages as relevant or miss
  paraphrases. No embedding model is included.
- Scope mismatch priority can conceal a contradiction that really applies
  across both scopes; the action is to inspect source context and compare like
  with like.
- `confidence` is a fixed heuristic priority by branch, not a probability,
  ranking calibrated against expert judgments, or evidence quality score.
- Complete passage quotation is exact but can be longer than the specific
  supporting sentence. The shared contract currently has no evidence span
  field for a shorter grounded extract.
- Gemini support was not added. The local implementation avoids API costs,
  credentials, and external model-version uncertainty.

## Experimental hypotheses

These are hypotheses for a future evaluation, not findings:

1. Scope-aware comparison may reduce false contradiction labels when relevant
   passages concern a different population, dataset, method, endpoint, or
   experimental condition.
2. It may shift some broad-claim/specific-result pairs from support to qualify.
3. The gain may be offset by scope extraction errors and missed paraphrases.
4. A text-only baseline may perform better when structured scope extraction
   is sparse or wrong.

A future study should use adjudicated claim-passage pairs, report per-relation
precision/recall and confusion matrices, stratify by scope availability, and
compare the two modes on the same splits. The synthetic unit tests must not be
reported as research validation.
