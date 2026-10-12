export type Relation =
  | "support"
  | "contradict"
  | "qualify"
  | "scope_mismatch"
  | "insufficient_evidence"
  | "unrelated";
export type DimensionStatus = "compatible" | "incompatible" | "partially_compatible" | "unknown";
export type ScopeValue<T> = { status: "known"; value: T } | { status: "unknown"; value?: null };
export type ScopeField = ScopeValue<string | string[]>;

export interface ScientificScope {
  population: ScopeValue<string>;
  dataset: ScopeValue<string>;
  methodology: ScopeValue<string>;
  intervention: ScopeValue<string>;
  outcome: ScopeValue<string>;
  metric: ScopeValue<string>;
  time_period: ScopeValue<string>;
  domain: ScopeValue<string>;
  conditions: ScopeValue<string[]>;
  certainty: ScopeValue<string>;
  direction: ScopeValue<string>;
  numerical_values: ScopeValue<string[]>;
}
export interface SourceSpan {
  document_id: string;
  section_id: string | null;
  page_number: number | null;
  start_offset: number | null;
  end_offset: number | null;
  exact_text: string;
}
export interface AtomicClaim {
  id: string;
  text: string;
  document_id: string;
  claim_type: string;
  scope: ScientificScope;
  source_span: SourceSpan;
  extraction_method: string;
}
export interface EvidenceChunk {
  id: string;
  document_id: string;
  text: string;
  section_name: string | null;
  page_number: number | null;
  start_offset: number | null;
  end_offset: number | null;
  metadata: Record<string, unknown>;
}
export interface RetrievalHit {
  chunk: EvidenceChunk;
  score: number;
  rank: number;
  retrieval_method: string;
}
export interface DimensionComparison {
  dimension: string;
  status: DimensionStatus;
  explanation: string;
}
export interface ComparisonResult {
  claim_id: string;
  evidence_chunk_id: string;
  relation: Relation;
  confidence: number;
  scope_compatibility: DimensionStatus;
  dimension_comparisons: DimensionComparison[];
  explanation: string;
  evidence_quote: string;
  recommended_action: string;
  model_version: string;
}
export interface ClaimAnalysis {
  claim: AtomicClaim;
  retrieval_hits: RetrievalHit[];
  comparisons: ComparisonResult[];
}
export interface DocumentSummary {
  document_id: string;
  filename: string;
  status: string;
}
export interface DocumentUploadResponse extends DocumentSummary {
  message: string;
}
export interface AnalyzeRequest {
  draft_text: string;
  selected_document_ids: string[];
}
export interface AnalyzeResponse {
  analyses: ClaimAnalysis[];
  status: string;
}
export interface HealthResponse {
  status: string;
  version: string;
  mode: string;
}

export interface Project {
  id: string;
  name: string;
  description: string;
  updated: string;
  documents: number;
  drafts: number;
  analyses: number;
}
export interface ProjectResponse {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}
export interface LibraryDocument extends DocumentSummary {
  kind: "Draft" | "Source paper";
  title: string;
  authors: string | null;
  year: number | null;
  uploadedAt: string | null;
  claims: number;
}
export interface Finding extends ComparisonResult {
  id: string;
  documentTitle: string;
  documentAuthors: string | null;
  documentYear: number | null;
  section: string | null;
  page: number | null;
  review: "unreviewed" | "accepted" | "dismissed" | "needs_review";
  note: string;
  claimText: string;
  sourceText: string;
  claimScope?: ScientificScope;
}
