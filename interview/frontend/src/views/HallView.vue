<template>
  <div>
    <div class="page-head">
      <h1>你好，{{ auth.userName || '候选人' }} 👋</h1>
      <p>这是你收到的面试邀请，点击「进入面试」即可开始。</p>
    </div>

    <div class="stat-row">
      <div class="stat"><div class="num blue">{{ stats.pending }}</div><div class="lbl">待参加</div></div>
      <div class="stat"><div class="num amber">{{ stats.evaluating }}</div><div class="lbl">评分中</div></div>
      <div class="stat"><div class="num green">{{ stats.reported }}</div><div class="lbl">已出报告</div></div>
      <div class="stat"><div class="num">{{ stats.total }}</div><div class="lbl">全部邀请</div></div>
    </div>

    <h2 class="section-title">📋 我的面试</h2>
    <div v-loading="store.loading" class="interview-list">
      <InterviewCard
        v-for="item in store.list"
        :key="item.id"
        :interview="item"
        @enter="onEnter"
        @view-result="onViewResult"
      />
      <el-empty v-if="!store.loading && store.list.length === 0" description="暂无面试邀请" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import type { Interview } from '../types'
import InterviewCard from '../components/InterviewCard.vue'
import { useAuthStore } from '../stores/auth'
import { useInterviewStore } from '../stores/interview'

const auth = useAuthStore()
const store = useInterviewStore()
const router = useRouter()

const stats = computed(() => ({
  pending: store.list.filter((i) => i.status === 'pending').length,
  evaluating: store.list.filter((i) => i.status === 'evaluating').length,
  reported: store.list.filter((i) => i.status === 'reported').length,
  total: store.list.length,
}))

onMounted(() => {
  store.loadInterviews()
})

function onEnter(item: Interview) {
  router.push('/prep/' + item.id)
}
function onViewResult(item: Interview) {
  router.push('/result/' + item.id)
}
</script>

<style scoped>
.stat-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 28px;
}
.stat {
  background: var(--surface);
  border: 1px solid var(--line-soft);
  border-radius: var(--r-lg);
  padding: 18px 20px;
  box-shadow: var(--shadow-sm);
}
.stat .num {
  font-size: 28px;
  font-weight: 800;
  line-height: 1.1;
}
.stat .lbl {
  font-size: 12px;
  color: var(--ink-500);
  margin-top: 4px;
}
.num.blue {
  color: var(--brand);
}
.num.amber {
  color: var(--warning);
}
.num.green {
  color: var(--success);
}
.interview-list {
  display: grid;
  gap: 14px;
  min-height: 80px;
}
</style>
