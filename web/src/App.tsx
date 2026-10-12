import { useEffect, useMemo, useRef, useState, type ChangeEvent, type DragEvent, type FormEvent, type ReactNode } from "react";
import { api, ApiError, configuredApiBase } from "./api";
import type { AnalyzeResponse, Finding, LibraryDocument, Project, Relation, ScopeField } from "./contracts";
import { demoDocuments, demoFindings, demoProjects, sampleScope } from "./demo";

type Page = "overview" | "documents" | "analysis" | "results" | "history";
type Mode = "demo" | "live";
const relationNames: Record<Relation, string> = {
  support: "Supports", contradict: "Contradicts", qualify: "Qualifies", scope_mismatch: "Scope mismatch",
  insufficient_evidence: "Insufficient evidence", unrelated: "Unrelated",
};
const relationClass: Record<Relation, string> = {
  support: "support", contradict: "contradict", qualify: "qualify", scope_mismatch: "mismatch",
  insufficient_evidence: "insufficient", unrelated: "unrelated",
};
const priorities: Record<Relation, string> = {
  support: "Routine", contradict: "High", qualify: "Review", scope_mismatch: "High",
  insufficient_evidence: "Review", unrelated: "Low",
};
const scopeRows = [
  ["population", "Population"], ["dataset", "Dataset"], ["methodology", "Methodology"],
  ["intervention", "Intervention"], ["outcome", "Outcome"], ["metric", "Metric"],
  ["time_period", "Time period"], ["domain", "Domain"], ["conditions", "Conditions"],
  ["certainty", "Certainty"], ["direction", "Direction"], ["numerical_values", "Numerical values"],
] as const;

function Icon({ name, size = 18 }: { name: string; size?: number }) {
  const paths: Record<string, ReactNode> = {
    grid: <><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /></>,
    files: <><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><path d="M14 2v6h6M8 13h8M8 17h8" /></>,
    search: <><circle cx="11" cy="11" r="7" /><path d="m20 20-4-4" /></>,
    chart: <><path d="M3 3v18h18" /><path d="m19 9-5 5-4-4-5 5" /></>,
    clock: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
    upload: <><path d="M12 16V4m-5 5 5-5 5 5" /><path d="M4 20h16" /></>,
    plus: <><path d="M12 5v14M5 12h14" /></>,
    arrow: <><path d="M5 12h14m-7-7 7 7-7 7" /></>,
    chevron: <path d="m9 18 6-6-6-6" />,
    close: <><path d="m18 6-12 12M6 6l12 12" /></>,
    check: <path d="m5 12 4 4L19 6" />,
    file: <><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><path d="M14 2v6h6" /></>,
  };
  return <svg aria-hidden="true" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">{paths[name] ?? paths.file}</svg>;
}
function scopeText(value: ScopeField | undefined): string {
  if (!value || value.status === "unknown") return "Unknown";
  return Array.isArray(value.value) ? value.value.join(", ") : String(value.value);
}
function findingsFromResponse(response: AnalyzeResponse, documents: LibraryDocument[]): Finding[] {
  return response.analyses.flatMap((analysis) => analysis.comparisons.map((comparison) => {
    const hit = analysis.retrieval_hits.find((item) => item.chunk.id === comparison.evidence_chunk_id);
    const doc = documents.find((item) => item.document_id === hit?.chunk.document_id);
    return {
      ...comparison, id: `${comparison.claim_id}-${comparison.evidence_chunk_id}`,
      documentTitle: doc?.title ?? doc?.filename ?? "Source document",
      documentAuthors: doc?.authors ?? null, documentYear: doc?.year ?? null,
      section: hit?.chunk.section_name ?? null, page: hit?.chunk.page_number ?? null,
      review: "unreviewed" as const, note: "", claimText: analysis.claim.text,
      sourceText: hit?.chunk.text ?? comparison.evidence_quote,
      claimScope: analysis.claim.scope,
    };
  }));
}

function App() {
  const [page, setPage] = useState<Page>(() => {
    const candidate = location.hash.slice(1) as Page;
    return ["overview", "documents", "analysis", "results", "history"].includes(candidate) ? candidate : "overview";
  });
  const [mode, setMode] = useState<Mode>((import.meta.env.VITE_API_MODE as Mode | undefined) === "live" ? "live" : "demo");
  const [projects, setProjects] = useState(demoProjects);
  const [projectId, setProjectId] = useState(demoProjects[0].id);
  const [documents, setDocuments] = useState<LibraryDocument[]>(demoDocuments);
  const [findings, setFindings] = useState<Finding[]>(demoFindings);
  const [loading, setLoading] = useState(false);
  const [liveError, setLiveError] = useState("");
  const [toast, setToast] = useState("");
  const [selectedFindingId, setSelectedFindingId] = useState("finding-1");
  const [selectedEvidence, setSelectedEvidence] = useState(0);
  const [relationFilter, setRelationFilter] = useState("all");
  const [priorityFilter, setPriorityFilter] = useState("all");
  const [reviewFilter, setReviewFilter] = useState("all");
  const [documentFilter, setDocumentFilter] = useState("all");
  const [modal, setModal] = useState<"project" | "upload" | null>(null);
  const [draftProjectName, setDraftProjectName] = useState("");
  const [draftText, setDraftText] = useState("Sleep universally improves memory consolidation across all types of learning. Sleep after learning can support consolidation of some declarative memories.");
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>(demoDocuments.filter((d) => d.kind === "Source paper").map((d) => d.document_id));
  const [analysisBusy, setAnalysisBusy] = useState(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadBusy, setUploadBusy] = useState(false);
  const [uploadMessage, setUploadMessage] = useState("");
  const [dragging, setDragging] = useState(false);
  const [newNote, setNewNote] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);
  const currentProject = projects.find((project) => project.id === projectId) ?? projects[0];
  const selectedFinding = findings.find((finding) => finding.id === selectedFindingId) ?? findings[0];
  const visibleFindings = useMemo(() => findings.filter((finding) =>
    (relationFilter === "all" || finding.relation === relationFilter)
    && (priorityFilter === "all" || priorities[finding.relation].toLowerCase() === priorityFilter)
    && (reviewFilter === "all" || finding.review === reviewFilter)
    && (documentFilter === "all" || finding.documentTitle === documentFilter)), [findings, relationFilter, priorityFilter, reviewFilter, documentFilter]);

  useEffect(() => {
    const onHash = () => {
      const candidate = location.hash.slice(1) as Page;
      if (["overview", "documents", "analysis", "results", "history"].includes(candidate)) setPage(candidate);
    };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  useEffect(() => {
    if (mode !== "live") { setLiveError(""); setLoading(false); return; }
    let active = true;
    setLoading(true);
    setLiveError("");
    Promise.all([api.health(), api.projects()]).then(([, remoteProjects]) => {
      if (!active) return;
      const mapped = remoteProjects.map((project) => ({
        id: project.id, name: project.name, description: project.description ?? "",
        updated: new Date(project.updated_at).toLocaleDateString(), documents: 0, drafts: 0, analyses: 0,
      }));
      setProjects(mapped);
      setProjectId((current) => mapped.some((item) => item.id === current) ? current : mapped[0]?.id ?? "");
      if (!mapped.length) { setDocuments([]); setSelectedDocIds([]); setFindings([]); }
    }).catch((error: unknown) => {
      if (active) setLiveError(error instanceof ApiError ? error.message : "Could not load workspace data.");
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [mode]);

  useEffect(() => {
    if (mode !== "live" || !projectId || projects.every((project) => project.id !== projectId)) return;
    let active = true;
    setLoading(true);
    api.documents(projectId).then((remoteDocs) => {
      if (!active) return;
      setDocuments(remoteDocs.map((doc) => ({
        ...doc, kind: "Source paper" as const, title: doc.filename, authors: null, year: null,
        uploadedAt: null, claims: 0,
      })));
      setSelectedDocIds(remoteDocs.map((doc) => doc.document_id));
      setFindings([]);
    }).catch((error: unknown) => {
      if (active) setLiveError(error instanceof ApiError ? error.message : "Could not load project documents.");
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [mode, projectId, projects]);

  function navigate(next: Page) {
    setPage(next);
    location.hash = next;
  }
  function notify(message: string) {
    setToast(message);
    window.setTimeout(() => setToast(""), 3400);
  }
  function switchMode(next: Mode) {
    setMode(next);
    setLiveError("");
    if (next === "demo") {
      setDocuments(demoDocuments); setFindings(demoFindings);
      setProjects(demoProjects); setProjectId(demoProjects[0].id);
    }
  }
  function selectProject(id: string) {
    setProjectId(id);
    if (mode === "live") { setFindings([]); setSelectedDocIds([]); }
    else {
      if (id === demoProjects[0].id) {
        setDocuments(demoDocuments);
        setFindings(demoFindings);
      } else {
        setDocuments([]);
        setFindings([]);
      }
    }
  }
  async function addProject(event: FormEvent) {
    event.preventDefault();
    const name = draftProjectName.trim();
    if (!name) return;
    if (mode === "live") {
      setLiveError("");
      try {
        const created = await api.createProject(name);
        const project: Project = { id: created.id, name: created.name, description: created.description ?? "", updated: new Date(created.updated_at).toLocaleDateString(), documents: 0, drafts: 0, analyses: 0 };
        setProjects((items) => [project, ...items]); setProjectId(project.id); setDocuments([]); setSelectedDocIds([]); setFindings([]);
        setDraftProjectName(""); setModal(null); notify("Project created.");
      } catch (error) { setLiveError(error instanceof ApiError ? error.message : "Project could not be created."); }
      return;
    }
    const project: Project = { id: `project-${Date.now()}`, name, description: "New research workspace", updated: "Just now", documents: 0, drafts: 0, analyses: 0 };
    setProjects((items) => [project, ...items]); setProjectId(project.id); setDocuments([]); setFindings([]); setDraftProjectName(""); setModal(null);
    notify("Project created in this demo session.");
  }
  function validateFile(file: File): string {
    const allowed = /\.(pdf|docx|txt|md|markdown)$/i.test(file.name);
    if (!allowed) return "Choose a PDF, DOCX, TXT, or Markdown file.";
    if (file.size > 25 * 1024 * 1024) return "Files must be smaller than 25 MB.";
    return "";
  }
  function chooseFile(file?: File) {
    if (!file) return;
    const error = validateFile(file);
    setUploadMessage(error);
    setUploadFile(error ? null : file);
    setUploadProgress(0);
  }
  function onFileChange(event: ChangeEvent<HTMLInputElement>) { chooseFile(event.target.files?.[0]); }
  function onDrop(event: DragEvent) {
    event.preventDefault(); setDragging(false); chooseFile(event.dataTransfer.files[0]);
  }
  async function startUpload() {
    if (!uploadFile) return;
    setUploadMessage(""); setUploadBusy(true); setUploadProgress(0);
    if (mode === "live") {
      try {
        if (!projectId) throw new ApiError("Create or select a project before uploading documents.");
        const uploaded = await api.upload(uploadFile, projectId, setUploadProgress);
        setDocuments((items) => [{ ...uploaded, title: uploaded.filename, kind: "Source paper", authors: null, year: null, uploadedAt: null, claims: 0 }, ...items]);
        setSelectedDocIds((items) => items.includes(uploaded.document_id) ? items : [...items, uploaded.document_id]);
        setUploadMessage(uploaded.message || "Upload complete. Processing status will update when the document is ready.");
      } catch (error) {
        setUploadMessage(error instanceof ApiError ? error.message : "Upload failed.");
      } finally { setUploadBusy(false); }
      return;
    }
    const timer = window.setInterval(() => setUploadProgress((progress) => {
      if (progress >= 92) { window.clearInterval(timer); return 100; }
      return Math.min(progress + 13, 92);
    }), 110);
    window.setTimeout(() => {
      window.clearInterval(timer);
      const document: LibraryDocument = {
        document_id: `demo-${Date.now()}`, filename: uploadFile.name, title: uploadFile.name.replace(/\.(pdf|docx)$/i, ""),
        kind: "Source paper", authors: null, year: null, uploadedAt: "Just now", status: "processing", claims: 0,
      };
      setDocuments((items) => [document, ...items]); setUploadProgress(100); setUploadBusy(false);
      setUploadMessage("Added to the demo library. Processing is simulated; no file was sent to a server.");
    }, 1050);
  }
  async function runAnalysis(event: FormEvent) {
    event.preventDefault();
    if (!draftText.trim()) { notify("Add draft text before running analysis."); return; }
    if (!selectedDocIds.length) { notify("Select at least one source document."); return; }
    if (mode === "demo") {
      setAnalysisBusy(true);
      window.setTimeout(() => {
        setFindings(demoFindings); setSelectedFindingId("finding-1"); setAnalysisBusy(false);
        navigate("analysis"); notify("Demo analysis shown. Example findings are synthetic.");
      }, 650);
      return;
    }
    setAnalysisBusy(true); setLiveError("");
    try {
      const response = await api.analyze({ draft_text: draftText, selected_document_ids: selectedDocIds });
      const result = findingsFromResponse(response, documents);
      setFindings(result); setSelectedFindingId(result[0]?.id ?? ""); navigate("analysis");
      if (!result.length) notify("The API returned no claim comparisons.");
    } catch (error) {
      setLiveError(error instanceof ApiError ? error.message : "Analysis could not be completed.");
    } finally { setAnalysisBusy(false); }
  }
  function updateReview(review: Finding["review"]) {
    if (!selectedFinding) return;
    if (mode === "live") { notify("Review persistence is not available in the API contract. No changes were saved."); return; }
    setFindings((items) => items.map((item) => item.id === selectedFinding.id ? { ...item, review, note: newNote.trim() || item.note } : item));
    setNewNote(""); notify("Review updated in this demo session only.");
  }

  const nav: { id: Page; label: string; icon: string }[] = [
    { id: "overview", label: "Overview", icon: "grid" }, { id: "documents", label: "Documents", icon: "files" },
    { id: "analysis", label: "Analysis workspace", icon: "search" }, { id: "results", label: "Results", icon: "chart" },
    { id: "history", label: "History", icon: "clock" },
  ];
  const pageTitle: Record<Page, string> = { overview: "Project overview", documents: "Document library", analysis: "Analysis workspace", results: "Analysis results", history: "Analysis history" };

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark">S</div><div><strong>SCOPE</strong><span>Research workspace</span></div></div>
      <div className="project-pick-label">CURRENT PROJECT</div>
      <label className="project-select-label" htmlFor="project-select">Select project</label>
      <select id="project-select" className="project-select" value={projectId} onChange={(e) => selectProject(e.target.value)}>
        {projects.map((project) => <option value={project.id} key={project.id}>{project.name}</option>)}
      </select>
      <button className="sidebar-new" onClick={() => setModal("project")}><Icon name="plus" size={16} /> New project</button>
      <nav className="nav-list" aria-label="Main navigation">
        {nav.map((item) => <button key={item.id} className={page === item.id ? "nav-item active" : "nav-item"} onClick={() => navigate(item.id)} aria-current={page === item.id ? "page" : undefined}>
          <Icon name={item.icon} /><span>{item.label}</span>{item.id === "results" && <span className="nav-count">{findings.length}</span>}
        </button>)}
      </nav>
      <div className="sidebar-foot">
        <div className="mode-caption">WORKSPACE MODE</div>
        <div className={mode === "demo" ? "mode-switch demo-on" : "mode-switch"}>
          <span className="mode-dot" />
          <span>{mode === "demo" ? "Demo data" : "Live API"}</span>
          <button className="mode-toggle" onClick={() => switchMode(mode === "demo" ? "live" : "demo")} aria-label={mode === "demo" ? "Switch to live API" : "Switch to demo data"}>{mode === "demo" ? "LIVE" : "DEMO"}</button>
        </div>
        <div className="api-caption">{mode === "live" ? configuredApiBase : "Sample workspace · synthetic examples"}</div>
        <div className="user-block"><div className="avatar">AR</div><div><strong>Alex Rivera</strong><span>Researcher</span></div><button aria-label="Account options" className="more-button">···</button></div>
      </div>
    </aside>

    <main className="main-area">
      <header className="topbar">
        <div className="breadcrumbs"><span>{currentProject?.name ?? "Research workspace"}</span><Icon name="chevron" size={14} /><strong>{pageTitle[page]}</strong></div>
        <div className="top-actions"><span className={mode === "demo" ? "status-pill demo-pill" : "status-pill live-pill"}><span />{mode === "demo" ? "DEMO WORKSPACE" : "LIVE CONNECTION"}</span><button className="avatar small" aria-label="Profile">AR</button></div>
      </header>
      <div className="page-content">
        {mode === "demo" && <div className="demo-banner"><span className="demo-icon">i</span><span><strong>Demo workspace</strong> · Example documents and findings are synthetic and for interface preview only.</span><button onClick={() => switchMode("live")}>Connect to API <Icon name="arrow" size={14} /></button></div>}
        {liveError && <div className="error-banner" role="alert"><span>{liveError}</span><button onClick={() => switchMode("demo")}>Enter demo mode</button><button className="icon-button" aria-label="Dismiss error" onClick={() => setLiveError("")}><Icon name="close" size={16} /></button></div>}
        {loading && <div className="loading-line"><span />Connecting to SCOPE API…</div>}
        {page === "overview" && <Overview project={currentProject} projects={projects} documents={documents} findings={findings} mode={mode} onOpen={navigate} onCreate={() => setModal("project")} onUpload={() => setModal("upload")} onSelectProject={selectProject} />}
        {page === "documents" && <Documents documents={documents} loading={loading} mode={mode} onUpload={() => { setModal("upload"); setUploadMessage(""); }} onAnalyze={(id) => { if (id) setSelectedDocIds((items) => items.includes(id) ? items : [...items, id]); navigate("analysis"); }} />}
        {page === "analysis" && <AnalysisWorkspace findings={findings} selected={selectedFinding} selectedEvidence={selectedEvidence} setSelectedEvidence={setSelectedEvidence} onSelect={(id) => { setSelectedFindingId(id); setSelectedEvidence(0); }} draftText={draftText} setDraftText={setDraftText} selectedDocIds={selectedDocIds} setSelectedDocIds={setSelectedDocIds} documents={documents} onAnalyze={runAnalysis} busy={analysisBusy} mode={mode} reviewNote={newNote} setReviewNote={setNewNote} onReview={updateReview} />}
        {page === "results" && <Results findings={visibleFindings} all={findings} relationFilter={relationFilter} setRelationFilter={setRelationFilter} priorityFilter={priorityFilter} setPriorityFilter={setPriorityFilter} reviewFilter={reviewFilter} setReviewFilter={setReviewFilter} documentFilter={documentFilter} setDocumentFilter={setDocumentFilter} onSelect={(id) => { setSelectedFindingId(id); navigate("analysis"); }} />}
        {page === "history" && <History findings={findings} onOpen={(id) => { setSelectedFindingId(id); navigate("analysis"); }} />}
      </div>
    </main>

    {toast && <div className="toast" role="status"><Icon name="check" size={16} />{toast}</div>}
    {modal === "project" && <div className="modal-backdrop" role="presentation" onMouseDown={(e) => { if (e.target === e.currentTarget) setModal(null); }}><form className="modal" onSubmit={addProject} aria-labelledby="project-modal-title">
      <div className="modal-head"><div><span className="eyebrow">WORKSPACE</span><h2 id="project-modal-title">Create a project</h2></div><button type="button" className="icon-button" aria-label="Close" onClick={() => setModal(null)}><Icon name="close" /></button></div>
      <label className="field-label" htmlFor="project-name">Project name</label><input autoFocus id="project-name" value={draftProjectName} onChange={(e) => setDraftProjectName(e.target.value)} placeholder="e.g. Nutrition intervention review" required maxLength={80} />
      {mode === "live" && <p className="inline-note">This project will be saved to the connected SCOPE backend.</p>}
      <div className="modal-actions"><button type="button" className="button secondary" onClick={() => setModal(null)}>Cancel</button><button className="button primary" type="submit">Create project</button></div>
    </form></div>}
    {modal === "upload" && <div className="modal-backdrop" role="presentation" onMouseDown={(e) => { if (e.target === e.currentTarget && !uploadBusy) setModal(null); }}><div className="modal upload-modal" role="dialog" aria-modal="true" aria-labelledby="upload-title">
      <div className="modal-head"><div><span className="eyebrow">DOCUMENT LIBRARY</span><h2 id="upload-title">Add a document</h2></div><button className="icon-button" aria-label="Close" onClick={() => setModal(null)} disabled={uploadBusy}><Icon name="close" /></button></div>
      <p className="modal-copy">Upload a source document to this project. PDF, DOCX, TXT, or Markdown files up to 25 MB.</p>
      <input ref={fileRef} type="file" accept=".pdf,.docx,.txt,.md,.markdown,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,text/markdown" onChange={onFileChange} hidden />
      <div className={dragging ? "drop-zone dragging" : "drop-zone"} onDragOver={(e) => { e.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={onDrop}>
        <div className="drop-icon"><Icon name="upload" size={20} /></div><strong>Drag your file here</strong><span>or <button className="text-button" onClick={() => fileRef.current?.click()} type="button">browse files</button></span><small>PDF, DOCX, TXT, or Markdown · 25 MB max</small>
      </div>
      {uploadFile && <div className="file-preview"><div className="file-type"><Icon name="file" /></div><div className="file-info"><strong>{uploadFile.name}</strong><span>{(uploadFile.size / 1024 / 1024).toFixed(1)} MB</span></div><button className="icon-button" aria-label="Remove file" onClick={() => { setUploadFile(null); setUploadProgress(0); }}><Icon name="close" size={16} /></button></div>}
      {uploadBusy && <div className="progress-wrap"><div className="progress-label"><span>{mode === "demo" ? "Simulating upload…" : "Uploading…"}</span><span>{uploadProgress}%</span></div><div className="progress-track"><span style={{ width: `${uploadProgress}%` }} /></div></div>}
      {uploadMessage && <div className={uploadMessage.startsWith("Choose") || uploadMessage.startsWith("Files") || uploadMessage.includes("failed") || uploadMessage.includes("not implemented") ? "upload-feedback error" : "upload-feedback"} role="status">{uploadMessage}</div>}
      {mode === "demo" && <p className="demo-upload-note">Demo mode: file bytes stay in your browser and are not processed.</p>}
      <div className="modal-actions"><button className="button secondary" onClick={() => setModal(null)} disabled={uploadBusy}>Close</button><button className="button primary" onClick={startUpload} disabled={!uploadFile || uploadBusy}>{uploadBusy ? "Working…" : mode === "demo" ? "Add to demo library" : "Upload document"}</button></div>
    </div></div>}
  </div>;
}

export default App;

function SectionHeading({ eyebrow, title, description, action }: { eyebrow?: string; title: string; description?: string; action?: ReactNode }) {
  return <div className="section-heading"><div>{eyebrow && <div className="eyebrow">{eyebrow}</div>}<h1>{title}</h1>{description && <p>{description}</p>}</div>{action && <div>{action}</div>}</div>;
}
function Overview({ project, projects, documents, findings, mode, onOpen, onCreate, onUpload, onSelectProject }: { project?: Project; projects: Project[]; documents: LibraryDocument[]; findings: Finding[]; mode: Mode; onOpen: (page: Page) => void; onCreate: () => void; onUpload: () => void; onSelectProject: (id: string) => void }) {
  const relationCounts: [Relation, string][] = [["support", "Supported"], ["contradict", "Contradictions"], ["qualify", "Qualifications"], ["scope_mismatch", "Scope mismatches"], ["insufficient_evidence", "Insufficient evidence"], ["unrelated", "Unrelated"]];
  return <div className="overview-page">
    <SectionHeading eyebrow="PROJECT OVERVIEW" title={project?.name ?? "Your projects"} description={project?.description ?? "Manage your evidence review projects."} action={<button className="button primary" onClick={onCreate}><Icon name="plus" size={16} /> New project</button>} />
    <div className="overview-meta"><span><span className="tiny-dot" /> Active project</span><span>Last activity {project?.updated ?? "—"}</span><span>{projects.length} projects</span></div>
    <div className="metric-grid">
      {[["Source documents", documents.filter((item) => item.kind === "Source paper").length, "files"], ["Drafts", documents.filter((item) => item.kind === "Draft").length, "files"], ["Analyzed findings", findings.length, "chart"], ["Needs review", findings.filter((item) => item.review === "unreviewed" || item.review === "needs_review").length, "clock"]].map(([label, value, icon]) =>
        <div className="metric-card" key={String(label)}><div className="metric-icon"><Icon name={String(icon)} size={17} /></div><span>{label}</span><strong>{value}</strong><small>{mode === "demo" ? "In this sample project" : "Loaded from current API session"}</small></div>)}
    </div>
    <div className="dashboard-grid">
      <section className="panel project-list-panel">
        <div className="panel-heading"><div><h2>Research projects</h2><p>Workspaces you can return to</p></div><button className="subtle-link" onClick={onCreate}>Create project <Icon name="arrow" size={14} /></button></div>
        <div className="project-list">{projects.map((item, i) => <button className={item.id === project?.id ? "project-row selected" : "project-row"} key={item.id} onClick={() => onSelectProject(item.id)}>
          <div className={`project-avatar color-${i % 3}`}>{item.name.slice(0, 1).toUpperCase()}</div><div className="project-row-main"><strong>{item.name}</strong><span>{item.description}</span><small>{item.documents} documents <i /> {item.analyses} analyses</small></div><span className="project-updated">{item.updated}</span><Icon name="chevron" size={16} />
        </button>)}</div>
        <button className="project-list-footer" onClick={onCreate}><Icon name="plus" size={16} /> Create another project</button>
      </section>
      <section className="panel activity-panel">
        <div className="panel-heading"><div><h2>Recent activity</h2><p>Latest work in this project</p></div><button className="subtle-link" onClick={() => onOpen("history")}>View history <Icon name="arrow" size={14} /></button></div>
        <div className="activity-list">
          <div className="activity-item"><span className="activity-icon blue"><Icon name="chart" size={15} /></span><div><strong>Claim analysis completed</strong><span>Example draft synthesis · 4 findings</span><small>Today, 10:42</small></div><button onClick={() => onOpen("results")} aria-label="Open recent analysis"><Icon name="chevron" size={16} /></button></div>
          <div className="activity-item"><span className="activity-icon tan"><Icon name="files" size={15} /></span><div><strong>Source paper added</strong><span>Synthetic review passage A</span><small>Yesterday, 16:18</small></div><button onClick={() => onOpen("documents")} aria-label="Open documents"><Icon name="chevron" size={16} /></button></div>
          <div className="activity-item"><span className="activity-icon green"><Icon name="check" size={15} /></span><div><strong>Finding accepted</strong><span>“Sleep after learning can support…”</span><small>Oct 10, 09:06</small></div><button onClick={() => onOpen("analysis")} aria-label="Open analysis workspace"><Icon name="chevron" size={16} /></button></div>
        </div>
        <div className="activity-footnote">Activity shown here is part of the example workspace.</div>
      </section>
    </div>
    <section className="panel finding-summary">
      <div className="panel-heading"><div><h2>Findings at a glance</h2><p>Relationship labels organize evidence for researcher review.</p></div><button className="subtle-link" onClick={() => onOpen("results")}>Open results <Icon name="arrow" size={14} /></button></div>
      <div className="summary-stats">{relationCounts.map(([relation, label]) => <button className="summary-stat" key={relation} onClick={() => onOpen("results")}><span className={`relation-dot ${relationClass[relation]}`} /><span>{label}</span><strong>{findings.filter((item) => item.relation === relation).length}</strong></button>)}</div>
    </section>
    <div className="quick-actions"><div><strong>Continue your review</strong><span>Bring in source material or inspect a claim against its evidence.</span></div><button className="button secondary" onClick={onUpload}><Icon name="upload" size={16} /> Add documents</button><button className="button primary" onClick={() => onOpen("analysis")}><Icon name="search" size={16} /> Open analysis workspace</button></div>
  </div>;
}
function Documents({ documents, loading, mode, onUpload, onAnalyze }: { documents: LibraryDocument[]; loading: boolean; mode: Mode; onUpload: () => void; onAnalyze: (id?: string) => void }) {
  const [filter, setFilter] = useState("All documents");
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<LibraryDocument | null>(null);
  const filtered = documents.filter((doc) => (filter === "All documents" || doc.kind === filter) && (doc.title.toLowerCase().includes(query.toLowerCase()) || doc.filename.toLowerCase().includes(query.toLowerCase())));
  return <div className="documents-page">
    <SectionHeading eyebrow="PROJECT MATERIALS" title="Document library" description="Manage drafts and source papers used in claim analysis." action={<button className="button primary" onClick={onUpload}><Icon name="upload" size={16} /> Add document</button>} />
    <div className="library-toolbar"><div className="segmented">{["All documents", "Draft", "Source paper"].map((item) => <button key={item} className={filter === item ? "selected" : ""} onClick={() => setFilter(item)}>{item}{item === "All documents" && <span>{documents.length}</span>}</button>)}</div><div className="library-search"><Icon name="search" size={16} /><input placeholder="Search documents" aria-label="Search documents" value={query} onChange={(e) => setQuery(e.target.value)} /></div></div>
    {loading ? <div className="empty-state">Loading documents…</div> : filtered.length === 0 ? <div className="empty-state"><span className="empty-icon"><Icon name="files" size={22} /></span><strong>No documents here yet</strong><p>Add a draft or a source paper to begin your review.</p><button className="button primary" onClick={onUpload}><Icon name="upload" size={15} /> Add document</button></div> :
      <div className="library-layout"><section className="panel document-table-panel"><div className="table-wrap"><table className="document-table"><thead><tr><th>DOCUMENT</th><th>TYPE</th><th>PUBLICATION</th><th>ADDED</th><th>STATUS</th><th></th></tr></thead><tbody>
        {filtered.map((doc) => <tr key={doc.document_id} className={selected?.document_id === doc.document_id ? "row-selected" : ""} onClick={() => setSelected(doc)} tabIndex={0} onKeyDown={(e) => { if (e.key === "Enter") setSelected(doc); }}>
          <td><div className="document-title-cell"><span className={doc.kind === "Draft" ? "document-file draft-file" : "document-file"}><Icon name="file" size={17} /></span><span><strong>{doc.title}</strong><small>{doc.filename}</small></span></div></td>
          <td><span className={doc.kind === "Draft" ? "type-pill draft-type" : "type-pill source-type"}>{doc.kind}</span></td>
          <td>{doc.authors ? <span>{doc.authors}{doc.year ? ` · ${doc.year}` : ""}</span> : <span className="muted">Not available</span>}</td>
          <td>{doc.uploadedAt ?? <span className="muted">Not available</span>}</td>
          <td><span className={doc.status === "ready" ? "processing-status ready" : "processing-status processing"}><span />{doc.status === "ready" ? "Ready" : "Processing"}</span></td>
          <td><button className="icon-button row-open" aria-label={`View ${doc.title}`} onClick={(e) => { e.stopPropagation(); setSelected(doc); }}><Icon name="chevron" size={16} /></button></td>
        </tr>)}
      </tbody></table></div><div className="table-footer"><span>Showing {filtered.length} of {documents.length} documents</span><span>Publication metadata appears only when provided by the source.</span></div></section>
      {selected && <aside className="panel metadata-panel"><div className="metadata-head"><span className={selected.kind === "Draft" ? "document-file draft-file" : "document-file"}><Icon name="file" /></span><button className="icon-button" aria-label="Close details" onClick={() => setSelected(null)}><Icon name="close" size={16} /></button></div><span className={selected.kind === "Draft" ? "type-pill draft-type" : "type-pill source-type"}>{selected.kind}</span><h2>{selected.title}</h2><p className="metadata-filename">{selected.filename}</p><dl className="metadata-list"><div><dt>Authors</dt><dd>{selected.authors ?? "Not available"}</dd></div><div><dt>Publication year</dt><dd>{selected.year ?? "Not available"}</dd></div><div><dt>Added</dt><dd>{selected.uploadedAt ?? "Not available"}</dd></div><div><dt>Processing status</dt><dd>{selected.status === "ready" ? "Ready" : "Processing"}</dd></div><div><dt>Available claims</dt><dd>{selected.claims || "Not extracted"}</dd></div><div><dt>Document ID</dt><dd className="id-value">{selected.document_id}</dd></div></dl><div className="metadata-actions"><button className="button primary full" onClick={() => onAnalyze(selected.kind === "Source paper" ? selected.document_id : undefined)}><Icon name="search" size={15} /> Analyze with this document</button><small>{mode === "demo" ? "Analysis examples are synthetic." : "Analysis uses the selected document if supported by the API."}</small></div></aside>}
    </div>}
  </div>;
}
function AnalysisWorkspace({ findings, selected, selectedEvidence, setSelectedEvidence, onSelect, draftText, setDraftText, selectedDocIds, setSelectedDocIds, documents, onAnalyze, busy, mode, reviewNote, setReviewNote, onReview }: {
  findings: Finding[]; selected?: Finding; selectedEvidence: number; setSelectedEvidence: (index: number) => void; onSelect: (id: string) => void;
  draftText: string; setDraftText: (text: string) => void; selectedDocIds: string[]; setSelectedDocIds: (ids: string[]) => void;
  documents: LibraryDocument[]; onAnalyze: (event: FormEvent) => void; busy: boolean; mode: Mode; reviewNote: string; setReviewNote: (note: string) => void; onReview: (review: Finding["review"]) => void;
}) {
  const [showRunForm, setShowRunForm] = useState(false);
  const uniqueClaims = Array.from(new Map(findings.map((finding) => [finding.claim_id, finding])).values());
  const sameClaim = selected ? findings.filter((finding) => finding.claim_id === selected.claim_id) : [];
  const passage = sameClaim[selectedEvidence] ?? selected;
  const dimensions = selected?.dimension_comparisons ?? [];
  const scopeValue = (label: string) => scopeText((selected?.claimScope ?? sampleScope)[label as keyof typeof sampleScope] as ScopeField);
  return <div className="analysis-page">
    <div className="analysis-heading"><div><div className="eyebrow">EVIDENCE REVIEW</div><h1>Analysis workspace</h1><p>Compare draft wording with retrieved passages and inspect scope differences.</p></div><div className="analysis-heading-actions"><span className={mode === "demo" ? "status-pill demo-pill" : "status-pill live-pill"}><span />{mode === "demo" ? "EXAMPLE ANALYSIS" : "LIVE API"}</span><button className="button primary" onClick={() => setShowRunForm((value) => !value)}><Icon name="search" size={15} /> Run analysis</button></div></div>
    {showRunForm && <form className="panel run-form" onSubmit={(event) => { onAnalyze(event); if (mode === "demo") setShowRunForm(false); }}>
      <div className="run-form-head"><div><h2>Analyze draft claims</h2><p>Choose source documents and review the draft text before submitting.</p></div><button type="button" className="icon-button" aria-label="Close analysis form" onClick={() => setShowRunForm(false)}><Icon name="close" size={16} /></button></div>
      <label className="field-label" htmlFor="draft-text">Draft text</label><textarea id="draft-text" rows={4} value={draftText} onChange={(e) => setDraftText(e.target.value)} placeholder="Paste draft claims here" required />
      <div className="field-label source-label">Select source documents <span>Required</span></div><div className="source-choices">{documents.filter((doc) => doc.kind === "Source paper").map((doc) => <label key={doc.document_id}><input type="checkbox" checked={selectedDocIds.includes(doc.document_id)} onChange={(e) => setSelectedDocIds(e.target.checked ? [...selectedDocIds, doc.document_id] : selectedDocIds.filter((id) => id !== doc.document_id))} /><span><strong>{doc.title}</strong><small>{doc.authors ?? "Publication metadata unavailable"}{doc.year ? ` · ${doc.year}` : ""}</small></span></label>)}</div>
      <div className="run-form-footer"><span>{mode === "demo" ? "Synthetic example output" : "Submitted to configured FastAPI service"}</span><button className="button primary" type="submit" disabled={busy}>{busy ? <><span className="spinner" /> Analyzing…</> : "Analyze selected text"}</button></div>
    </form>}
    <div className="workspace-grid">
      <section className="panel claims-panel"><div className="workspace-panel-head"><div><h2>Draft claims</h2><span>{uniqueClaims.length} claims</span></div><button className="icon-button" aria-label="Claim list options"><span className="kebab">···</span></button></div>
        <div className="claim-source"><span className="draft-source-icon"><Icon name="file" size={15} /></span><div><strong>Example draft synthesis</strong><small>Draft document · example claims</small></div></div>
        <div className="claims-list">{uniqueClaims.map((finding, index) => <button className={finding.claim_id === selected?.claim_id ? "claim-item selected" : "claim-item"} key={finding.claim_id} onClick={() => onSelect(finding.id)}>
          <div className="claim-item-top"><span>CLAIM {String(index + 1).padStart(2, "0")}</span><span className={`priority-label ${priorities[finding.relation].toLowerCase().replace(" ", "-")}`}>{priorities[finding.relation]}</span></div><p>{finding.claimText}</p><div className="claim-item-bottom"><RelationTag relation={finding.relation} /><span>{findings.filter((item) => item.claim_id === finding.claim_id).length} passages</span></div>
        </button>)}</div>
        <button className="add-claim-button" onClick={() => setShowRunForm(true)}><Icon name="plus" size={15} /> Add draft text</button>
      </section>
      <section className="evidence-column">
        <div className="panel draft-claim-card"><div className="evidence-topline"><span className="evidence-label">SELECTED DRAFT CLAIM</span><span className="claim-id">{selected?.claim_id ?? "—"}</span></div><p>{selected?.claimText ?? "Select a claim to inspect its evidence."}</p><span className="source-inline"><Icon name="file" size={13} /> Example draft synthesis · Draft document</span></div>
        <div className="panel evidence-panel"><div className="evidence-panel-heading"><div><span className="evidence-label">RETRIEVED EVIDENCE</span><h2>Source passage</h2></div><span className="passage-counter">{sameClaim.length ? `0${selectedEvidence + 1} / 0${sameClaim.length}` : "—"}</span></div>
          {sameClaim.length > 1 && <div className="passage-tabs" role="tablist" aria-label="Evidence passages">{sameClaim.map((item, index) => <button role="tab" aria-selected={selectedEvidence === index} className={selectedEvidence === index ? "active" : ""} key={item.id} onClick={() => setSelectedEvidence(index)}><span>{item.documentAuthors ?? "Source"}</span>{item.documentYear ?? "Year unavailable"}</button>)}</div>}
          <div className="source-document-line"><span className="paper-icon"><Icon name="file" size={16} /></span><span><strong>{passage?.documentTitle ?? "No source selected"}</strong><small>{passage?.documentAuthors ?? "Author metadata unavailable"}{passage?.documentYear ? ` · ${passage.documentYear}` : ""}</small></span><span className="match-score">{passage ? `${Math.round(passage.confidence * 100)}%` : "—"}<small>match score</small></span></div>
          <div className="evidence-quote"><div className="quote-mark">“</div><p>{passage?.sourceText ?? "Select a claim to view retrieved evidence."}</p></div>
          <div className="passage-provenance"><span><strong>Section</strong>{passage?.section ?? "Not available"}</span><span><strong>Page</strong>{passage?.page ?? "Not available"}</span><span><strong>Source ID</strong>{passage?.evidence_chunk_id ?? "Not available"}</span></div>
          <div className="evidence-foot"><span>Exact passage from indexed source</span><button className="subtle-link" onClick={() => navigator.clipboard?.writeText(passage?.sourceText ?? "")}>Copy quotation</button></div>
        </div>
        <div className="panel graph-panel"><div className="graph-heading"><div><h2>Evidence path</h2><p>Trace this finding to its source</p></div><span className="graph-caption">RECORD LINKAGE</span></div><EvidenceGraph finding={passage} /></div>
      </section>
      <aside className="alignment-column">
        <div className="panel alignment-card"><div className="alignment-head"><div><span className="evidence-label">PREDICTED RELATIONSHIP</span><h2>{selected ? <RelationTag relation={selected.relation} /> : "No finding selected"}</h2></div><button className="icon-button"><span className="kebab">···</span></button></div>
          <div className="confidence-row"><span>Model confidence</span><strong>{selected ? `${Math.round(selected.confidence * 100)}%` : "—"}</strong></div><div className="confidence-track"><span style={{ width: `${selected ? selected.confidence * 100 : 0}%` }} /></div>
          <p className="alignment-explanation">{selected?.explanation ?? "Select a claim and passage to inspect the comparison."}</p>
          <div className="review-callout"><span className="callout-icon">i</span><p>This is an automated comparison to support your review. It does not establish scientific truth.</p></div>
          <div className="scope-section-head"><h3>Scope compatibility</h3><StatusTag status={selected?.scope_compatibility ?? "unknown"} /></div>
          <ScopeTable dimensions={dimensions} scopeValue={scopeValue} />
          <div className="recommended-action"><span>RECOMMENDED ACTION</span><strong>{selected ? selected.recommended_action.replaceAll("_", " ") : "No recommendation"}</strong></div>
          <div className="review-controls"><div className="review-state">Review status <span>{selected?.review.replace("_", " ") ?? "—"}</span></div><label className="field-label" htmlFor="review-note">Reviewer note</label><textarea id="review-note" rows={2} placeholder="Add a note for your team…" value={reviewNote} onChange={(e) => setReviewNote(e.target.value)} /><div className="review-buttons"><button className="button review-accept" onClick={() => onReview("accepted")}><Icon name="check" size={15} /> Accept</button><button className="button review-secondary" onClick={() => onReview("needs_review")}>Needs review</button><button className="button review-dismiss" onClick={() => onReview("dismissed")}>Dismiss</button></div><small>{mode === "demo" ? "Saved in this browser session only." : "Review actions are not persisted by the API."}</small></div>
        </div>
      </aside>
    </div>
  </div>;
}
function RelationTag({ relation }: { relation: Relation }) {
  const icon = relation === "support" ? "✓" : relation === "contradict" ? "×" : relation === "qualify" ? "≈" : relation === "scope_mismatch" ? "↔" : relation === "unrelated" ? "·" : "?";
  return <span className={`relation-tag ${relationClass[relation]}`}><span>{icon}</span>{relationNames[relation]}</span>;
}
function StatusTag({ status }: { status: string }) {
  const label = status === "partially_compatible" ? "Partial" : status.slice(0, 1).toUpperCase() + status.slice(1);
  return <span className={`status-tag ${status.replaceAll("_", "-")}`}><span />{label}</span>;
}
function ScopeTable({ dimensions, scopeValue }: { dimensions: Finding["dimension_comparisons"]; scopeValue: (key: string) => string }) {
  const mapped: Record<string, string> = {
    population_compatibility: "population", dataset_compatibility: "dataset", methodological_compatibility: "methodology",
    outcome_metric_compatibility: "outcome", numerical_agreement: "numerical_values", relation_direction_agreement: "direction",
    experimental_condition_compatibility: "conditions", certainty_generalization_mismatch: "certainty",
  };
  const entries = new Map(dimensions.map((dimension) => [mapped[dimension.dimension] ?? dimension.dimension, dimension]));
  return <div className="scope-table-scroll"><table className="scope-table"><thead><tr><th>Dimension</th><th>Draft claim</th><th>Source evidence</th><th>Compatibility</th><th>Explanation</th></tr></thead><tbody>{scopeRows.map(([key, label]) => {
    const dimension = entries.get(key);
    const draftValue = scopeValue(key);
    const sourceText = dimension?.status === "unknown" ? "Unknown" : "Not extracted";
    const explanation = dimension?.explanation ?? "No dimension comparison was returned.";
    const status = dimension?.status ?? "unknown";
    return <tr key={key}><th>{label}</th><td>{draftValue}</td><td>{sourceText}</td><td><StatusTag status={status} /></td><td>{explanation}</td></tr>;
  })}</tbody></table></div>;
}
function EvidenceGraph({ finding }: { finding?: Finding }) {
  return <div className="evidence-graph" aria-label="Source document leads to an evidence passage, then a draft claim and predicted relationship">
    <div className="graph-node"><span className="graph-node-icon"><Icon name="files" size={16} /></span><span><strong>{finding?.documentTitle ?? "Source document"}</strong><small>Research document</small></span></div><div className="graph-edge"><span /></div>
    <div className="graph-node"><span className="graph-node-icon passage"><Icon name="file" size={16} /></span><span><strong>{finding?.evidence_chunk_id ?? "Evidence passage"}</strong><small>{finding?.section ?? "Section unavailable"}{finding?.page ? ` · p. ${finding.page}` : ""}</small></span></div><div className="graph-edge"><span /></div>
    <div className="graph-node"><span className="graph-node-icon claim"><Icon name="file" size={16} /></span><span><strong>{finding?.claim_id ?? "Draft claim"}</strong><small>Draft document</small></span></div><div className="graph-edge"><span /></div>
    <div className={finding ? `graph-relation ${relationClass[finding.relation]}` : "graph-relation"}>{finding ? relationNames[finding.relation] : "Relationship"}</div>
  </div>;
}
function Results({ findings, all, relationFilter, setRelationFilter, priorityFilter, setPriorityFilter, reviewFilter, setReviewFilter, documentFilter, setDocumentFilter, onSelect }: {
  findings: Finding[]; all: Finding[]; relationFilter: string; setRelationFilter: (value: string) => void; priorityFilter: string; setPriorityFilter: (value: string) => void; reviewFilter: string; setReviewFilter: (value: string) => void; documentFilter: string; setDocumentFilter: (value: string) => void; onSelect: (id: string) => void;
}) {
  return <div className="results-page">
    <SectionHeading eyebrow="FINDINGS" title="Analysis results" description="Review the relationship labels and evidence passages returned for this project." action={<button className="button secondary" onClick={() => window.print()}>Export view</button>} />
    <div className="results-counters">{(["support", "contradict", "qualify", "scope_mismatch", "insufficient_evidence", "unrelated"] as Relation[]).map((relation) => <div className="result-counter" key={relation}><span className={`relation-dot ${relationClass[relation]}`} /><span>{relationNames[relation]}</span><strong>{all.filter((item) => item.relation === relation).length}</strong></div>)}</div>
    <section className="panel results-panel"><div className="results-toolbar"><div><h2>Findings <span>{findings.length}</span></h2><p>Each result links a draft claim to a retrieved source passage.</p></div><div className="filter-row">
      <label><span>Relationship</span><select value={relationFilter} onChange={(e) => setRelationFilter(e.target.value)}><option value="all">All relations</option>{Object.entries(relationNames).map(([key, value]) => <option value={key} key={key}>{value}</option>)}</select></label>
      <label><span>Priority</span><select value={priorityFilter} onChange={(e) => setPriorityFilter(e.target.value)}><option value="all">All priorities</option><option value="high">High</option><option value="review">Review</option><option value="routine">Routine</option><option value="low">Low</option></select></label>
      <label><span>Source</span><select value={documentFilter} onChange={(e) => setDocumentFilter(e.target.value)}><option value="all">All sources</option>{Array.from(new Set(all.map((item) => item.documentTitle))).map((title) => <option key={title} value={title}>{title}</option>)}</select></label>
      <label><span>Review state</span><select value={reviewFilter} onChange={(e) => setReviewFilter(e.target.value)}><option value="all">All states</option><option value="unreviewed">Unreviewed</option><option value="accepted">Accepted</option><option value="dismissed">Dismissed</option><option value="needs_review">Needs review</option></select></label>
    </div></div>
      {findings.length ? <div className="table-wrap"><table className="results-table"><thead><tr><th>CLAIM / PASSAGE</th><th>RELATION</th><th>SCOPE FIT</th><th>CONFIDENCE</th><th>PRIORITY</th><th>REVIEW</th><th></th></tr></thead><tbody>{findings.map((finding) => <tr key={finding.id}>
        <td><button className="result-claim-cell" onClick={() => onSelect(finding.id)}><strong>{finding.claimText}</strong><span><Icon name="file" size={13} /> {finding.documentTitle}{finding.documentYear ? ` · ${finding.documentYear}` : ""}</span><small>“{finding.sourceText.slice(0, 118)}{finding.sourceText.length > 118 ? "…" : ""}”</small></button></td>
        <td><RelationTag relation={finding.relation} /></td><td><StatusTag status={finding.scope_compatibility} /></td><td><div className="confidence-cell"><strong>{Math.round(finding.confidence * 100)}%</strong><span><i style={{ width: `${finding.confidence * 100}%` }} /></span></div></td>
        <td><span className={`priority-label ${priorities[finding.relation].toLowerCase().replace(" ", "-")}`}>{priorities[finding.relation]}</span></td>
        <td><span className={`review-pill ${finding.review}`}>{finding.review.replace("_", " ")}</span></td><td><button className="icon-button" aria-label="Inspect finding" onClick={() => onSelect(finding.id)}><Icon name="chevron" size={16} /></button></td>
      </tr>)}</tbody></table></div> : <div className="empty-state compact"><strong>No findings match these filters</strong><p>Try a different relationship, source, priority, or review state.</p><button className="button secondary" onClick={() => { setRelationFilter("all"); setReviewFilter("all"); setDocumentFilter("all"); setPriorityFilter("all"); }}>Clear filters</button></div>}
      <div className="results-footer"><span>Showing {findings.length} of {all.length} findings</span><span>Automated comparisons require human interpretation.</span></div>
    </section>
    <div className="results-disclaimer">These relationship labels describe model comparisons between the claim and retrieved text. They do not establish whether a scientific claim is true.</div>
  </div>;
}
function History({ findings, onOpen }: { findings: Finding[]; onOpen: (id: string) => void }) {
  const groups = Array.from(new Map(findings.map((finding) => [finding.claim_id, finding])).values());
  return <div className="history-page">
    <SectionHeading eyebrow="PROJECT ACTIVITY" title="Analysis history" description="Recent claim comparisons from the current workspace." action={<span className="status-pill demo-pill"><span />{findings[0]?.model_version ?? "NO ANALYSIS RUNS"}</span>} />
    <div className="history-timeline">{groups.map((finding, index) => <div className="history-entry" key={finding.claim_id}><div className="timeline-rail"><span className="timeline-dot" />{index < groups.length - 1 && <span className="timeline-line" />}</div><section className="panel history-card"><div className="history-card-head"><div><span className="history-date">{index === 0 ? "TODAY · 10:42" : `OCT ${10 - index} · 09:18`}</span><h2>Draft analysis <span className="small-run-id">{finding.claim_id}</span></h2></div><button className="button secondary small" onClick={() => onOpen(finding.id)}>View findings <Icon name="arrow" size={14} /></button></div><p>{finding.claimText}</p><div className="history-card-foot"><span><Icon name="files" size={14} /> 3 source papers</span><span><Icon name="search" size={14} /> {findings.filter((item) => item.claim_id === finding.claim_id).length} evidence passages</span><RelationTag relation={finding.relation} /></div></section></div>)}</div>
    {!groups.length && <div className="empty-state"><strong>No analysis history</strong><p>Run an analysis to see activity here.</p></div>}
  </div>;
}
