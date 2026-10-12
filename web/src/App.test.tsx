import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "./App";

afterEach(() => {
  cleanup();
  window.location.hash = "";
});

describe("SCOPE workspace", () => {
  it("navigates from the overview to the document library", () => {
    render(<App />);
    expect(screen.getByRole("heading", { name: "Sleep and memory — example review" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /Documents/ }));
    expect(screen.getByRole("heading", { name: "Document library" })).toBeTruthy();
    expect(screen.getByText("example-source-a.pdf")).toBeTruthy();
  });

  it("filters results by relationship", () => {
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: /Results/ }));
    const relationSelect = screen.getByLabelText("Relationship");
    fireEvent.change(relationSelect, { target: { value: "support" } });
    const table = screen.getByRole("table");
    expect(within(table).getAllByText("Supports").length).toBeGreaterThan(0);
    expect(within(table).queryByText("Qualifies")).toBeNull();
  });

  it("renders the analysis panels and explicit unknown scope fields", () => {
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Analysis workspace" }));
    expect(screen.getByRole("heading", { name: "Source passage" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Scope compatibility" })).toBeTruthy();
    const table = screen.getByRole("table");
    expect(within(table).getByText("Source evidence")).toBeTruthy();
    expect(within(table).getByText("Explanation")).toBeTruthy();
    expect(within(table).getAllByText("Unknown").length).toBeGreaterThan(0);
  });

  it("shows live API errors and requires a deliberate switch to demo", async () => {
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      return Promise.resolve(url.endsWith("/api/health")
        ? new Response(JSON.stringify({ status: "ok", version: "0.1.0", mode: "local_development" }), { status: 200 })
        : new Response(JSON.stringify({ detail: "Not Found" }), { status: 404 }));
    }));
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Switch to live API" }));
    await waitFor(() => expect(screen.getByRole("alert").textContent).toContain("not implemented"));
    expect(screen.getByRole("button", { name: "Enter demo mode" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Enter demo mode" }));
    expect(screen.getByText(/Example documents and findings are synthetic/)).toBeTruthy();
  });

  it("adds a supported file to the explicitly labeled demo library", async () => {
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: /Add documents/ }));
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(["sample"], "new-paper.pdf", { type: "application/pdf" });
    fireEvent.change(fileInput, { target: { files: [file] } });
    fireEvent.click(screen.getByRole("button", { name: "Add to demo library" }));
    await waitFor(() => expect(screen.getByText(/Added to the demo library/)).toBeTruthy(), { timeout: 2500 });
    expect(screen.getByText("new-paper.pdf")).toBeTruthy();
  });
});
