# Academic report outline and readiness guide

This is a structure for student-authored writing. It is not a completed report. Replace prompts with students' own analysis and cite primary sources. The current codebase is a foundation with unimplemented core modules; the report must state that plainly unless later commits and experiments provide evidence.

## 1. Problem statement

**Questions students must answer**

- What decision does SCOPE help a researcher make?
- Why can a semantically relevant passage still fail to support the same claim?
- What is the boundary between evidence alignment and claims about scientific truth?

**Evidence needed:** A carefully sourced motivating example; definitions of claim, evidence unit, relation, and scope; review of SciFact/SciFact-Open and scope-sensitive cases [R02, R03].

**Tables/figures:** One claim-versus-evidence example that marks population, dataset, outcome, and generalization; system boundary diagram.

**Code artifacts:** None required to explain the problem; link repo architecture for implementation status.

**Incomplete:** Confirm the motivating example is illustrative and not presented as a real study finding; write the final statement in student-authored prose.

## 2. Objectives and research questions

**Questions students must answer:** What measurable objective will be tested? Which RQs/hypotheses are in scope? What counts as success or failure?

**Evidence needed:** Operational relation labels, dimensions, primary endpoint, baselines, and planned comparisons from [research_design.md](../methodology/research_design.md).

**Tables/figures:** RQ-to-hypothesis-to-metric table; preregistered decision criteria if the course requires them.

**Code artifacts:** Versioned label definitions and evaluation configuration.

**Incomplete:** Candidate RQs and hypotheses are proposals, not findings. Finalize sample, task, and metrics before evaluation.

## 3. Literature review (target: 25–30 research articles)

**Questions students must answer:** What methods already perform claim retrieval, evidence selection, stance/NLI, document-level reasoning, scope extraction, citation analysis, or factual consistency? What assumptions and datasets limit transfer?

**Evidence needed:** Read and annotate all included full texts. Start with SciFact, SciFact-Open, MultiVerS, Evidence Inference, ARSJoint, FEVER, NLI, factual consistency, citation intent, retrieval, and parsing literature [R01–R30]. The [review matrix](../literature/review_matrix.csv) is an initial verified bibliography, not a substitute for reading.

**Tables/figures:** Literature comparison matrix (can condense the CSV for the report); taxonomy by task, evidence unit, labels, datasets, and scope fields.

**Code artifacts:** `docs/literature/review_matrix.csv`, `critical_synthesis.md`, and `references_apa.md` as research records.

**Incomplete:** The search is not systematic or exhaustive; authors and students must document search strings, date ranges, inclusion/exclusion criteria, full-text reading, and revised selection rationale.

## 4. Limitations of existing systems

**Questions students must answer:** Which limits are explicitly discussed in papers, which follow from task/dataset design, and which remain hypotheses? Which systems already address full context, special-case evidence, outcomes, numerical/table evidence, and uncertainty?

**Evidence needed:** Direct paper passages and results for each limitation; balanced coverage of work that already addresses scope-adjacent problems [R03, R04, R07, R26].

**Tables/figures:** Coverage-by-dimension matrix, with `addressed`, `partial`, `not evaluated`, and `unknown` labels plus citations.

**Code artifacts:** None beyond reproducible dataset/system version notes.

**Incomplete:** Do not write “prior work ignores scope” as a blanket claim. Confirm specific limitations in full text before attributing them to authors.

## 5. Proposed methodology/model

**Questions students must answer:** How are atomic claims formed without losing scope? How are passages retrieved, evidence spans preserved, scope fields represented, dimensions compared, relations assigned, uncertainty surfaced, and people involved in review?

**Evidence needed:** A versioned algorithm and formal definitions, design choices, assumptions, and explicit distinction between existing code and proposed components. See [research design](../methodology/research_design.md).

**Tables/figures:** Pipeline diagram; scope field schema; decision table for relation labels; worked example with unknown values.

**Code artifacts:** Current contracts in `src/scopecheck/contracts.py`; eventual parser, extractor, retrieval index, comparator, and pipeline paths from actual commits.

**Incomplete:** Most computational components are stubs. Update this section to match the code that exists at report freeze; never describe planned pseudocode as implemented.

## 6. Code repository

**Questions students must answer:** Where is the repository? Which commit/branch was evaluated? What runs locally? How can another student reproduce setup and output?

**Evidence needed:** Verified repository URL supplied by project owners (never infer one), setup commands, dependency versions, interface/API docs, run logs, licenses/data access notes, and a precise implementation-status statement.

**Tables/figures:** Module ownership/status table; optional architecture diagram.

**Code artifacts:** README, `pyproject.toml`, API docs, tests, scripts, benchmark manifests, commit hash.

**Incomplete:** No GitHub URL is present in the reviewed workspace. Core functions currently raise `NotImplementedError`; students must confirm the exact branch and commit included in submission.

## 7. Experimental analysis and current progress

**Questions students must answer:** What data and splits were used? Were baselines run under matched conditions? How are retrieval, classification, evidence localization, scope extraction, calibration, and errors measured? What failed?

**Evidence needed:** Dataset versions, counts, label distribution, annotation protocol, run configs/logs, actual metrics with uncertainty, error examples, and code commit. Follow [research_design.md](../methodology/research_design.md).

**Tables/figures:** Results table with baselines and splits; confusion matrix; retrieval recall plot; dimension ablation; representative error analysis.

**Code artifacts:** Evaluation scripts, fixed split manifests, run outputs, model/config versions, human annotation records with privacy safeguards.

**Incomplete:** No SCOPE experiments or metrics are present in the repository foundation. Do not fill in estimated or expected values as results.

## 8. APA-style references

**Questions students must answer:** Does every in-text citation resolve to a verified reference? Are venue, DOI, year, title, author order, and capitalization correct for the source version used?

**Evidence needed:** Publisher or DOI metadata and full-text reading. Start with [references_apa.md](../literature/references_apa.md).

**Tables/figures:** None. Optional appendix: source verification log.

**Code artifacts:** Citation keys in the CSV/reference list; optional bibliography checker.

**Incomplete:** Confirm institutional APA interpretation and full paper versions; this list is a working scaffold.

## 9. Individual contributions and AI disclosure

**Questions students must answer:** Which work did each student personally perform? Which AI/software tools assisted with discovery, code, analysis, or drafting? What did students check, revise, reject, or independently produce?

**Evidence needed:** Git history, task records, notebooks, review notes, and actual tool-use log.

**Tables/figures:** Completed [contribution template](contribution_template.md); updated [AI-assistance log](ai_assistance_log.md).

**Code artifacts:** Commit IDs and attributable artifacts; do not infer contribution from authorship or tool output.

**Incomplete:** Student identities, allocations, dates, and personal contributions must be filled in by students. Follow university disclosure policy and keep final academic writing student-authored.

## Report-readiness checklist

- [x] Initial set of 30 unique publication records with canonical URLs or DOI links, cross-linked to APA-style entries.
- [x] Critical synthesis distinguishes existing coverage from provisional gaps; close prior art is named.
- [x] Proposed methodology, pseudocode, mathematical sketch, hypotheses, datasets, baselines, metrics, ablations, and validity threats are documented as proposals.
- [x] Contribution and AI-disclosure templates are present.
- [ ] Students have read and critically annotated every selected full paper.
- [ ] Search strategy and article inclusion criteria are documented and reviewed by students/supervisor.
- [ ] Annotation definitions and agreement study are completed.
- [ ] Implementation evidence is added for each component claimed as complete.
- [ ] Experiments are executed with reproducible splits/configuration and real results.
- [ ] Error analysis, uncertainty, and limitations are written from observed results.
- [ ] Students complete contribution statements and update the AI-assistance log.
- [ ] References and in-text citation keys are checked against institution requirements.

**Current readiness:** research scaffold ready for student review; implementation and experimental-analysis sections are not evidence-ready.
