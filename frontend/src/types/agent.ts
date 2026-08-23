export type RunStatus = "running" | "waiting_for_approval" | "success" | "failed" | "rejected";

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
  pending_approval: PendingApproval | null;
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

export interface PendingApproval {
  approval_id: string;
  step_number: number;
  tool_call_id: string;
  tool_name: string;
  tool_input: unknown;
}
