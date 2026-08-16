<script lang="ts">
const PRIVATE_PAYLOAD_KEY_PATTERN = /(chain[_-]?of[_-]?thought|private[_-]?reasoning|reasoning|thought)/i;

export function publicFallbackPayload(payload: Record<string, unknown>): Record<string, unknown> {
  return Object.fromEntries(
    Object.entries(payload).filter(([key]) => !PRIVATE_PAYLOAD_KEY_PATTERN.test(key))
  );
}
</script>

<script setup lang="ts">
import { computed } from "vue";
import type { RunEvent } from "../types/agent";
import ToolCallCard from "./ToolCallCard.vue";

const props = defineProps<{
  events: RunEvent[];
  loading: boolean;
  error: string | null;
}>();

const orderedEvents = computed(() => [...props.events].sort((left, right) => left.sequence - right.sequence));

function payloadString(payload: Record<string, unknown>, key: string, fallback: string): string {
  const value = payload[key];
  return typeof value === "string" && value.trim().length > 0 ? value : fallback;
}
</script>

<template>
  <section class="panel timeline-panel" aria-labelledby="timeline-heading">
    <div class="panel-header">
      <div>
        <p class="section-label">Event Timeline</p>
        <h2 id="timeline-heading">Public execution events</h2>
      </div>
      <span class="count">{{ orderedEvents.length }}</span>
    </div>

    <p v-if="loading" class="empty-state">Loading events...</p>
    <p v-else-if="error" class="error-message" role="alert">{{ error }}</p>
    <p v-else-if="orderedEvents.length === 0" class="empty-state">No public trace events for this run.</p>

    <ol v-else class="timeline">
      <li v-for="event in orderedEvents" :key="`${event.run_id}-${event.sequence}`" class="timeline-event">
        <div class="event-marker">{{ event.sequence }}</div>
        <div class="event-body">
          <div class="event-topline">
            <span class="event-type">{{ event.event_type }}</span>
            <time :datetime="event.created_at">{{ event.created_at }}</time>
          </div>

          <div v-if="event.event_type === 'status_change'" class="event-content">
            <p>
              Status changed to
              <span class="inline-strong">{{ payloadString(event.payload, "status", "unknown") }}</span>
            </p>
            <p v-if="payloadString(event.payload, 'error', '')" class="event-error">
              {{ payloadString(event.payload, "error", "") }}
            </p>
          </div>

          <ToolCallCard v-else-if="event.event_type === 'tool_call'" :event="event" />

          <div v-else-if="event.event_type === 'final_answer'" class="event-content">
            <p>{{ payloadString(event.payload, "final_answer", "Final answer recorded.") }}</p>
          </div>

          <div v-else class="event-content">
            <p>Public event recorded.</p>
            <details>
              <summary>Payload</summary>
              <pre>{{ JSON.stringify(publicFallbackPayload(event.payload), null, 2) }}</pre>
            </details>
          </div>
        </div>
      </li>
    </ol>
  </section>
</template>
