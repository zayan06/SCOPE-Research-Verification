# Critical synthesis for SCOPE

## Scope and status

This is an evidence-grounded research note, not a finished student literature review. It synthesizes 30 publications whose bibliographic records were checked against publisher or proceedings records (primarily ACL Anthology and NeurIPS; see [the review matrix](review_matrix.csv) and [verified APA references](references_apa.md)). The records establish publication metadata and the summarized task/method claims. A full-text reading and student verification of these analytical interpretations remain necessary before submission.

SCOPE is intended to help a researcher inspect whether retrieved passages align with a draft claim under stated conditions. It does not establish scientific truth or aggregate the whole literature into a clinical or scientific recommendation. The repository foundation is explicit that ingestion, extraction, retrieval, alignment, and evaluation are currently stubs ([repository foundation](../architecture/FOUNDATION.md); [architecture handoff](../handoffs/architecture-foundation.md)).

## Why semantic similarity alone is insufficient

Semantic similarity ranks text that discusses related ideas. It does not by itself test whether the evidence entails the same proposition. The difference is visible in claim structure: “improved accuracy on Dataset X” can be highly similar to “improves accuracy across all datasets,” while failing to entail the universal quantifier. The discrepancy concerns generalization scope, not topic relevance.

The literature already gives several reasons to avoid equating similarity with evidential support:

- Scientific verification benchmarks separate document retrieval, rationale selection, and stance prediction. SciFact formalizes those stages and provides expert-written claims and rationales [R02]. SciFact-Open shows that open-corpus retrieval is harder and includes evidence that supports only a special case of a claim [R03].
- Dense retrieval and citation recommendation optimize candidate relevance/ranking, not whether a retrieved paper supports a claim [R11, R25]. Aspect-based paper similarity shows that even scholarly similarity has facets, but its citation-section proxies are not evidence-verdict labels [R29].
- Scientific claim verification uses full-document context, weak supervision, and rationales in MultiVerS [R04]; joint retrieval/rationale/stance modeling has also been studied [R06]. These works already address context and evidence reasoning. SCOPE must not claim those ideas are absent from prior work.
- Evidence Inference conditions comparative treatment judgments on intervention, comparator, and outcome [R07], while FEVEROUS requires structured table-cell as well as prose evidence for general claims [R26]. Thus outcome conditioning and structured evidence are established research directions, even though their coverage differs from a general-purpose draft reviewer.
- General NLI benchmarks teach entailment, contradiction, and neutral classification [R13, R14], while clinical NLI illustrates the need for domain-specific data [R15]. They do not make scientific population, study design, measurement, or conditional scope explicit in the complete claim-evidence workflow.

An evidence relation therefore needs at least two questions: (1) is this passage about the same entities, outcome, and relation; and (2) does it establish the claim at the claim's stated level of specificity and generalization? A passage can be relevant yet insufficient, or support a narrower claim while qualifying a broader one.

## What existing systems already address

| Dimension or issue | Existing coverage | Remaining question for SCOPE |
|---|---|---|
| Evidence retrieval and rationale attribution | FEVER and SciFact evaluate evidence retrieval/selection alongside labels [R01, R02]; full-paper QA datasets require evidence spans [R09]. | How does retrieval recall affect downstream scope decisions, and can users trace each comparison to a source span? |
| Scientific domain language | SciFact, SciBERT, and MultiVerS directly address scientific text or scientific claim verification [R02, R04, R20]. | Does an inexpensive deterministic baseline work well enough for a local research prototype? |
| Full-document context | MultiVerS uses full-document context; QASPER evaluates questions over full research papers [R04, R09]. | Which document sections and evidence units are necessary for scope comparison, especially tables and methods? |
| Population, treatment, and outcome | Evidence Inference models intervention/comparator/outcome-conditioned clinical comparisons [R07]; PubMedQA includes quantitative research question answering [R08]. | How should a cross-domain schema represent populations, dataset, methodology, metric, and experimental conditions consistently? |
| Special cases and generalization | SciFact-Open explicitly reports evidence supporting only a special case of a claim [R03]. | Can explicit scope fields reduce over-generalization errors relative to relevant scientific baselines? |
| Multi-task reasoning | ARSJoint and MultiVerS jointly model retrieval/rationale/stance tasks [R04, R06]. | What is the smallest explainable pipeline that improves researcher decisions? |
| Tables and numerical evidence | FEVEROUS includes table cells; CORD-19 documented table extraction and matching challenges [R26, R27]. | How reliable is the current parser for scientific numeric tables, units, denominators, and confidence intervals? The repository does not implement this yet. |
| Factual consistency and text alignment | FactCC, QAGS, SummaC, and AlignScore evaluate consistency/alignment in summarization or broad text-pair settings [R16–R19]. | Do these general metrics detect scientific scope mismatch, and do scope-specific features add value? |
| Citation context | Citation-intent and citation-recommendation studies model context and rhetorical role [R23–R25]. | Citation intent or similarity must not be mistaken for evidential support. |
| Missing/uncertain evidence | FEVER and PubMedQA include not-enough-information or maybe labels [R01, R08]; SciFact-Open identifies annotation pooling limits [R03]. | How should SCOPE separate insufficient evidence, unknown scope, and actual mismatch, and how should uncertainty be calibrated? |

## Critical assessment by scope dimension

The literature is uneven rather than empty. Interventions and outcomes receive structured treatment in clinical evidence inference [R07]. Scientific verification work has retrieval, rationale, stance, and full-document models [R02, R04, R06]. General fact checking has benchmarks with structured table evidence [R26]. Claim generation work considers atomization [R05]. Open-domain scientific verification has already surfaced special-case evidence [R03].

The more defensible research question is whether a transparent, explicit, dimension-wise comparison improves classification or researcher review decisions beyond retrieval plus general NLI/alignment, under carefully defined labels and a feasible annotation budget. Relevant dimensions proposed in the project include entities, population, dataset, method, outcome/metric, numerical values, relation direction, experimental conditions, certainty, and generalization. These dimensions should not be treated as independent or complete: one missing population field can make a comparison uninterpretable, and an unknown field must not be counted as a match.

The current shared contract already names the dimensions and distinguishes `compatible`, `incompatible`, `partially_compatible`, and `unknown`; it also distinguishes `support`, `contradict`, `qualify`, `scope_mismatch`, `insufficient_evidence`, and `unrelated` ([contracts](../../src/scopecheck/contracts.py)). Those are proposed software labels, not validated scientific categories. Annotation guidelines and inter-annotator agreement are still required.

## Gaps that remain plausible, not proven

The following are hypotheses for a student project to investigate, not literature-wide facts:

1. A reviewer-facing, typed scope comparison may make reasons for a relation decision easier to inspect than one holistic score. This must be compared with rationale-bearing baselines such as SciFact and MultiVerS [R02, R04].
2. A broader schema spanning populations, datasets, methods, metrics, numerical values, conditions, certainty, and generalization may be useful outside the clinical intervention/outcome setting [R07]. The cost and reliability of extracting these dimensions are unknown.
3. Explicit scope comparisons may reduce false contradiction decisions when studies differ in dataset, population, or experimental condition. This needs a deliberately constructed or expertly annotated evaluation set and adjudication protocol.
4. A local deterministic BM25/TF-IDF baseline may be sufficient to validate the workflow without paid APIs. This is an engineering choice, not a research finding; BM25 is a candidate baseline [R12].
5. Human review may be necessary to decide whether a field is absent, unreported, or not applicable. The current contract encodes unknown values but does not yet provide a validated annotation policy ([contracts](../../src/scopecheck/contracts.py)).

No claim of novelty should be made until the students search more broadly, read full papers, compare to MultiVerS, SciFact-Open, Evidence Inference, and recent claim-verification work, and confirm the exact scope of their implemented method.

## Synthesis conclusion for student drafting

The defensible framing is: semantic and dense retrieval are useful for finding candidate passages, but retrieval relevance alone does not establish claim support; existing scientific verification already combines retrieval, rationale extraction, stance classification, context, and selected scope-related reasoning. SCOPE proposes to test whether exposing a set of scientific scope dimensions helps researchers inspect claim-evidence alignment in a local-first workflow. The project has not yet implemented or evaluated that proposal. Any claimed contribution, performance benefit, or remaining gap must be revised after full-text review, implementation, and experiments.

## Source checking

Publisher records and paper abstracts were checked on 12 October 2026. ACL Anthology entries were used for ACL-family works; NeurIPS proceedings for RAG and AVeriTeC; the NeurIPS Datasets and Benchmarks record and paper for FEVEROUS; and the DOI/publisher record for BM25. The CSV preserves a canonical URL for every item. “Verified” refers to bibliographic identity and publication record, not independent replication or exhaustive full-text appraisal.
