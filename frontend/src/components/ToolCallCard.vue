<script lang="ts">
const TOOL_PAYLOAD_KEYS = new Set(["tool_name", "status", "tool_input", "tool_output", "error"]);

export function getPayloadValue(payload: Record<string, unknown>, key: string): unknown {
  if (!TOOL_PAYLOAD_KEYS.has(key)) {
    return undefined;
  }

  return Object.prototype.hasOwnProperty.call(payload, key) ? payload[key] : undefined;
}

export function getPayloadString(payload: Record<string, unknown>, key: string, fallback: string): string {
  const value = getPayloadValue(payload, key);
  return typeof value === "string" && value.trim().length > 0 ? value : fallback;
}

export function toPrettyJson(value: unknown): string {
  return JSON.stringify(value, null, 2);
}
</script>

<script setup lang="ts">
import type { RunEvent } from "../types/agent";

defineProps<{
  event: RunEvent;
}>();
</script>

<template>
  <article class="tool-call-card" aria-label="Tool call">
    <div class="tool-call-header">
      <div>
        <span class="detail-label">Tool</span>
        <h3>{{ getPayloadString(event.payload, "tool_name", "Unknown tool") }}</h3>
      </div>
      <span class="status" :class="getPayloadString(event.payload, 'status', 'unknown')">
        {{ getPayloadString(event.payload, "status", "unknown") }}
      </span>
    </div>

    <details v-if="getPayloadValue(event.payload, 'tool_input') !== undefined">
      <summary>Tool input</summary>
      <pre>{{ toPrettyJson(getPayloadValue(event.payload, "tool_input")) }}</pre>
    </details>

    <details v-if="getPayloadValue(event.payload, 'tool_output') !== undefined">
      <summary>Tool output</summary>
      <pre>{{ toPrettyJson(getPayloadValue(event.payload, "tool_output")) }}</pre>
    </details>

    <p v-if="getPayloadValue(event.payload, 'error')" class="tool-error">
      {{ getPayloadString(event.payload, "error", "Tool call failed.") }}
    </p>
  </article>
</template>
