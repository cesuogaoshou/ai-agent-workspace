<script setup lang="ts">
import { computed, ref } from "vue";

const props = defineProps<{
  submitting: boolean;
  error: string | null;
}>();

const emit = defineEmits<{
  submit: [payload: { task: string; maxSteps?: number }];
}>();

const task = ref("");
const maxSteps = ref<number | string | null>(null);

const isBlank = computed(() => task.value.trim().length === 0);
const canSubmit = computed(() => !props.submitting && !isBlank.value);

function submitRun() {
  if (!canSubmit.value) {
    return;
  }

  const numericMaxSteps = typeof maxSteps.value === "number" && Number.isFinite(maxSteps.value) ? maxSteps.value : undefined;

  const payload: { task: string; maxSteps?: number } = { task: task.value };
  if (numericMaxSteps !== undefined) {
    payload.maxSteps = numericMaxSteps;
  }

  emit("submit", payload);
}
</script>

<template>
  <form class="panel composer-panel" aria-labelledby="composer-heading" @submit.prevent="submitRun">
    <div>
      <p class="section-label">Task Composer</p>
      <h1 id="composer-heading">AI Agent Workspace</h1>
    </div>

    <label class="field-label" for="task">Task</label>
    <textarea
      id="task"
      v-model="task"
      rows="6"
      placeholder="Ask the agent to inspect files, call tools, or explain a trace."
    ></textarea>

    <div class="composer-actions">
      <label class="step-field" for="max-steps">
        <span>Max steps</span>
        <input id="max-steps" v-model.number="maxSteps" type="number" min="1" max="20" placeholder="6" />
      </label>
      <button type="submit" :disabled="!canSubmit">
        {{ submitting ? "Creating..." : "Create run" }}
      </button>
    </div>

    <p v-if="error" class="error-message" role="alert">{{ error }}</p>
  </form>
</template>
