# Prior-art comparison

This comparison is a research note for student review. The proposed SCOPE design is not yet implemented or evaluated, so similarity judgments and possible contributions below are provisional.

## Closest publications

| Publication | What it already solves | What it does not establish | Similarity to proposed SCOPE | Question that could remain |
|---|---|---|---|---|
| SciFact (Wadden et al., 2020) [R02] | Scientific claim retrieval, evidence rationales, and support/refute labels on a curated expert-annotated benchmark. | Does not test every dimension in the current SCOPE contract, a multi-user workspace, or the proposed `qualify`/`scope_mismatch` distinction as a validated taxonomy. | High: same central scientific claim-to-literature evidence task. | Does explicit, reviewer-visible dimension-wise scope comparison improve relation labeling over SciFact-style stance and rationale baselines? |
| SciFact-Open (Wadden et al., 2022) [R03] | Open-corpus scientific retrieval/verification at 500K abstracts; reports retrieval generalization difficulty and special-case evidence. | Pooling does not guarantee exhaustive evidence; it does not settle a general dimension-wise comparison interface or all full-text/table issues. | Very high: same use case and directly relevant to broad claims versus narrow evidence. | Can a scope schema reliably identify and explain the special-case/generalization mismatch, with human adjudication? |
| MultiVerS (Wadden et al., 2022) [R04] | Full-document context, document labels, rationale selection, weak supervision, cross-dataset scientific evaluation. | Its reported relation framing is support/refute plus evidence rationale; it does not establish that adding explicit SCOPE fields is beneficial. | Very high: both align scientific claims against papers and return evidence. | Any claimed SCOPE gain needs a direct comparison or careful explanation of why a typed scope review layer serves a distinct user/research question. |
| Evidence Inference 2.0 (DeYoung et al., 2020) [R07] | Structured treatment/comparator/outcome comparisons from clinical trial articles with supporting evidence. | Domain/task-specific clinical comparison does not cover general scientific datasets, methods, metrics, or the complete SCOPE workflow. | High in structured study-scope reasoning, narrower in domain and task. | Can a general schema reuse intervention/outcome ideas while supporting non-clinical claims, and where does it fail? |
| ARSJoint (Zhang et al., 2021) [R06] | Joint abstract retrieval, rationale selection, and stance prediction. | It does not test SCOPE's explicit dimension-by-dimension output or broader scope labels. | High on pipeline architecture; proposed SCOPE may overlap substantially in the core verification workflow. | If SCOPE remains a pipeline of retrieval, evidence selection, and stance, those portions are standard. A distinct contribution must be empirically tied to scope modeling and transparency. |

## Standard components versus potential contribution

| Proposed SCOPE element | Prior-art status | Research implication |
|---|---|---|
| BM25/dense/TF-IDF candidate retrieval | Established IR methods [R11, R12]. | Use as baseline and report retrieval recall. Do not claim retrieval novelty. |
| Scientific claim verification and evidence rationales | Directly established in SciFact and MultiVerS [R02, R04]. | Evaluate against close baselines; show a specific scope-aware improvement or user value. |
| Atomic claim extraction | Scientific claim generation and atomic claim formation have been studied [R05]. | Preserve quantifiers and conditions; don't claim first atomization method. |
| NLI or factual alignment classification | Established in NLI and factual consistency work [R13–R19]. | Compare general alignment/NLI to explicit structured dimensions. |
| Domain-specific scientific language model | SciBERT is established [R20]. | Optional encoder choice, not a contribution by itself. |
| Citation context and paper similarity | Citation intent/recommendation and aspect similarity are established [R23–R25, R29]. | Similarity, citation function, and evidential support are different targets. |
| Scope dimensions in existing software contract | The current SCOPE contract proposes typed scope values/statuses and comparison dimensions ([contracts](../../src/scopecheck/contracts.py)). | The schema is a project design; its validity, completeness, and benefit are untested. |
| Researcher-facing local workflow | Repository foundation defines a local-first prototype goal ([foundation](../architecture/FOUNDATION.md)). | Could be an engineering contribution if implemented and evaluated; currently not implemented. |

## Provisional contribution statement for investigation

The project could investigate whether a transparent set of typed scope comparisons (entity, population, dataset, methodology, outcome/metric, numerical result, relation direction, experimental condition, certainty, and generalization) helps identify when retrieved scientific evidence supports only a narrower claim than the draft asserts. This is a candidate research question, not an established novelty claim or result. The work should be described as a prototype unless a clear benchmark, annotation study, or user evaluation supports a stronger claim.

## Minimum comparison before a novelty claim

Students should read full texts and check methods, labels, datasets, evaluation splits, and limitations for R02–R07, R11–R12, and R16–R19. They should then update this table against the actual implemented method. If their comparator is ordinary retrieval plus NLI/rationale classification, state that these are standard techniques and describe SCOPE as an integration prototype. If no measurable difference remains after comparison, say so explicitly.
