import { describe, expect, it } from "vitest";
import EventTimeline, { publicFallbackPayload } from "./EventTimeline.vue";
import RunDetail, { displayError, formatDateTime } from "./RunDetail.vue";
import ToolCallCard, { getPayloadString, getPayloadValue } from "./ToolCallCard.vue";

describe("trace display components", () => {
  it("exposes the run detail and timeline components", () => {
    expect(RunDetail).toBeTruthy();
    expect(EventTimeline).toBeTruthy();
    expect(ToolCallCard).toBeTruthy();
  });

  it("formats missing and invalid timestamps safely", () => {
    expect(formatDateTime(null)).toBe("Not finished");
    expect(formatDateTime("not-a-date")).toBe("not-a-date");
  });

  it("uses sanitized failed-run error text", () => {
    expect(displayError("Agent run failed.\ninternal detail")).toBe("Agent run failed.");
    expect(displayError(null)).toBe("Agent run failed.");
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

  it("filters reasoning-like fields from unknown event fallback payloads", () => {
    expect(
      publicFallbackPayload({
        message: "visible",
        private_reasoning: "hidden",
        chain_of_thought: "hidden",
        thought: "hidden"
      })
    ).toEqual({ message: "visible" });
  });
});
