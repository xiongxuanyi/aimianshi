<template>
  <div class="card interview-card">
    <div class="ic-company" :style="{ background: interview.companyGradient }">
      {{ interview.companyInitial }}
    </div>

    <div class="ic-main">
      <h3>{{ interview.position }}</h3>
      <div class="meta">
        <span>🏢 {{ interview.company }}</span>
        <span>🤖 AI 面试官</span>
        <span>📝 {{ interview.questionCount }} 题</span>
        <span>⏱️ {{ interview.duration }}</span>
      </div>
    </div>

    <div class="ic-side">
      <StatusBadge :status="interview.status" />
      <div class="expire">{{ subText }}</div>
      <el-button
        v-if="interview.status === 'pending'"
        type="primary"
        @click="$emit('enter', interview)"
      >
        进入面试
      </el-button>
      <el-button v-else-if="interview.status === 'evaluating'" disabled>评分中…</el-button>
      <el-button v-else @click="$emit('view-result', interview)">查看结果</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Interview } from '../types'
import StatusBadge from './StatusBadge.vue'

const props = defineProps<{ interview: Interview }>()
defineEmits<{ (e: 'enter', interview: Interview): void; (e: 'view-result', interview: Interview): void }>()

const subText = computed(() =>
  props.interview.status === 'pending'
    ? `邀请有效期至 ${props.interview.expireTime}`
    : `提交于 ${props.interview.submittedAt}`,
)
</script>

<style scoped>
.interview-card {
  padding: 20px 22px;
  display: flex;
  align-items: center;
  gap: 18px;
  transition: box-shadow 0.18s, transform 0.18s, border-color 0.18s;
}
.interview-card:hover {
  box-shadow: var(--shadow-md);
  border-color: var(--brand-100);
  transform: translateY(-1px);
}
.ic-company {
  width: 46px;
  height: 46px;
  border-radius: 12px;
  flex-shrink: 0;
  display: grid;
  place-items: center;
  font-size: 20px;
  font-weight: 700;
  color: #fff;
}
.ic-main {
  flex: 1;
  min-width: 0;
}
.ic-main h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
}
.meta {
  margin-top: 4px;
  font-size: 13px;
  color: var(--ink-500);
  display: flex;
  flex-wrap: wrap;
  gap: 6px 16px;
}
.meta span {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}
.ic-side {
  text-align: right;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 10px;
  flex-shrink: 0;
}
.expire {
  font-size: 11px;
  color: var(--ink-400);
}
</style>
