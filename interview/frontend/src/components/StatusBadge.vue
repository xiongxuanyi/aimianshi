<template>
  <span class="badge" :class="conf.cls">
    <span class="dot"></span>{{ conf.label }}
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { InterviewStatus } from '../types'

const props = defineProps<{ status: InterviewStatus }>()

const MAP: Record<InterviewStatus, { label: string; cls: string }> = {
  pending: { label: '待参加', cls: 'badge-pending' },
  evaluating: { label: '评分中', cls: 'badge-waiting' },
  reported: { label: '已出报告', cls: 'badge-done' },
}

const conf = computed(() => MAP[props.status])
</script>

<style scoped>
.badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 24px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  line-height: 1;
  white-space: nowrap;
}
.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}
.badge-pending {
  background: var(--info-bg);
  color: var(--info);
}
.badge-waiting {
  background: var(--warning-bg);
  color: var(--warning);
}
.badge-done {
  background: var(--success-bg);
  color: var(--success);
}
</style>
