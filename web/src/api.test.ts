import { afterEach, describe, expect, it, vi } from "vitest";
import { api, ApiError } from "./api";

afterEach(() => vi.unstubAllGlobals());

describe("typed API adapter", () => {
  it("returns the health contract in live mode", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ status: "ok", version: "0.1.0", mode: "local_development" }), { status: 200 })));
    await expect(api.health()).resolves.toMatchObject({ status: "ok", version: "0.1.0" });
  });

  it("creates a project and scopes document listing and uploads to it", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ id: "project-1", name: "Study", description: null, created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z" }), { status: 201 }));
    vi.stubGlobal("fetch", fetchMock);
    await expect(api.createProject("Study")).resolves.toMatchObject({ id: "project-1" });
    expect(fetchMock).toHaveBeenCalledWith("/api/projects", expect.objectContaining({ method: "POST" }));
    fetchMock.mockResolvedValueOnce(new Response("[]", { status: 200 }));
    await expect(api.documents("project-1")).resolves.toEqual([]);
    expect(fetchMock).toHaveBeenLastCalledWith("/api/documents?project_id=project-1", undefined);
  });

  it("surfaces a missing live route without substituting demo data", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "Not Found" }), { status: 404 })));
    await expect(api.documents("project-1")).rejects.toBeInstanceOf(ApiError);
    await expect(api.documents("project-1")).rejects.toThrow("This API route is not implemented by the current backend.");
  });

  it("shows structured backend validation messages", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: { code: "invalid", message: "Choose a supported file." } }), { status: 415 })));
    await expect(api.projects()).rejects.toThrow("Choose a supported file.");
  });

  it("surfaces network failures for explicit user handling", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("offline")));
    await expect(api.health()).rejects.toThrow("Could not reach the SCOPE API");
  });
});
