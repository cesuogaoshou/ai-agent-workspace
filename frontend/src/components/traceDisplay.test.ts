import { describe, expect, it } from "vitest";
import ApprovalPanel, { pendingApprovalFromEvents } from "./ApprovalPanel.vue";
import EventTimeline, { eventPayloadJson } from "./EventTimeline.vue";
import RunDetail, { displayError, finalAnswerText, formatDateTime } from "./RunDetail.vue";
import ToolCallCard, { getPayloadString, getPayloadValue } from "./ToolCallCard.vue";

describe("trace display components", () => {
  it("exposes the run detail and timeline components", () => {
    expect(RunDetail).toBeTruthy();
    expect(EventTimeline).toBeTruthy();
    expect(ToolCallCard).toBeTruthy();
    expect(ApprovalPanel).toBeTruthy();
  });

  it("formats missing and invalid timestamps safely", () => {
    expect(formatDateTime(null)).toBe("Not finished");
    expect(formatDateTime("not-a-date")).toBe("not-a-date");
  });

  it("uses sanitized failed-run error text", () => {
    expect(displayError("Agent run failed.\ninternal detail")).toBe("Agent run failed.");
    expect(displayError(null)).toBe("Agent run failed.");
  });

  it("formats final answer text independently from failed-run errors", () => {
    expect(finalAnswerText("partial answer")).toBe("partial answer");
    expect(finalAnswerText(null)).toBe("This run has not produced a final answer yet.");
  });

  it("reads only known public tool payload fields", () => {
    const payload = {
      tool_name: "calculator",
      tool_input: { expression: "40 + 2" },
      private_reasoning: "do not render"
    };

    expect(getPayloadValue(payload, "tool_name")).toBe("calculator");
    expect(getPayloadString(payload, "tool_name", "Unknown tool")).toBe("calculator");
    expect(getPayloadValue(payload, "private_reasoning")).toBeUndefined();
  });

  it("serializes unknown public event payloads as received from the backend", () => {
    const payload = {
      message: "visible",
      backend_field: { nested: true }
    };

    expect(eventPayloadJson(payload)).toBe(JSON.stringify(payload, null, 2));
  });

  it("extracts the latest approval request from public events", () => {
    const approval = pendingApprovalFromEvents([
      {
        run_id: "run_1",
        event_type: "approval_required",
        sequence: 2,
        payload: {
          approval_id: "approval_1",
          step_number: 1,
          tool_call_id: "call_1",
          tool_name: "sensitive_echo",
          tool_input: { value: "hello" }
        },
        created_at: "2026-08-24T00:00:00Z"
      }
    ]);

    expect(approval).toEqual({
      approval_id: "approval_1",
      step_number: 1,
      tool_call_id: "call_1",
      tool_name: "sensitive_echo",
      tool_input: { value: "hello" }
    });
  });
});
