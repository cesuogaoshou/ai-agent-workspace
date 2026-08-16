<script setup lang="ts">
import { onMounted, ref } from "vue";
import { createRun, getRun, listRuns } from "./api/agent";
import RunComposer from "./components/RunComposer.vue";
import RunList from "./components/RunList.vue";
import type { AgentRun, RunSummary } from "./types/agent";

const runs = ref<RunSummary[]>([]);
const selectedRun = ref<AgentRun | null>(null);
const loadingRuns = ref(false);
const submitting = ref(false);
const error = ref<string | null>(null);

function sortNewestFirst(items: RunSummary[]): RunSummary[] {
  return [...items].sort((left, right) => Date.parse(right.created_at) - Date.parse(left.created_at));
}

function formatDate(value: string | null): string {
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
    minute: "2-digit"
  }).format(date);
}

async function selectRun(run: RunSummary) {
  error.value = null;
  try {
    selectedRun.value = await getRun(run.id);
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : "Failed to load run.";
  }
}

async function loadRuns(preferredRunId?: string) {
  loadingRuns.value = true;
  error.value = null;

  try {
    const response = await listRuns();
    const sortedRuns = sortNewestFirst(response.items);
    runs.value = sortedRuns;

    const currentId = preferredRunId ?? selectedRun.value?.id;
    const nextSelection = sortedRuns.find((run) => run.id === currentId) ?? sortedRuns[0];
    if (nextSelection) {
      await selectRun(nextSelection);
    } else {
      selectedRun.value = null;
    }
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : "Failed to load runs.";
  } finally {
    loadingRuns.value = false;
  }
}

async function submitRun(payload: { task: string; maxSteps?: number }) {
  submitting.value = true;
  error.value = null;

  try {
    const createdRun = await createRun(payload.task, payload.maxSteps);
    selectedRun.value = createdRun;
    await loadRuns(createdRun.id);
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : "Failed to create run.";
  } finally {
    submitting.value = false;
  }
}

onMounted(() => {
  void loadRuns();
});
</script>

<template>
  <main class="workspace-shell" aria-label="AI Agent Workspace">
    <aside class="sidebar" aria-label="Run controls">
      <RunComposer :submitting="submitting" :error="error" @submit="submitRun" />
      <RunList :runs="runs" :selected-run-id="selectedRun?.id ?? null" :loading="loadingRuns" @select="selectRun" />
    </aside>

    <section class="main-pane" aria-label="Run detail">
      <section v-if="selectedRun" class="panel detail-panel" aria-labelledby="detail-heading">
        <div class="panel-header">
          <div>
            <p class="section-label">Run Detail</p>
            <h2 id="detail-heading">{{ selectedRun.id }}</h2>
          </div>
          <span class="status" :class="selectedRun.status">{{ selectedRun.status }}</span>
        </div>

        <div class="detail-grid">
          <div>
            <span class="detail-label">Task</span>
            <p>{{ selectedRun.task }}</p>
          </div>
          <div>
            <span class="detail-label">Created</span>
            <p>{{ formatDate(selectedRun.created_at) }}</p>
          </div>
          <div>
            <span class="detail-label">Finished</span>
            <p>{{ formatDate(selectedRun.finished_at) }}</p>
          </div>
        </div>

        <div class="answer-block">
          <span class="detail-label">{{ selectedRun.error ? "Error" : "Final answer" }}</span>
          <p>{{ selectedRun.error ?? selectedRun.final_answer ?? "This run has not produced a final answer yet." }}</p>
        </div>
      </section>

      <section v-else class="panel detail-panel empty-detail" aria-labelledby="detail-heading">
        <p class="section-label">Run Detail</p>
        <h2 id="detail-heading">Select a run</h2>
        <p>No run is selected yet.</p>
      </section>

      <section class="panel timeline-panel" aria-labelledby="timeline-heading">
        <div class="panel-header">
          <div>
            <p class="section-label">Event Timeline</p>
            <h2 id="timeline-heading">Public execution events</h2>
          </div>
        </div>

        <p class="empty-state">Task 4 will add the selected run event timeline.</p>
      </section>
    </section>
  </main>
</template>
