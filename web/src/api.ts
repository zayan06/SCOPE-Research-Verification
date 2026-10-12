import type { AnalyzeRequest, AnalyzeResponse, DocumentSummary, DocumentUploadResponse, HealthResponse, ProjectResponse } from "./contracts";

const apiBase = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "") ?? "";
export class ApiError extends Error {
  constructor(message: string, readonly status?: number) {
    super(message);
    this.name = "ApiError";
  }
}
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${apiBase}${path}`, init);
  } catch {
    throw new ApiError("Could not reach the SCOPE API. Check that the backend is running and the API URL is correct.");
  }
  if (!response.ok) {
    let detail = response.status === 404
      ? "This API route is not implemented by the current backend."
      : `Request failed (${response.status})`;
    try {
      const body: unknown = await response.json();
      if (response.status !== 404 && body && typeof body === "object" && "message" in body && typeof body.message === "string") detail = body.message;
      else if (response.status !== 404 && body && typeof body === "object" && "detail" in body) {
        const nested = body.detail;
        if (typeof nested === "string") detail = nested;
        else if (nested && typeof nested === "object" && "message" in nested && typeof nested.message === "string") detail = nested.message;
      }
    } catch { /* keep the status based message */ }
    throw new ApiError(detail, response.status);
  }
  return response.json() as Promise<T>;
}
export const api = {
  health: () => request<HealthResponse>("/api/health"),
  projects: () => request<ProjectResponse[]>("/api/projects"),
  createProject: (name: string) => request<ProjectResponse>("/api/projects", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name }),
  }),
  documents: (projectId: string) => request<DocumentSummary[]>(`/api/documents?project_id=${encodeURIComponent(projectId)}`),
  upload: (file: File, projectId: string, onProgress?: (percent: number) => void): Promise<DocumentUploadResponse> => {
    // XMLHttpRequest exposes upload progress while keeping the response typed.
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("POST", `${apiBase}/api/documents`);
      xhr.responseType = "json";
      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable) onProgress?.(Math.round((event.loaded / event.total) * 100));
      };
      xhr.onerror = () => reject(new ApiError("Could not reach the SCOPE API during upload."));
      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) resolve(xhr.response as DocumentUploadResponse);
        else {
          const detail = xhr.response?.message ?? xhr.response?.detail?.message ?? xhr.response?.detail;
          reject(new ApiError(typeof detail === "string" ? detail : (xhr.status === 404 ? "Document upload is not implemented by the current backend." : `Upload failed (${xhr.status})`), xhr.status));
        }
      };
      const body = new FormData();
      body.append("file", file);
      body.append("project_id", projectId);
      xhr.send(body);
    });
  },
  analyze: (payload: AnalyzeRequest) => request<AnalyzeResponse>("/api/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  }),
};
export const configuredApiBase = apiBase || "(same origin)";
