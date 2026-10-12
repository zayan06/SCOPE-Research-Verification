# Proposed research design: scope-aware claim–evidence alignment

## Status and purpose

This is a proposed design for student review. It is not an implemented method or a validated result. The repository currently has typed contracts and interface stubs; the core parser, claim extractor, retriever, comparator, evaluation, and end-to-end pipeline are not implemented ([architecture foundation](../architecture/FOUNDATION.md); [handoff](../handoffs/architecture-foundation.md)). SCOPE is researcher decision support and must not be described as determining objective scientific truth.

The closest established work includes SciFact, SciFact-Open, and MultiVerS, which already combine scientific claim verification with retrieved evidence, rationale selection, and document context [R02–R04]. Evidence Inference structures clinical comparisons around interventions, comparators, outcomes, and cited evidence [R07]. The research question here is narrower: whether making multiple scope comparisons explicit improves a reviewer's ability to distinguish support, contradiction, qualification, scope mismatch, insufficient evidence, and irrelevance.

## Research questions and hypotheses

### Candidate research questions

- **RQ1:** On a held-out set of scientific claim–evidence pairs, how does explicit scope modeling affect relation classification compared with retrieval plus a general NLI/alignment baseline?
- **RQ2:** Does scope-aware comparison reduce false contradiction labels when claim and evidence differ in dataset, population, method, or experimental condition?
- **RQ3:** Which dimensions (population, dataset, method, outcome/metric, numerical result, direction, condition, certainty/generalization) account for the largest change in classification quality?
- **RQ4:** How does retrieval quality, measured independently, affect downstream scope-aware alignment?
- **RQ5:** At what evidence/scope uncertainty should the comparator abstain, and what is the resulting risk–coverage trade-off compared with always assigning a relation?

### Hypotheses to test (not findings)

- **H1:** Adding explicit scope comparisons will improve macro-F1 or reduce a pre-registered false-contradiction error rate over a text-only NLI/alignment baseline on a scope-annotated test set.
- **H2:** A scope-dimension ablation will show that at least one dimension changes errors involving mismatched study context or overgeneralization.
- **H3:** Higher evidence recall at fixed top-*k* will improve downstream classification only when retrieved passages contain enough information to adjudicate the claim; retrieval relevance alone will not guarantee better alignment.
- **H4:** A selective comparator can lower error among answered pairs by abstaining on some uncertain cases; the trade-off must be reported as risk against coverage, not as accuracy alone.

Reject, revise, or narrow these hypotheses based on sample size and annotation agreement. Do not report them as findings before running the planned analysis.

## Operational units and labels

1. **Draft claim:** A sentence or clause split into atomic propositions while retaining quantifiers, population, condition, comparator, outcome, metric, direction, and certainty. If extraction changes meaning, a reviewer corrects it or marks it unusable.
2. **Evidence unit:** A traceable sentence or passage from a selected paper, retaining document ID, section, page, exact quote, and character offsets when available.
3. **Scope representation:** Claim and evidence values for the contract dimensions: population, dataset, methodology, intervention, outcome, metric, time period, domain, conditions, certainty, direction, and numerical values. Each value is either known or explicitly unknown.
4. **Dimension comparison:** `compatible`, `incompatible`, `partially_compatible`, or `unknown`, with a short explanation and source span where possible.
5. **Relation labels:** Use the current contract's `support`, `contradict`, `qualify`, `scope_mismatch`, `insufficient_evidence`, and `unrelated` labels as provisional annotation categories. Write guidelines that distinguish them before collecting labels:
   - **support:** evidence supports the proposition at the claim's asserted scope, subject to stated uncertainty;
   - **contradict:** evidence directly conflicts with the proposition under sufficiently compatible scope;
   - **qualify:** evidence supports a narrower or conditional version, or limits the degree/certainty of a broader statement;
   - **scope_mismatch:** evidence is topically relevant, but a known difference in population, dataset, method, outcome, or condition prevents a direct comparison;
   - **insufficient_evidence:** the passage does not establish either support or contradiction, including unresolved/missing key evidence;
   - **unrelated:** the passage does not materially address the atomic claim.

These definitions overlap in hard cases, especially `qualify`, `scope_mismatch`, and `insufficient_evidence`. Proposed precedence: mark `unrelated` only if the passage does not address the proposition; mark `insufficient_evidence` when relevance exists but evidence is absent/ambiguous or a decisive field is unknown; mark `scope_mismatch` only when a known incompatibility blocks inference; mark `qualify` when evidence supports a narrower/conditional proposition; use `contradict` only when compatible scope and relation direction directly conflict; use `support` only when the stated scope is covered. This is a draft rule requiring expert review. The annotation guide must add examples and precedence rules, and students should report agreement and adjudication. Do not treat unknown scope as compatible by default.

## Proposed system outline

```text
Input: draft D, selected documents P, retrieval cutoff k
1. Parse P into evidence units E with exact source spans and document metadata.
2. Extract atomic claims C from D; preserve original text and offsets.
3. For each claim c in C:
   a. Retrieve candidate evidence Ec from P using a documented local retriever.
   b. For each evidence e in Ec:
      i. Extract/annotate claim scope sc and evidence scope se.
     ii. For every dimension j, compare sc[j] with se[j].
         If either value is unknown, emit unknown (unless a human supplies it).
    iii. Analyze proposition, polarity, relation, numbers, and certainty.
     iv. Assign a provisional relation and calibrated uncertainty using
         semantic evidence plus the dimension comparisons.
      v. Store a traceable quote, source span, model/version, and explanation.
   c. Present results for human review; allow correction, abstention, and
      additional evidence search.
4. Return claim-level results; do not infer whole-literature consensus or truth.
```

## Mathematical sketch

Let `c` be an atomic claim, `e` an evidence passage, and `J` the set of scope dimensions. Let `s_cj` and `s_ej` be values for dimension `j`, each either known or unknown. Define a comparison function:

\[
q_j(c,e) = \begin{cases}
\text{unknown}, & s_{cj} \text{ or } s_{ej} \text{ is unknown},\\
\text{compatible / incompatible / partial}, & \text{according to a documented comparator.}
\end{cases}
\]

The proposed relation predictor is a function of proposition-level evidence and the explicit comparison vector:

\[
\hat{y}_{c,e} = f_\theta\left(c,e,\{q_j(c,e)\}_{j\in J}\right), \quad
\hat{p}_{c,e}(y) = \operatorname{Calibrate}(f_\theta).
\]

Here `y` is one of the six provisional relation labels above. A simple baseline may use a text-only NLI/alignment model; a scope ablation supplies only selected dimensions. Do not collapse `unknown` into a positive compatibility score. If a scalar diagnostic is desired, define it only over observed dimensions and report coverage separately:

\[
S_{obs} = \frac{\sum_{j\in J_{obs}} w_j m_j}{\sum_{j\in J_{obs}} w_j}, \qquad
Coverage = \frac{|J_{obs}|}{|J|}.
\]

`m_j` is an explicitly documented numeric mapping for a known comparison status and `w_j` is a predeclared weight. This score is optional, not a scientific effect estimate, and must not replace the categorical relation or evidence display. When no dimensions are observed, `S_obs` is undefined.

## Evaluation plan

### Datasets and annotation

- **SciFact:** Use the public claim/evidence benchmark for a direct scientific-verification comparison, observing its abstract-centered scope and label design [R02].
- **SciFact-Open:** Use for open-corpus retrieval and evidence-pooling limitations; do not interpret pooled evidence as exhaustive [R03].
- **Evidence Inference 2.0:** Use as a clinical, outcome-conditioned complement if licensing and data access permit; do not directly merge its labels with SCOPE labels [R07].
- **Small SCOPE annotation set:** Create a student-supervised, domain-bounded set of claim/evidence pairs with scope fields and relation labels. Report sampling, inclusion criteria, annotator qualifications, annotation instructions, adjudication, and agreement. Avoid claims about broad scientific validity from a small pilot.

Split by source document (and preferably claim family) to prevent text from the same paper appearing in train and test. Freeze corpus versions and retrieval candidates. Ensure train/development/test access rules are followed.

### Baselines

1. **Lexical retrieval:** TF-IDF or BM25 [R12], reporting recall at fixed *k*.
2. **Dense retrieval:** DPR or a scientific-text encoder if compute and model availability permit [R11, R20]. This is optional; no external credential should be required.
3. **Text relation baseline:** NLI or a factual-alignment score such as SummaC/AlignScore, adapted only where input formats permit [R18, R19].
4. **Scientific verifier baseline:** SciFact baseline or MultiVerS where reproduction, data use, and compute are feasible [R02, R04]. Report what was reproduced versus taken from published results; do not compare numbers from different splits as if controlled.
5. **Scope-aware variant:** Same retrieval candidates and relation backbone with explicit scope values/comparisons appended or used as features. This isolates the proposed change.

### Metrics

- Relation classification: per-class precision/recall/F1, macro-F1, confusion matrix, and accuracy as a secondary measure.
- Retrieval: evidence Recall@k / Success@k and, when ranked gold evidence is available, MRR or nDCG.
- Evidence traceability: rationale span precision/recall/F1 or exact evidence-document recall, matching the dataset annotation form.
- Scope extraction/comparison: per-dimension accuracy or macro-F1 on known values; unknown detection/coverage reported separately.
- Uncertainty: Brier score or expected calibration error with calibration procedure and data split reported; abstention coverage-risk curve if implemented.
- Annotation reliability: Cohen's kappa for two annotators or Krippendorff's alpha for suitable multi-annotator/missing-data settings, plus adjudication counts.
- Error-focused endpoint: predefine false contradiction rate on cases where relevant evidence differs in scope or supports only a subcase.

Report sample counts and confidence intervals where feasible. Do not invent scores or state a benefit unless observed on a controlled test split.

### Ablations and error analysis

- Remove scope dimensions one at a time and by groups: population/dataset; method/conditions; outcome/metric/numbers; direction/certainty/generalization.
- Compare text-only relation prediction, text plus extracted scope, and text plus human-corrected scope to separate extraction error from comparison error.
- Vary retrieval cutoff *k* and compare with oracle-gold evidence only as a clearly labeled diagnostic.
- Stratify errors by broad-to-narrow claims, causal versus correlational wording, population shift, dataset shift, metric mismatch, opposite numerical direction, unknown scope, and missing/contradictory context.
- Manually inspect false support, false contradiction, unsupported broad generalization, retrieval miss, parser/table error, and overconfident abstention examples.

## Threats to validity and implementation challenges

- **Construct validity:** “support,” “qualify,” “scope mismatch,” and “insufficient” are not interchangeable and may be hard to annotate consistently.
- **Dataset validity:** SciFact is small and abstract-based; its claims/evidence do not represent every draft, discipline, or outcome type. Evidence Inference is domain-specific. SciFact-Open uses pooling and is not exhaustive.
- **Leakage:** Duplicate claims, citations, or related papers can cross splits; publication dates can leak future evidence into a historical claim.
- **Retrieval confounding:** A comparator cannot decide correctly if relevant evidence is not retrieved. Keep retrieval evaluation separate and hold candidates constant across comparator ablations.
- **Extraction quality:** PDF layouts, tables, units, footnotes, and OCR can corrupt exact numeric comparisons. No table accuracy is currently measured in this repository.
- **Human annotation:** Students may lack domain expertise; adjudication may be needed for populations, methods, and causal language. Preserve disagreements rather than hiding them.
- **Model behavior:** Text similarity, NLI, and language-model scores can be overconfident and sensitive to wording; calibration must be measured on held-out data.
- **Scope schema:** The current contract uses string values and lists, not a normalized ontology of units, thresholds, or sample definitions. Any richer schema requires coordinated contract revision.
- **Generalization:** Results from one discipline or corpus do not imply utility across scientific fields.
- **System status:** Ingestion, extraction, retrieval, comparison, and experiments are not implemented yet. This design must be revised to match actual code and available data.

## Unresolved design decisions

1. Is evidence a sentence, paragraph, table cell, or a linked set of units? How are offsets normalized after PDF parsing?
2. Which fields are extracted automatically, annotated by humans, or left unknown? What is the minimum evidence for a “known” value?
3. How do units, ranges, confidence intervals, sample sizes, and statistical significance compare?
4. What precedence rules separate qualify from scope mismatch and insufficient evidence?
5. Can claims cite a single paper, multiple studies, or contradictory evidence? How are findings aggregated without implying consensus?
6. Which local baseline is affordable and reproducible on the target hardware? Does dense retrieval earn its additional dependency/latency?
7. What probability calibration and abstention threshold are useful for researcher review?
8. How will private multi-user document handling be protected once persistence is implemented?

## Code artifacts required before reporting results

Current interfaces are documented in the repository contract/handoff. Needed artifacts include: parser with source offsets; deterministic claim extraction baseline; BM25/TF-IDF index; comparator with explicit unknown values and dimension-level explanations; pipeline wiring; versioned sample/benchmark manifests; annotation guide and adjudicated labels; evaluation script with fixed splits and metrics; reproducible run configuration; error-analysis outputs. These artifacts are proposals; none should be described as present until merged and verified.


## RQ-to-measurement plan

| Question | Unit and comparison | Primary measures | Interpretation guardrail |
|---|---|---|---|
| RQ1 | Held-out claim–evidence pairs; text-only verifier vs same verifier plus explicit scope fields, fixed retrieved candidates | Macro-F1 across six relations; per-class precision/recall/F1; paired bootstrap confidence interval | Use identical data, candidates, and backbone. A gain on one benchmark does not establish general scientific validity. |
| RQ2 | Pairs with adjudicated known population/dataset/method/condition differences | False-contradiction rate (predicted `contradict` among gold non-contradiction cases), plus precision/recall for `scope_mismatch` and `qualify` | Predefine subgroup and gold labels; report counts and uncertainty. Do not label all different studies as incompatible. |
| RQ3 | Dimension ablations on the same test pairs | Change in macro-F1 and target error rates after removing each dimension; paired confidence intervals | Correlated dimensions and missing data mean single-feature ablations are diagnostic, not causal proof of independent scientific importance. |
| RQ4 | Each claim with a fixed corpus and retrieval cutoff *k* | Evidence Recall@k / Success@k, MRR if ranked gold evidence exists; downstream macro-F1 and evidence-conditioned performance | Report oracle-evidence results separately from end-to-end results. Retrieval quality and comparison quality are distinct. |
| RQ5 | Comparator predictions across confidence/abstention thresholds | Coverage = answered pairs / all eligible pairs; selective risk = error rate among answered pairs; risk–coverage curve and area under curve where sufficiently sampled; abstention precision/recall for gold `insufficient_evidence` | State what “abstain” maps to in the six-label contract. Calibrate on development data, freeze threshold before test, and report class balance. |

Abstention frequency alone is not a quality measure. Report coverage together with selective risk, the gold insufficiency detection measures, and a fixed-threshold confusion matrix. If no calibrated probability exists, use a documented deterministic uncertainty rule and call the resulting curve a threshold analysis, not probability calibration.

## More explicit proposed procedure

```text
Input: draft text D, selected paper set P, retrieval depth k, frozen model/config M
C <- extract_atomic_claims(D); retain original span and reviewer edits
E <- parse(P); retain document, section, page, offsets, and exact text when available
for claim c in C:
    Q <- retrieve(c, E, k)
    for passage e in Q:
        claim_scope <- extract_or_annotate_scope(c)
        evidence_scope <- extract_or_annotate_scope(e)
        for dimension j in schema:
            q[j] <- compare(claim_scope[j], evidence_scope[j])
            if either value is unknown: q[j] <- unknown
        proposition_signal <- compare_entities_predicate_polarity_numbers_and_modality(c, e)
        candidate_relation <- apply_predeclared_precedence(proposition_signal, q)
        uncertainty <- estimate_from_calibrated_model_or_explicit_unknown/ conflict rules
        if uncertainty exceeds development-frozen abstention threshold:
            candidate_relation <- insufficient_evidence
        emit relation, dimension statuses, evidence quote/span, explanation, uncertainty, versions
show result for researcher correction; record edits separately from model output
```

The pseudocode is a proposal. It assumes a claim can be decomposed without losing quantifiers or conditional clauses, a passage can be aligned to the correct document context, and annotation rules can identify known incompatibilities. If these assumptions fail, preserve the result as unknown/insufficient and expose the passage for review.

### Dimension and relation score sketch

Let `z(c,e)` be a proposition-level representation, `q_j(c,e)` a categorical comparison for dimension `j`, and `u_j` indicate whether both values are known. One trainable baseline can concatenate encoded text and one-hot comparison statuses:

\[h = [z(c,e); q_1; \ldots; q_J; u_1; \ldots; u_J], \quad p(y\mid c,e)=\operatorname{softmax}(W h+b).\]

An explicit rule-based comparator is an alternative: compute proposition polarity/direction, then apply the relation precedence rules. Evaluate both only if implementation effort permits; do not call hand-written rules a learned model. A scope coverage diagnostic is `coverage_scope = sum_j u_j / J`; report alongside any aggregate compatibility score so a high score on one known field cannot hide many unknown fields. No universal weights are justified yet, so avoid a weighted “scope score” in the main outcome unless weights are predeclared and sensitivity-tested.

### Alternatives considered

- **Pure retrieval similarity:** cheapest and useful for candidate ranking, but does not establish relation or shared scope; retain as a retrieval baseline.
- **Single NLI/verifier label:** simpler and comparable to prior work, but hides which study conditions were compared; use as the main comparator baseline.
- **Joint retrieval/rationale/verdict model:** established in ARSJoint and MultiVerS; potentially stronger but makes it harder to isolate the value of explicit scope and may exceed prototype compute.
- **Human-entered scope fields:** improves control in a pilot but costs annotation time; compare with automatically extracted and human-corrected fields to separate extraction error from comparison error.
- **LLM-based extraction/comparison:** potentially flexible but adds cost, service variability, privacy concerns, and calibration issues; optional adapter only, never a required local dependency.

## Dataset access and licensing notes

| Dataset | Intended use | Labels/fit | Access and license status to verify before redistribution/use |
|---|---|---|---|
| SciFact (R02) | Primary scientific retrieval/rationale/verdict baseline | Support/refute/no evidence; abstracts; evidence rationales. Requires mapping to six SCOPE labels and scope annotations. | Repository states claim/evidence annotations are CC BY 4.0, abstracts are inherited from S2ORC under ODC-By 1.0, and code is Apache 2.0. Review the [license file](https://github.com/allenai/scifact/blob/master/LICENSE.md); retain separate corpus provenance. |
| SciFact-Open (R03) | Open-corpus retrieval stress test | Pooled evidence; includes special-case evidence; pooled candidates cannot be treated as exhaustive negatives. | Dataset docs identify source/provenance and refer to S2ORC corpus; inspect [data documentation](https://github.com/dwadden/scifact-open/blob/main/doc/data.md) and upstream S2ORC terms before copying or redistribution. License for each component must be confirmed from repository files at download time. |
| Evidence Inference 2.0 (R07) | Complementary outcome-conditioned clinical task | Increase/decrease/no significant difference with ICO prompt; not directly equivalent to SCOPE labels. | Download and documentation are provided by the [project site](https://evidence-inference.ebm-nlp.com/download/); article full-text rights may vary by source/PMC license. Confirm current terms and each article license; do not assume a blanket corpus license from public availability. |

Use benchmark files locally only after recording source URL, release/version/date, checksum, license text, access conditions, and redistribution decision in a manifest. An academic paper being open access does not automatically license its underlying corpus. Avoid bundling publisher full text.
