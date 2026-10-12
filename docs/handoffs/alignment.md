# Alignment workstream handoff

## Branch and implementation commit

- Branch: `feat/alignment`
- Implementation commits: `71e7b9561fbcbe07b7a413a6b09c2a35803292f0`
  (algorithm) and `7341fca5ebcbc52d482bc523c7cf0f66ea1fc473` (score/documentation
  refinement).
- Handoff note is committed as a follow-up documentation commit on the same
  branch.

## Changed files

- `src/scopecheck/alignment/__init__.py`
- `src/scopecheck/alignment/comparator.py`
- `src/scopecheck/alignment/factual.py`
- `src/scopecheck/alignment/scope.py`
- `tests/test_alignment.py`
- `docs/methodology/alignment_algorithm.md`
- `docs/handoffs/alignment.md`

Shared contracts, other research modules, and root dependencies were not
changed.

## Implemented behavior and public interfaces

Required entrypoint:

```python
compare_claim_to_hit(claim: AtomicClaim, hit: RetrievalHit) -> ComparisonResult
```

It returns the shared relation enum, field-level dimension comparisons,
categorical scope compatibility, a heuristic confidence value, explanation,
the exact retrieved passage as `evidence_quote`, a researcher action, and a
method version. It uses scope-aware mode by default.

Evaluation switch:

```python
ComparatorConfig(mode=ComparatorMode.TEXT_ONLY)
ComparatorConfig(mode=ComparatorMode.SCOPE_AWARE)
compare_claim_to_hit_with_config(claim, hit, config)
```

The selected mode is included in `model_version` (`rules/0.1.0:text_only` or
`rules/0.1.0:scope_aware`). Configurable weights and claim-type multipliers
are documented in `docs/methodology/alignment_algorithm.md`. The numeric
weighted scope score is included in the result explanation because the shared
`ComparisonResult` contract has only categorical `scope_compatibility`.

`extract_evidence_scope` accepts a `ScientificScope` or serialized scope
mapping from `RetrievalHit.chunk.metadata["scope"]`, then fills fields that
remain unknown with conservative local text extraction. Invalid metadata also
falls back to local extraction. Explicit known values take precedence.
`extract_claim_scope` likewise preserves explicit claim scope and fills only
unknown fields from claim text. No unfinished Agent 2 or remote model code is
required.

Dimension comparisons cover population, dataset, methodology, intervention,
outcome, metric, time period, domain, experimental conditions, certainty,
direction, and numerical values. The shared contract groups several fields
under common enums, and every explanation names its specific field. Unknown
values do not count as agreement or enter the weighted score. A material
population, dataset, methodology, outcome/metric, or condition mismatch yields
`scope_mismatch`, even if textual directions oppose. Direction or comparable
numeric disagreement without such a mismatch can yield `contradict`. Other
supported relations are `support`, `qualify`, `insufficient_evidence`, and
`unrelated`.

## Dependencies

No new dependencies. Runtime uses the existing Pydantic contracts and Python
standard library only. Gemini support was not added; local deterministic
comparison remains available without credentials or network access.

## Tests and actual results

Validated with the bundled Python 3.12.14 runtime:

- `python -m pytest -q tests/test_alignment.py` — 22 synthetic development
  tests passed.
- `python -m pytest -q` — **30 passed**, one existing
  `StarletteDeprecationWarning` concerning `httpx` integration.
- `git diff --check` — passed before the implementation commit.

The test fixtures cover direct support and contradiction, qualified support,
population/dataset/method/outcome/metric mismatches, numerical agreement and
disagreement, negation, universal generalization, causation versus correlation,
insufficient evidence, unrelated text, missing scope, opposite directions
under different conditions, direct contradiction with comparable explicit
population, and text-only baseline selection. These are synthetic software
development fixtures, not research validation or measured model accuracy.

## Known weaknesses

- English regular expressions recognize only narrow lexical forms, and a
  content-word overlap is a crude relevance test.
- Scope strings are compared lexically; aliases, nested populations, synonyms,
  and scientific equivalence are not resolved.
- Polarity rules do not know whether larger values are desirable for an
  endpoint. Negation, conditionals, causal wording, and certainty are not
  full linguistic analyses.
- Numeric parsing does not model confidence intervals, denominator,
  comparator, endpoint, inequalities, or percent versus percentage points.
- Multiple numbers can be paired incorrectly; units must match literally.
- A material scope mismatch may mask a contradiction that applies in both
  scopes, so the output asks for source-context review.
- Confidence is a fixed heuristic branch score, not calibrated probability or
  source-quality rating. Weights are transparent assumptions, not optimized or
  validated parameters.
- The full passage is quoted exactly; the contract cannot currently retain a
  narrower evidence span or provenance fields in `ComparisonResult`.

See the methodology document for the score formula, assumptions, failure
cases, complexity, baseline comparison, and future experimental hypotheses.

## Integration instructions

1. Merge/cherry-pick `feat/alignment` through the integration workstream; this
   workstream did not merge to `main`.
2. Import `compare_claim_to_hit` from `scopecheck.alignment` and pass the
   existing `AtomicClaim` and `RetrievalHit` objects.
3. For evaluation, select `ComparatorMode.TEXT_ONLY` or
   `ComparatorMode.SCOPE_AWARE` with `compare_claim_to_hit_with_config`; record
   `model_version` and do not treat `confidence` as a probability.
4. Upstream extractors may provide structured evidence scope under
   `hit.chunk.metadata["scope"]` using the shared `ScientificScope` shape.
   Preserve unknown status for fields without evidence.
5. Have researchers review all contradiction and scope-mismatch outputs in
   original source context. Do not report synthetic test results as scientific
   performance.
