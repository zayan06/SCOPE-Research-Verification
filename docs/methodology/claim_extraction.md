# Atomic claim extraction and scope representation

## Pipeline

`scopecheck.claims.extractor.extract_claims(text, document_id)` is a local,
deterministic baseline. It trims and segments input into sentences while
retaining character offsets, splits on a small set of clear contrastive or
coordinated assertion boundaries, rejects fragments without a recognized
assertion cue, and constructs each result as the shared `AtomicClaim` model.
IDs are stable SHA-256 prefixes over document ID, source offsets, and source
text. No network call or extra package is needed.

When a split clause begins with a predicate and the preceding clause begins
with a recognizable `Model A`, `Method A`, `System A`, `Algorithm A`,
`Treatment A`, or `Group A` subject, that subject is repeated in `claim.text`
to make the claim readable on its own. The `SourceSpan` still points to the
exact original clause; its half-open offsets are zero-based Python character
offsets into the input. All untouched words, including `only`, `may`, `not`,
`associated with`, and statistical qualifications, remain in the claim text.

## Scope representation

Every field in `ScientificScope` is populated. If a value is not explicitly
recognized in the claim text, it remains `ScopeValue(status="unknown", value=null)`.
The baseline recognizes literal dataset/corpus/benchmark labels; common
population, method/intervention, outcome and metric terms; a small set of time
and domain patterns; conditional and generalization phrases; certainty cues;
direction/polarity; and number strings. `conditions` and `numerical_values`
use the contract's string-list values. Unknown fields are not filled from
outside context.

`claim_type` uses the shared enum. Causal language takes precedence, followed
by correlational language, comparative language, numerical claims,
generalization, and other recognized empirical assertions. This is a
rule-based label, not a causal inference.

## Atomicity criteria

The baseline emits a separate claim when a sentence contains a clear
contrastive boundary (`but`, `whereas`, `although`) or a semicolon. It also
splits a narrow set of coordinated clauses when the next clause has a clear
subject and assertion verb. It does not split every `and`: noun phrases,
uncertain coordination, or dependent clauses can change meaning when split.
When safe splitting is not evident, the full assertion is kept together.

## Uncertainty, polarity, and qualifications

The exact source language remains in `text`; qualifiers are not normalized
away. `certainty` records recognized values such as `possible`, `suggestive`,
`associated`, and `statistically_significant`, joined when multiple cues occur.
`direction` records positive, negative, or association cues. This compact field
cannot fully represent the scope or target of every negation; read it together
with the source text.

## Numerical extraction

Numbers and nearby recognized units, percentages, uncertainty notation, and
ranges are copied as strings into `scope.numerical_values`. The extractor does
not convert units, infer denominators, distinguish relative from absolute
percentages, or determine whether a number is a sample size, estimate, or
threshold. Exact wording in the source remains authoritative.

## Example output

Input: `Method A may improve accuracy by 12% on Dataset X.`

```json
{
  "id": "3bcb369a361d39623c4c",
  "text": "Method A may improve accuracy by 12% on Dataset X.",
  "document_id": "demo-paper",
  "claim_type": "quantitative",
  "scope": {
    "population": {"status": "unknown", "value": null},
    "dataset": {"status": "known", "value": "Dataset X"},
    "methodology": {"status": "known", "value": "Method A"},
    "intervention": {"status": "unknown", "value": null},
    "outcome": {"status": "known", "value": "accuracy"},
    "metric": {"status": "known", "value": "accuracy"},
    "time_period": {"status": "unknown", "value": null},
    "domain": {"status": "unknown", "value": null},
    "conditions": {"status": "unknown", "value": null},
    "certainty": {"status": "known", "value": "possible"},
    "direction": {"status": "known", "value": "positive"},
    "numerical_values": {"status": "known", "value": ["12%"]}
  },
  "source_span": {
    "document_id": "demo-paper",
    "section_id": null,
    "page_number": null,
    "start_offset": 0,
    "end_offset": 50,
    "exact_text": "Method A may improve accuracy by 12% on Dataset X."
  },
  "extraction_method": "rule_based"
}
```

For `Model A improves accuracy by 12% on Dataset X, but performs worse than
Model B on Dataset Y.`, two claims are emitted. Their datasets are respectively
`Dataset X` and `Dataset Y`; the second claim text is made standalone as
`Model A performs worse than Model B on Dataset Y.`, while its exact source span
is `performs worse than Model B on Dataset Y.`

## Optional Gemini adapter

`scopecheck.claims.gemini.extract_claims_gemini` requests JSON structured output
with `text` and verbatim `source_text` per item. It reads `GOOGLE_API_KEY` from
the environment, lazily imports the optional `google-genai` SDK, validates
response shape with Pydantic, confirms every source passage occurs verbatim in
the input, and constructs source offsets locally. Missing SDK/credentials and
malformed or unattributable output raise explicit errors. The adapter has no
required dependency impact on baseline operation. Model-provided scope is not
trusted; known fields are reconstructed using the same deterministic rules.

## Limitations and known failure cases

This baseline is intentionally conservative and has not been scientifically
validated. It uses English cue words and regular expressions, not syntactic or
domain-specific parsing. It can miss paraphrased assertions, misread ambiguous
negation, misclassify words such as `higher` without full context, fail to
resolve pronouns or cross-sentence references, and miss dataset names that do
not follow its literal label pattern. Sentence splitting around abbreviations,
decimal punctuation, and citations can be imperfect. A compound clause without
an explicit repeated subject can remain dependent on nearby source context.
Scope extraction is approximate; passing unit tests demonstrates implemented
behavior only, not scientific validity or extraction quality on literature.

Model-assisted extraction may improve coverage and syntactic decomposition,
but it can omit or invent content. The Gemini adapter therefore validates
structured shape and verbatim source attribution while keeping exact source
passages available for review; it does not validate whether a model's claim
interpretation is scientifically correct.
