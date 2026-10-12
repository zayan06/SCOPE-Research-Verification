# Benchmark datasets

## A. Development fixtures

`development_fixtures.jsonl` contains six **synthetic test fixtures**, one for
each SCOPE relation. All claims and passages are fabricated. The file exercises
numerical agreement, negation/direction, population scope, dataset and
methodology differences, unmeasured outcomes, and unrelated topics. It is for
development and metric verification only; it is not research data and must not
be used to claim model performance.

The shared record schema is `pair_id`, `claim`, `evidence`,
`source_document_id`, `source_location`, `gold_label`, `label_source`,
`annotation_status`, `annotator`, `notes`, `split`, `dataset_category`, and
`original_label`. Synthetic labels, original dataset labels, automatically
mapped labels, and human-reviewed SCOPE labels must remain identifiable in
`label_source` and `annotation_status`. Human-reviewed labels require annotator
identity. Preserve the original label in `original_label` if an explicitly
documented mapping is applied.

## B. Candidate scientific data

No external dataset has been downloaded into this repository. The sources below
were checked on 2026-10-12; availability describes the publisher's release,
not local acquisition.

| Dataset | Availability and source | License/provenance | Original label meaning | Fit for SCOPE |
| --- | --- | --- | --- | --- |
| SciFact | Download script and corpus/claim JSONL are published by [AllenAI](https://github.com/allenai/scifact); expert-written scientific claims and rationale annotations. | Official repository currently says claims and evidence annotations are CC BY 4.0, corpus abstracts are from S2ORC under ODC-By 1.0, and code is Apache-2.0. Observe both data licenses and source attribution. | Evidence rationales labeled SUPPORT or CONTRADICT; claims with no evidence are NOT ENOUGH INFO in the verification task. | Covers polarity and missing evidence only partially. No native qualification, scope-mismatch, or unrelated class; document-level NOT ENOUGH INFO is not automatically “unrelated” or “insufficient evidence” for a supplied pair. |
| SciFact-Open | Data download script and schemas are published by the [project repository](https://github.com/dwadden/scifact-open); claims, a 500K-abstract S2ORC corpus, and candidate corpus are described. | The repository exposes the data release but the inspected top-level file inventory does not state a dataset license. Confirm the applicable license with the maintainers and source-data terms before downloading or redistributing. Preserve `citation` versus `pooling` provenance. | SUPPORT/CONTRADICT rationales. Citation highlights are expert-annotated; pooled evidence highlights are model predictions and can be wrong. | Broader retrieval setting; still does not provide SCOPE’s six pair-level classes. Pooled highlights are not gold quotes. |

Primary dataset references:

- SciFact schema and original release: [AllenAI data documentation](https://github.com/allenai/scifact/blob/master/doc/data.md), [license](https://github.com/allenai/scifact/blob/master/LICENSE.md), and [paper](https://aclanthology.org/2020.emnlp-main.609/).
- SciFact-Open schema and data provenance: [data documentation](https://github.com/dwadden/scifact-open/blob/main/doc/data.md), [release repository](https://github.com/dwadden/scifact-open), and [paper](https://aclanthology.org/2022.findings-emnlp.347/).

### Mapping policy and annotation protocol

Do not map SciFact document-verdict labels directly to pair-level SCOPE labels.
In particular, NOT ENOUGH INFO does not distinguish an irrelevant passage from
a relevant passage that omits a required outcome, population, or method; a
positive verdict can still be qualified by a narrower study scope. Preserve the
source task label under `original_label` and set `label_source=original_dataset`
if using those labels for a separately reported three-way verdict task. Never
convert it to one of the six SCOPE classes automatically.

For an eventual SCOPE re-annotation, two independent annotators should inspect
the full claim and exact source passage with document/page/offset provenance,
record known and unknown population, dataset, methodology, outcome, metric,
conditions, certainty, direction, and numerical scope, then assign one relation
with a short rationale. Adjudicate disagreements with a third reviewer. Use
`human_reviewed` only after adjudication and retain annotator/adjudicator IDs.
If evidence does not establish the distinction, mark the pair unresolved and
exclude it from six-way scoring rather than inventing a gold label. Freeze
annotation guidance before a held-out split is labeled. Group splits by source
document and deduplicate exact/near duplicate claims and documents across splits.

Do not redistribute source abstracts until licensing/attribution obligations
are satisfied. Store dataset version/release date, source URL, file checksums,
download date, and any transformation script alongside each acquired copy.
