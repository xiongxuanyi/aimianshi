<template>
  <div class="card center-card">
    <div class="big-icon ok">✓</div>
    <h2>面试已提交</h2>
    <p class="lead">感谢你的作答，AI 面试官正在为你生成评估报告。</p>

    <div class="status-chip"><span class="dot"></span>评分中 · 预计 1–3 分钟出报告</div>

    <div class="summary-grid">
      <div class="sg"><b>已完成</b><span>面试状态</span></div>
      <div class="sg"><b>已提交</b><span>评分进度</span></div>
      <div class="sg"><b>即时</b><span>结果通知</span></div>
    </div>

    <div class="note-box">
      <b>结果可见性说明：</b>详细评分与报告由企业方控制是否向你开放。如已开放，你可在「面试大厅」中点击「查看结果」查看。
    </div>

    <el-button type="primary" size="large" class="block" @click="$router.push('/hall')">
      返回面试大厅
    </el-button>
  </div>
</template>

<script setup lang="ts"></script>

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
  background: var(--warning-bg);
  color: var(--warning);
}
.status-chip .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
  animation: pulse 1.4s infinite;
}
@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.35;
  }
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
