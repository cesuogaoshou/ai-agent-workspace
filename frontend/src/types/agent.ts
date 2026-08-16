export type RunStatus = "running" | "success" | "failed";

export interface RunEvent {
  run_id: string;
  event_type: "status_change" | "tool_call" | "final_answer" | string;
  sequence: number;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface AgentRun {
  id: string;
  task: string;
  status: RunStatus | string;
  final_answer: string | null;
  error: string | null;
  created_at: string;
  finished_at: string | null;
  steps: RunEvent[];
}

export interface RunSummary {
  id: string;
  task: string;
  status: RunStatus | string;
  final_answer: string | null;
  error: string | null;
  created_at: string;
  finished_at: string | null;
  step_count: number;
  tool_call_count: number;
}

export interface RunListResponse {
  items: RunSummary[];
}
