import { afterEach, describe, expect, it, vi } from "vitest";
import { createRun, getRunEvents, listRuns } from "./agent";

const runResponse = {
  id: "run_1",
  task: "Inspect files",
  status: "success",
  final_answer: "done",
  error: null,
  created_at: "2026-08-17T00:00:00Z",
  finished_at: "2026-08-17T00:00:01Z",
  steps: []
};

function mockFetch(response: Response) {
  const fetchMock = vi.fn().mockResolvedValue(response);
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("agent api client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("creates a run with a trimmed task and max steps", async () => {
    const fetchMock = mockFetch(Response.json(runResponse));

    await expect(createRun("  Inspect files  ", 6)).resolves.toEqual(runResponse);

    expect(fetchMock).toHaveBeenCalledWith("/api/agent/runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ task: "Inspect files", max_steps: 6 })
    });
  });

  it("rejects blank run tasks before calling the backend", async () => {
    const fetchMock = mockFetch(Response.json(runResponse));

    await expect(createRun("   ")).rejects.toThrow("Task is required.");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("throws backend detail when a request fails", async () => {
    mockFetch(Response.json({ detail: "Task is required." }, { status: 422, statusText: "Unprocessable Entity" }));

    await expect(listRuns()).rejects.toThrow("Task is required.");
  });

  it("parses SSE data lines into run events", async () => {
    const event = {
      run_id: "run_1",
      event_type: "status_change",
      sequence: 1,
      payload: { status: "running" },
      created_at: "2026-08-17T00:00:00Z"
    };
    mockFetch(new Response(`event: status_change\ndata: ${JSON.stringify(event)}\n\n`));

    await expect(getRunEvents("run_1")).resolves.toEqual([event]);
  });
});
