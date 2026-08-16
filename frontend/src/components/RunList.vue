<script setup lang="ts">
import type { RunSummary } from "../types/agent";

defineProps<{
  runs: RunSummary[];
  selectedRunId: string | null;
  loading: boolean;
}>();

const emit = defineEmits<{
  select: [run: RunSummary];
}>();

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  }).format(date);
}
</script>

<template>
  <section class="panel run-list-panel" aria-labelledby="runs-heading">
    <div class="panel-header">
      <div>
        <p class="section-label">Run List</p>
        <h2 id="runs-heading">Recent runs</h2>
      </div>
      <span class="count">{{ runs.length }}</span>
    </div>

    <p v-if="loading" class="empty-state">Loading runs...</p>
    <p v-else-if="runs.length === 0" class="empty-state">No runs yet.</p>

    <ol v-else class="run-list">
      <li v-for="run in runs" :key="run.id">
        <button
          type="button"
          class="run-item"
          :class="{ selected: run.id === selectedRunId }"
          :aria-pressed="run.id === selectedRunId"
          @click="emit('select', run)"
        >
          <span class="run-item-top">
            <span class="run-id">{{ run.id }}</span>
            <span class="status" :class="run.status">{{ run.status }}</span>
          </span>
          <span class="run-task">{{ run.task }}</span>
          <span class="run-meta">
            <span>{{ formatDate(run.created_at) }}</span>
            <span>{{ run.step_count }} steps</span>
            <span>{{ run.tool_call_count }} tools</span>
          </span>
        </button>
      </li>
    </ol>
  </section>
</template>
