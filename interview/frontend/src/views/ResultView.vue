<template>
  <div class="card center-card">
    <div class="big-icon ok">🎉</div>
    <h2>面试已完成</h2>
    <p class="lead">本场面试的评估报告已生成。</p>

    <div class="status-chip"><span class="dot"></span>已出报告</div>

    <div class="summary-grid">
      <div class="sg"><b>{{ interview?.position }}</b><span>面试岗位</span></div>
      <div class="sg"><b>{{ interview?.submittedAt }}</b><span>完成时间</span></div>
      <div class="sg"><b>已生成</b><span>报告状态</span></div>
    </div>

    <div class="note-box">
      <b>结果可见性说明：</b>本场面试的详细评分与逐题点评暂未向你开放，由企业方控制展示。如需了解结果，可联系面试企业。
    </div>

    <el-button type="primary" size="large" class="block" @click="$router.push('/hall')">
      返回面试大厅
    </el-button>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { fetchInterview } from '../api/mock'
import type { Interview } from '../types'

const route = useRoute()
const router = useRouter()
const interview = ref<Interview>()

onMounted(async () => {
  interview.value = await fetchInterview(route.params.id as string)
  if (!interview.value) {
    ElMessage.error('未找到该面试')
    router.replace('/hall')
  }
})
</script>

<style scoped>
.center-card {
  max-width: 520px;
  margin: 40px auto;
  text-align: center;
  padding: 48px 40px;
}
.big-icon {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  margin: 0 auto 20px;
  display: grid;
  place-items: center;
  font-size: 32px;
}
.big-icon.ok {
  background: var(--success-bg);
  color: var(--success);
}
h2 {
  margin: 0 0 8px;
  font-size: 22px;
  font-weight: 800;
}
.lead {
  color: var(--ink-500);
  margin: 0 0 24px;
}
.status-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  height: 34px;
  padding: 0 16px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 24px;
  background: var(--success-bg);
  color: var(--success);
}
.status-chip .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
}
.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 24px;
  text-align: left;
}
.sg {
  background: var(--bg);
  border-radius: var(--r-md);
  padding: 14px;
}
.sg b {
  display: block;
  font-size: 13px;
  word-break: break-all;
}
.sg span {
  font-size: 12px;
  color: var(--ink-500);
}
.note-box {
  text-align: left;
  background: var(--ai-soft);
  border: 1px solid #ede9fe;
  border-radius: var(--r-md);
  padding: 14px 16px;
  font-size: 13px;
  color: var(--ink-700);
  line-height: 1.7;
  margin-bottom: 24px;
}
.note-box b {
  color: var(--ai);
}
.block {
  width: 100%;
}
</style>
