<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { approveRun, createRun, getRun, getRunEvents, listRuns, rejectRun } from "./api/agent";
import ApprovalPanel, { pendingApprovalFromEvents } from "./components/ApprovalPanel.vue";
import EventTimeline from "./components/EventTimeline.vue";
import RunDetail from "./components/RunDetail.vue";
import RunComposer from "./components/RunComposer.vue";
import RunList from "./components/RunList.vue";
import type { AgentRun, RunEvent, RunSummary } from "./types/agent";

const runs = ref<RunSummary[]>([]);
const selectedRun = ref<AgentRun | null>(null);
const events = ref<RunEvent[]>([]);
const loadingRuns = ref(false);
const loadingEvents = ref(false);
const submitting = ref(false);
const decidingApproval = ref(false);
const error = ref<string | null>(null);
const eventsError = ref<string | null>(null);
const approvalError = ref<string | null>(null);
const latestSelectionRunId = ref<string | null>(null);

const pendingApproval = computed(() => {
  if (!selectedRun.value || selectedRun.value.status !== "waiting_for_approval") {
    return null;
  }
  return selectedRun.value.pending_approval ?? pendingApprovalFromEvents(events.value);
});

function sortNewestFirst(items: RunSummary[]): RunSummary[] {
  return [...items].sort((left, right) => Date.parse(right.created_at) - Date.parse(left.created_at));
}

async function selectRun(run: RunSummary) {
  latestSelectionRunId.value = run.id;
  error.value = null;
  eventsError.value = null;
  loadingEvents.value = true;

  try {
    const loadedRun = await getRun(run.id);
    if (latestSelectionRunId.value === run.id) {
      selectedRun.value = loadedRun;
      events.value = loadedRun.steps;
    }
  } catch (caught) {
    if (latestSelectionRunId.value === run.id) {
      error.value = caught instanceof Error ? caught.message : "Failed to load run.";
      events.value = [];
      loadingEvents.value = false;
    }
    return;
  }

  try {
    const loadedEvents = await getRunEvents(run.id);
    if (latestSelectionRunId.value === run.id) {
      events.value = loadedEvents;
    }
  } catch (caught) {
    if (latestSelectionRunId.value === run.id) {
      eventsError.value = caught instanceof Error ? caught.message : "Failed to load events.";
    }
  } finally {
    if (latestSelectionRunId.value === run.id) {
      loadingEvents.value = false;
    }
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
      latestSelectionRunId.value = null;
      selectedRun.value = null;
      events.value = [];
      eventsError.value = null;
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
    latestSelectionRunId.value = createdRun.id;
    eventsError.value = null;
    loadingEvents.value = false;
    selectedRun.value = createdRun;
    events.value = createdRun.steps;
    await loadRuns(createdRun.id);
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : "Failed to create run.";
  } finally {
    submitting.value = false;
  }
}

async function refreshRun(runId: string) {
  const summary = runs.value.find((run) => run.id === runId);
  if (summary) {
    await selectRun(summary);
    return;
  }
  await loadRuns(runId);
}

async function approvePendingRun() {
  if (!selectedRun.value || !pendingApproval.value) {
    return;
  }
  decidingApproval.value = true;
  approvalError.value = null;

  try {
    const updated = await approveRun(selectedRun.value.id, pendingApproval.value.approval_id);
    selectedRun.value = updated;
    events.value = updated.steps;
    await loadRuns(updated.id);
  } catch (caught) {
    approvalError.value = caught instanceof Error ? caught.message : "Failed to approve run.";
    await refreshRun(selectedRun.value.id);
  } finally {
    decidingApproval.value = false;
  }
}

async function rejectPendingRun(reason: string) {
  if (!selectedRun.value || !pendingApproval.value) {
    return;
  }
  decidingApproval.value = true;
  approvalError.value = null;

  try {
    const updated = await rejectRun(selectedRun.value.id, pendingApproval.value.approval_id, reason);
    selectedRun.value = updated;
    events.value = updated.steps;
    await loadRuns(updated.id);
  } catch (caught) {
    approvalError.value = caught instanceof Error ? caught.message : "Failed to reject run.";
    await refreshRun(selectedRun.value.id);
  } finally {
    decidingApproval.value = false;
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
      <RunDetail :run="selectedRun" />
      <ApprovalPanel
        :approval="pendingApproval"
        :deciding="decidingApproval"
        :error="approvalError"
        @approve="approvePendingRun"
        @reject="rejectPendingRun"
      />
      <EventTimeline :events="selectedRun ? events : []" :loading="loadingEvents" :error="eventsError" />
    </section>
  </main>
</template>
