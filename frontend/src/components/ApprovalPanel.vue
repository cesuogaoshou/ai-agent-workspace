<script lang="ts">
import type { PendingApproval, RunEvent } from "../types/agent";

export function pendingApprovalFromEvents(events: RunEvent[]): PendingApproval | null {
  const latest = [...events]
    .sort((left, right) => right.sequence - left.sequence)
    .find((event) => event.event_type === "approval_required");

  if (!latest) {
    return null;
  }

  const payload = latest.payload;
  if (
    typeof payload.approval_id !== "string" ||
    typeof payload.tool_name !== "string" ||
    typeof payload.tool_call_id !== "string" ||
    typeof payload.step_number !== "number"
  ) {
    return null;
  }

  return {
    approval_id: payload.approval_id,
    step_number: payload.step_number,
    tool_call_id: payload.tool_call_id,
    tool_name: payload.tool_name,
    tool_input: typeof payload.tool_input === "object" && payload.tool_input !== null ? payload.tool_input : null
  };
}
</script>

<script setup lang="ts">
defineProps<{
  approval: PendingApproval | null;
  deciding: boolean;
  error: string | null;
}>();

defineEmits<{
  approve: [];
  reject: [reason: string];
}>();
</script>

<template>
  <section v-if="approval" class="panel approval-panel" aria-labelledby="approval-heading">
    <div class="panel-header">
      <div>
        <p class="section-label">Human Approval</p>
        <h2 id="approval-heading">Sensitive tool call</h2>
      </div>
      <span class="status waiting_for_approval">waiting</span>
    </div>

    <div class="approval-summary">
      <span class="detail-label">Tool</span>
      <p class="mono-text">{{ approval.tool_name }}</p>
    </div>

    <details>
      <summary>Tool input</summary>
      <pre>{{ JSON.stringify(approval.tool_input, null, 2) }}</pre>
    </details>

    <p v-if="error" class="error-message" role="alert">{{ error }}</p>

    <div class="approval-actions">
      <button type="button" :disabled="deciding" @click="$emit('approve')">Approve</button>
      <button type="button" class="secondary-button danger-button" :disabled="deciding" @click="$emit('reject', '')">
        Reject
      </button>
    </div>
  </section>
</template>
