<script setup lang="ts">
import type { RunSummary } from "./types/agent";

interface TimelineEvent {
  sequence: number;
  eventType: "status_change" | "tool_call" | "final_answer";
  title: string;
  detail: string;
  timestamp: string;
}

const sampleRuns: RunSummary[] = [
  {
    id: "run_3",
    task: "Summarize workspace trace requirements",
    status: "success",
    final_answer: "The selected run detail will show the backend final answer, status, timestamps, and public trace events.",
    error: null,
    created_at: "10:42",
    finished_at: "10:42",
    step_count: 4,
    tool_call_count: 1
  },
  {
    id: "run_2",
    task: "Read sample.md and report key facts",
    status: "failed",
    final_answer: null,
    error: "Sample backend error",
    created_at: "10:17",
    finished_at: "10:18",
    step_count: 3,
    tool_call_count: 1
  },
  {
    id: "run_1",
    task: "Calculate 29 * 3",
    status: "success",
    final_answer: "87",
    error: null,
    created_at: "09:58",
    finished_at: "09:59",
    step_count: 5,
    tool_call_count: 2
  }
];

const timelineEvents: TimelineEvent[] = [
  {
    sequence: 1,
    eventType: "status_change",
    title: "Run started",
    detail: "The agent accepted the task and entered the execution loop.",
    timestamp: "10:42:01"
  },
  {
    sequence: 2,
    eventType: "tool_call",
    title: "Tool call: file_reader",
    detail: "Input and output payloads will expand here in the trace UI.",
    timestamp: "10:42:03"
  },
  {
    sequence: 3,
    eventType: "final_answer",
    title: "Final answer",
    detail: "The backend response final answer will render here.",
    timestamp: "10:42:05"
  }
];
</script>

<template>
  <main class="workspace-shell" aria-label="AI Agent Workspace">
    <aside class="sidebar" aria-label="Run controls">
      <section class="panel composer-panel" aria-labelledby="composer-heading">
        <div>
          <p class="section-label">Task Composer</p>
          <h1 id="composer-heading">AI Agent Workspace</h1>
        </div>

        <label class="field-label" for="task">Task</label>
        <textarea
          id="task"
          rows="6"
          placeholder="Ask the agent to inspect files, call tools, or explain a trace."
        ></textarea>

        <div class="composer-actions">
          <label class="step-field" for="max-steps">
            <span>Max steps</span>
            <input id="max-steps" type="number" min="1" max="20" value="6" />
          </label>
          <button type="button">Create run</button>
        </div>
      </section>

      <section class="panel run-list-panel" aria-labelledby="runs-heading">
        <div class="panel-header">
          <div>
            <p class="section-label">Run List</p>
            <h2 id="runs-heading">Recent runs</h2>
          </div>
          <span class="count">{{ sampleRuns.length }}</span>
        </div>

        <ol class="run-list">
          <li
            v-for="run in sampleRuns"
            :key="run.id"
            class="run-item"
            :class="{ selected: run.id === 'run_3' }"
          >
            <div class="run-item-top">
              <span class="run-id">{{ run.id }}</span>
              <span class="status" :class="run.status">{{ run.status }}</span>
            </div>
            <p>{{ run.task }}</p>
            <div class="run-meta">
              <span>{{ run.created_at }}</span>
              <span>{{ run.step_count }} steps</span>
              <span>{{ run.tool_call_count }} tools</span>
            </div>
          </li>
        </ol>
      </section>
    </aside>

    <section class="main-pane" aria-label="Run detail">
      <section class="panel detail-panel" aria-labelledby="detail-heading">
        <div class="panel-header">
          <div>
            <p class="section-label">Run Detail</p>
            <h2 id="detail-heading">run_3</h2>
          </div>
          <span class="status success">success</span>
        </div>

        <div class="detail-grid">
          <div>
            <span class="detail-label">Task</span>
            <p>Summarize workspace trace requirements</p>
          </div>
          <div>
            <span class="detail-label">Created</span>
            <p>10:42</p>
          </div>
          <div>
            <span class="detail-label">Finished</span>
            <p>10:42</p>
          </div>
        </div>

        <div class="answer-block">
          <span class="detail-label">Final answer</span>
          <p>The selected run detail will show the backend final answer, status, timestamps, and public trace events.</p>
        </div>
      </section>

      <section class="panel timeline-panel" aria-labelledby="timeline-heading">
        <div class="panel-header">
          <div>
            <p class="section-label">Event Timeline</p>
            <h2 id="timeline-heading">Public execution events</h2>
          </div>
        </div>

        <ol class="timeline">
          <li v-for="event in timelineEvents" :key="event.sequence" class="timeline-event">
            <div class="event-marker">{{ event.sequence }}</div>
            <div class="event-body">
              <div class="event-topline">
                <span class="event-type">{{ event.eventType }}</span>
                <time>{{ event.timestamp }}</time>
              </div>
              <h3>{{ event.title }}</h3>
              <p>{{ event.detail }}</p>
            </div>
          </li>
        </ol>
      </section>
    </section>
  </main>
</template>
