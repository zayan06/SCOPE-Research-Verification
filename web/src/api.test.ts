import { afterEach, describe, expect, it, vi } from "vitest";
import { api, ApiError } from "./api";

afterEach(() => vi.unstubAllGlobals());

describe("typed API adapter", () => {
  it("returns the health contract in live mode", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ status: "ok", version: "0.1.0", mode: "local_development" }), { status: 200 })));
    await expect(api.health()).resolves.toMatchObject({ status: "ok", version: "0.1.0" });
  });

  it("surfaces a missing live route without substituting demo data", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "Not Found" }), { status: 404 })));
    await expect(api.documents()).rejects.toBeInstanceOf(ApiError);
    await expect(api.documents()).rejects.toThrow("This API route is not implemented by the current backend.");
  });

  it("surfaces network failures for explicit user handling", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("offline")));
    await expect(api.health()).rejects.toThrow("Could not reach the SCOPE API");
  });
});
