import type { AgentRun, RunEvent, RunListResponse } from "../types/agent";

const API_BASE = "/api";

async function parseErrorMessage(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string" && body.detail.trim().length > 0) {
      return body.detail;
    }
  } catch {
    // Fall back to the HTTP status below when the backend did not send JSON.
  }

  return response.statusText || `Request failed with status ${response.status}`;
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init);
  if (!response.ok) {
    throw new Error(await parseErrorMessage(response));
  }

  return (await response.json()) as T;
}

export async function createRun(task: string, maxSteps?: number): Promise<AgentRun> {
  const trimmedTask = task.trim();
  if (trimmedTask.length === 0) {
    throw new Error("Task is required.");
  }

  const body: { task: string; max_steps?: number } = { task: trimmedTask };
  if (maxSteps !== undefined) {
    body.max_steps = maxSteps;
  }

  return requestJson<AgentRun>("/agent/runs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
}

export function listRuns(): Promise<RunListResponse> {
  return requestJson<RunListResponse>("/agent/runs");
}

export function getRun(runId: string): Promise<AgentRun> {
  return requestJson<AgentRun>(`/agent/runs/${encodeURIComponent(runId)}`);
}

export function approveRun(runId: string, approvalId: string): Promise<AgentRun> {
  return requestJson<AgentRun>(`/agent/runs/${encodeURIComponent(runId)}/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ approval_id: approvalId })
  });
}

export function rejectRun(runId: string, approvalId: string, reason?: string): Promise<AgentRun> {
  const body: { approval_id: string; reason?: string } = { approval_id: approvalId };
  if (reason !== undefined) {
    body.reason = reason;
  }

  return requestJson<AgentRun>(`/agent/runs/${encodeURIComponent(runId)}/reject`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
}

export async function getRunEvents(runId: string): Promise<RunEvent[]> {
  const response = await fetch(`${API_BASE}/agent/runs/${encodeURIComponent(runId)}/events`);
  if (!response.ok) {
    throw new Error(await parseErrorMessage(response));
  }

  const text = await response.text();
  return text
    .split(/\r?\n/)
    .filter((line) => line.startsWith("data:"))
    .map((line) => JSON.parse(line.slice("data:".length).trim()) as RunEvent);
}
