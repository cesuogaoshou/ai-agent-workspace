<script lang="ts">
export function formatDateTime(value: string | null): string {
  if (!value) {
    return "Not finished";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit"
  }).format(date);
}

export function displayError(error: string | null): string {
  const firstLine = error?.split(/\r?\n/).find((line) => line.trim().length > 0);
  return firstLine?.trim() || "Agent run failed.";
}

export function finalAnswerText(finalAnswer: string | null): string {
  return finalAnswer ?? "This run has not produced a final answer yet.";
}
</script>

<script setup lang="ts">
import type { AgentRun } from "../types/agent";

defineProps<{
  run: AgentRun | null;
}>();
</script>

<template>
  <section v-if="run" class="panel detail-panel" aria-labelledby="detail-heading">
    <div class="panel-header">
      <div>
        <p class="section-label">Run Detail</p>
        <h2 id="detail-heading">{{ run.id }}</h2>
      </div>
      <span class="status" :class="run.status">{{ run.status }}</span>
    </div>

    <div class="detail-grid">
      <div>
        <span class="detail-label">Run id</span>
        <p class="mono-text">{{ run.id }}</p>
      </div>
      <div>
        <span class="detail-label">Created</span>
        <p>{{ formatDateTime(run.created_at) }}</p>
      </div>
      <div>
        <span class="detail-label">Finished</span>
        <p>{{ formatDateTime(run.finished_at) }}</p>
      </div>
    </div>

    <div class="answer-block">
      <span class="detail-label">Task</span>
      <p>{{ run.task }}</p>
    </div>

    <div v-if="run.status === 'failed' || run.error" class="answer-block error-block">
      <span class="detail-label">Error</span>
      <p>{{ displayError(run.error) }}</p>
    </div>

    <div class="answer-block">
      <span class="detail-label">Final answer</span>
      <p>{{ finalAnswerText(run.final_answer) }}</p>
    </div>
  </section>

  <section v-else class="panel detail-panel empty-detail" aria-labelledby="detail-heading">
    <p class="section-label">Run Detail</p>
    <h2 id="detail-heading">Select a run</h2>
    <p>No run is selected yet.</p>
  </section>
</template>
