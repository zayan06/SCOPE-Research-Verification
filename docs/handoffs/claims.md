# Claims workstream handoff

## Workstream and branch

- Workstream: Agent 2, atomic scientific claim extraction and scope
- Branch: `feat/claims`
- Implementation commit: recorded below after implementation commit

## Functionality implemented

- Deterministic, offline claim extraction with sentence segmentation,
  conservative clause decomposition, recognized assertion cues, claim typing,
  and stable IDs.
- Full `ScientificScope` population using explicit known/unknown `ScopeValue`s;
  preserves modality, polarity, conditions, generalization cues, and recognized
  numeric strings.
- Exact source text and zero-based half-open character offsets for each claim.
- Optional Gemini structured-output adapter with environment credentials,
  Pydantic validation, and verbatim-source verification. No Gemini request was
  made during validation.

## Public interfaces

```python
extract_claims(text: str, document_id: str) -> list[AtomicClaim]
extract_claims_gemini(
    text: str, document_id: str, *, model: str = "gemini-2.5-flash"
) -> list[AtomicClaim]
```

The first interface is exported from `scopecheck.claims`. The Gemini adapter
is imported from `scopecheck.claims.gemini` and is optional at runtime.

## Files modified

- `src/scopecheck/claims/__init__.py`
- `src/scopecheck/claims/extractor.py`
- `src/scopecheck/claims/gemini.py`
- `tests/test_claims.py`
- `docs/methodology/claim_extraction.md`
- `docs/handoffs/claims.md`

Shared contracts and other workstreams' implementation files were not changed.

## Dependencies

Core extraction uses only the existing Python and Pydantic dependencies.
Gemini support optionally requires the `google-genai` package and the
`GOOGLE_API_KEY` environment variable; neither is required for local extraction.
No project dependency declaration was changed.

## Tests and actual results

- `python -m pip install -e '.[dev]'` — succeeded in the prepared worktree.
- `python -m pytest -q tests/test_claims.py` — **15 passed**.
- `python -m pytest -q` — **23 passed, 1 warning**. The warning is the existing
  Starlette deprecation notice about its `httpx` test-client integration.
- `git diff --check` — passed.

Tests cover atomic/compound claims, numeric results, negative polarity,
generalization, dataset and conditional scope, qualification and modality,
causal/correlational/comparative statements, explicit unknown values, empty and
non-claim text, malformed model JSON, and source attribution validation.

## Example

Input:

```text
Model A improves accuracy by 12% on Dataset X, but performs worse than Model B on Dataset Y.
```

Output summary: two claims; the first has dataset `Dataset X`, metric `accuracy`,
and quantity `12%`. The second has dataset `Dataset Y` and comparative type;
its standalone claim text inherits `Model A`, while its exact source span is
the original second clause. Full serialized output and pipeline details are in
`docs/methodology/claim_extraction.md`.

## Limitations

This is an unvalidated English regex baseline. It may miss paraphrases, mishandle
ambiguous negation, miss unfamiliar dataset labels, produce imperfect sentence
boundaries, and fail to resolve references across clauses or sentences. Scope
and numeric extraction are approximate and must be reviewed against the source.
Unit tests establish only the covered software behavior, not scientific
validity. The Gemini adapter's live service call was not exercised.

## Integration instructions

Import `extract_claims` from `scopecheck.claims` or the function's defining
module. It returns the existing canonical `AtomicClaim` contracts and needs no
service credentials. Unknown scope fields remain explicitly unknown. For
model-assisted extraction, install `google-genai`, set `GOOGLE_API_KEY`, and
call the separate Gemini adapter; handle its explicit availability and
validation errors. No shared-contract migration is required.

## Commit hash

Implementation commit: `46261acd57fa90af9b0b7bda55926f6459e80229`
