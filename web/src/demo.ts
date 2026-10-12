import type { Finding, LibraryDocument, Project, ScientificScope } from "./contracts";

const unknown = () => ({ status: "unknown" as const });
const unknownScope: ScientificScope = {
  population: unknown(), dataset: unknown(), methodology: unknown(), intervention: unknown(),
  outcome: unknown(), metric: unknown(), time_period: unknown(), domain: unknown(),
  conditions: unknown(), certainty: unknown(), direction: unknown(), numerical_values: unknown(),
};
export const demoProjects: Project[] = [
  { id: "proj-1", name: "Sleep and memory — example review", description: "Synthetic draft workspace", updated: "Today, 10:42", documents: 5, drafts: 2, analyses: 4 },
  { id: "proj-2", name: "Example project B", description: "Empty synthetic project workspace", updated: "No activity", documents: 0, drafts: 0, analyses: 0 },
  { id: "proj-3", name: "Example project C", description: "Empty synthetic project workspace", updated: "No activity", documents: 0, drafts: 0, analyses: 0 },
];
export const demoDocuments: LibraryDocument[] = [
  { document_id: "draft-1", filename: "example-sleep-draft.docx", title: "Example draft: sleep and memory", kind: "Draft", authors: null, year: null, uploadedAt: "Oct 12, 2026", status: "ready", claims: 12 },
  { document_id: "paper-1", filename: "example-source-a.pdf", title: "Synthetic review passage A", kind: "Source paper", authors: null, year: null, uploadedAt: "Oct 11, 2026", status: "ready", claims: 0 },
  { document_id: "paper-2", filename: "example-source-b.pdf", title: "Synthetic review passage B", kind: "Source paper", authors: null, year: null, uploadedAt: "Oct 10, 2026", status: "ready", claims: 0 },
  { document_id: "paper-3", filename: "example-source-c.pdf", title: "Synthetic review passage C", kind: "Source paper", authors: null, year: null, uploadedAt: "Oct 9, 2026", status: "processing", claims: 0 },
  { document_id: "draft-2", filename: "example-chapter.docx", title: "Example draft chapter", kind: "Draft", authors: null, year: null, uploadedAt: "Oct 8, 2026", status: "ready", claims: 0 },
];
const baseDimensions = [
  { dimension: "population_compatibility", status: "unknown" as const, explanation: "The draft does not name a population; the passage discusses adult participants." },
  { dimension: "methodological_compatibility", status: "partially_compatible" as const, explanation: "The claim generalizes across studies while the review describes several distinct paradigms." },
  { dimension: "outcome_metric_compatibility", status: "compatible" as const, explanation: "Both refer to later memory performance." },
  { dimension: "certainty_generalization_mismatch", status: "incompatible" as const, explanation: "The draft uses a universal statement; the passage reports effects that vary by task and study." },
];
const evidence1 = "Sleep can enhance the consolidation of newly acquired declarative memories, particularly when sleep occurs soon after learning. The magnitude and direction of effects depend on task characteristics and study design.";
const evidence2 = "The relationship between sleep and memory is not uniform across all forms of learning. Results vary with the type of memory assessed, the timing of sleep, and the methods used to measure retention.";
const claim1 = "Sleep universally improves memory consolidation across all types of learning.";
const claim2 = "Sleep after learning can support consolidation of some declarative memories.";
export const demoFindings: Finding[] = [
  {
    id: "finding-1", claim_id: "claim-1", evidence_chunk_id: "chunk-1", relation: "qualify", confidence: 0.92,
    scope_compatibility: "partially_compatible", dimension_comparisons: baseDimensions,
    explanation: "The source supports a narrower version of the claim. It describes benefits for some declarative memory tasks and notes variation across methods and task types.",
    evidence_quote: evidence1, recommended_action: "consider_narrowing_claim", model_version: "demo-example-v1",
    documentTitle: "Synthetic review passage A", documentAuthors: null, documentYear: null, section: null, page: null,
    review: "unreviewed", note: "", claimText: claim1, sourceText: evidence1,
  },
  {
    id: "finding-2", claim_id: "claim-1", evidence_chunk_id: "chunk-2", relation: "scope_mismatch", confidence: 0.78,
    scope_compatibility: "incompatible", dimension_comparisons: [
      { dimension: "population_compatibility", status: "unknown", explanation: "The draft does not specify a population." },
      { dimension: "outcome_metric_compatibility", status: "partially_compatible", explanation: "The passage discusses multiple memory outcomes." },
      { dimension: "certainty_generalization_mismatch", status: "incompatible", explanation: "The passage explicitly cautions against a uniform effect." },
    ],
    explanation: "The passage describes variability by memory type, timing, and measurement, which limits the draft's universal wording.",
    evidence_quote: evidence2, recommended_action: "consider_narrowing_claim", model_version: "demo-example-v1",
    documentTitle: "Synthetic review passage B", documentAuthors: null, documentYear: null, section: null, page: null,
    review: "needs_review", note: "Check the cited task categories before revising.", claimText: claim1, sourceText: evidence2,
  },
  {
    id: "finding-3", claim_id: "claim-2", evidence_chunk_id: "chunk-3", relation: "support", confidence: 0.86,
    scope_compatibility: "compatible", dimension_comparisons: [
      { dimension: "population_compatibility", status: "unknown", explanation: "Population is not stated in the draft claim." },
      { dimension: "methodological_compatibility", status: "compatible", explanation: "The wording is appropriately limited to some declarative tasks." },
      { dimension: "certainty_generalization_mismatch", status: "compatible", explanation: "The draft uses qualified language." },
    ],
    explanation: "This review passage aligns with the claim's qualified wording. Confirm that the cited primary studies match the intended population and task.",
    evidence_quote: "Sleep following learning can benefit the retention of certain declarative memories; the size of the benefit differs across tasks and participants.",
    recommended_action: "review_source_context", model_version: "demo-example-v1",
    documentTitle: "Synthetic review passage C", documentAuthors: null, documentYear: null, section: null, page: null,
    review: "accepted", note: "Wording matches the review's qualification.", claimText: claim2,
    sourceText: "Sleep following learning can benefit the retention of certain declarative memories; the size of the benefit differs across tasks and participants.",
  },
  {
    id: "finding-4", claim_id: "claim-3", evidence_chunk_id: "chunk-4", relation: "insufficient_evidence", confidence: 0.41,
    scope_compatibility: "unknown", dimension_comparisons: [
      { dimension: "dataset_compatibility", status: "unknown", explanation: "No dataset is identified in the selected passage." },
      { dimension: "numerical_agreement", status: "unknown", explanation: "No matching numerical result is present." },
    ],
    explanation: "The selected sources do not provide a passage that directly assesses this numerical statement. Search for the original study or leave the claim unresolved.",
    evidence_quote: "The available review summarizes several experiments but does not report an overall pooled effect estimate for this outcome.",
    recommended_action: "search_for_additional_evidence", model_version: "demo-example-v1",
    documentTitle: "Synthetic review passage A", documentAuthors: null, documentYear: null, section: null, page: null,
    review: "unreviewed", note: "", claimText: "Sleep increases retention by exactly 42% in every age group.",
    sourceText: "The available review summarizes several experiments but does not report an overall pooled effect estimate for this outcome.",
  },
];
export const scopeLabels: Record<string, string> = {
  population: "Population", dataset: "Dataset", methodology: "Methodology", intervention: "Intervention",
  outcome: "Outcome", metric: "Metric", time_period: "Time period", domain: "Domain",
  conditions: "Conditions", certainty: "Certainty", direction: "Direction", numerical_values: "Numerical values",
};
export const sampleScope: ScientificScope = {
  ...unknownScope,
};
