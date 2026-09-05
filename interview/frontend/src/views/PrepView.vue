<template>
  <div class="prep-wrap">
    <div class="page-head">
      <h1>面试前准备</h1>
      <p>岗位：{{ interview?.position }} · {{ interview?.company }}</p>
    </div>

    <el-steps :active="stepActive" align-center class="steps">
      <el-step title="设备检测" description="检测麦克风" />
      <el-step title="面试须知" description="了解规则" />
      <el-step title="隐私授权" description="授权同意" />
    </el-steps>

    <div class="card prep-card">
      <h3>🎙️ 麦克风检测</h3>
      <p class="desc">如你计划使用语音作答，请先确认麦克风可正常录音。</p>
      <div class="mic-box">
        <div class="mic-visual" :class="{ ok: micOk }">{{ micOk ? '✅' : '🎙️' }}</div>
        <div class="mic-info">
          <b>{{ micOk ? '麦克风正常' : '尚未检测' }}</b>
          <span>{{ micOk ? '检测通过，可正常录音用于语音作答' : '点击右侧按钮开始检测麦克风设备' }}</span>
        </div>
        <div class="wave" :class="{ on: micOk }">
          <template v-if="micOk"><i v-for="n in 8" :key="n"></i></template>
        </div>
        <el-button @click="toggleMic">{{ micOk ? '重新检测' : '开始检测' }}</el-button>
      </div>
    </div>

    <div class="card prep-card">
      <h3>📋 面试须知</h3>
      <p class="desc">开始前请了解本场面试的基本信息与规则。</p>
      <ul class="notice-list">
        <li><div class="ic">💼</div><div><b>面试岗位</b><span>{{ interview?.position }} · {{ interview?.company }}</span></div></li>
        <li><div class="ic">⏱️</div><div><b>时长与题量</b><span>共 {{ interview?.questionCount }} 题，预计 {{ interview?.duration }}</span></div></li>
        <li><div class="ic">💬</div><div><b>作答形式</b><span>文字实时对话为主，可开启语音输入，AI 面试官会自动追问</span></div></li>
        <li><div class="ic">✍️</div><div><b>作答建议</b><span>尽量具体、举例说明；每题作答后 AI 可能追问 1–2 次</span></div></li>
      </ul>
    </div>

    <div class="card prep-card">
      <h3>🛡️ 隐私与授权</h3>
      <p class="desc">为保证面试与评分正常进行，需你授权以下信息处理（依据《个人信息保护法》）。</p>

      <el-checkbox v-model="c1" class="consent-item">
        <div class="c-box"><b>授权录音</b><span>允许在面试过程中通过麦克风采集你的语音</span></div>
      </el-checkbox>
      <el-checkbox v-model="c2" class="consent-item">
        <div class="c-box"><b>授权语音转写</b><span>将你的语音转写为文字，作为面试对话的一部分</span></div>
      </el-checkbox>
      <el-checkbox v-model="c3" class="consent-item">
        <div class="c-box"><b>授权 AI 分析与评分</b><span>由 AI 对你的作答进行分析、打分并生成评估报告</span></div>
      </el-checkbox>

      <p class="consent-all">你的个人信息仅用于本次面试评估，采用最小化、用途限定原则处理，可依法申请查阅、更正与删除。</p>
    </div>

    <div class="prep-actions">
      <el-button size="large" @click="router.push('/hall')">返回</el-button>
      <el-button type="primary" size="large" class="start-btn" :disabled="!allConsent" @click="start">
        开始面试
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { fetchInterview } from '../api/mock'
import type { Interview } from '../types'

const route = useRoute()
const router = useRouter()

const interview = ref<Interview>()
const micOk = ref(false)
const c1 = ref(false)
const c2 = ref(false)
const c3 = ref(false)

const allConsent = computed(() => c1.value && c2.value && c3.value)
const stepActive = computed(() => (allConsent.value ? 3 : micOk.value ? 2 : 1))

onMounted(async () => {
  interview.value = await fetchInterview(route.params.id as string)
  if (!interview.value) {
    ElMessage.error('未找到该面试')
    router.replace('/hall')
  }
})

function toggleMic() {
  micOk.value = !micOk.value
  if (micOk.value) ElMessage.success('麦克风检测通过 🎙️')
}

function start() {
  router.push('/interview/' + route.params.id)
}
</script>

<style scoped>
.prep-wrap {
  max-width: 760px;
  margin: 0 auto;
}
.steps {
  margin-bottom: 28px;
}
.prep-card {
  padding: 26px 30px;
  margin-bottom: 18px;
}
.prep-card h3 {
  margin: 0 0 4px;
  font-size: 16px;
  font-weight: 700;
}
.desc {
  margin: 0 0 20px;
  font-size: 13px;
  color: var(--ink-500);
}
.mic-box {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 18px 20px;
  border: 1px solid var(--line);
  border-radius: var(--r-md);
}
.mic-visual {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: var(--brand-50);
  color: var(--brand);
  display: grid;
  place-items: center;
  font-size: 24px;
  flex-shrink: 0;
}
.mic-visual.ok {
  background: var(--success-bg);
  color: var(--success);
}
.mic-info {
  flex: 1;
}
.mic-info b {
  display: block;
  font-size: 14px;
}
.mic-info span {
  font-size: 12px;
  color: var(--ink-500);
}
.wave {
  display: flex;
  align-items: center;
  gap: 3px;
  height: 28px;
}
.wave i {
  width: 3px;
  border-radius: 2px;
  background: var(--brand);
  height: 6px;
}
.wave.on i {
  animation: wave 1s ease-in-out infinite;
}
.wave i:nth-child(1) { animation-delay: 0s; }
.wave i:nth-child(2) { animation-delay: 0.12s; }
.wave i:nth-child(3) { animation-delay: 0.24s; }
.wave i:nth-child(4) { animation-delay: 0.06s; }
.wave i:nth-child(5) { animation-delay: 0.18s; }
.wave i:nth-child(6) { animation-delay: 0.3s; }
.wave i:nth-child(7) { animation-delay: 0.1s; }
.wave i:nth-child(8) { animation-delay: 0.22s; }
@keyframes wave {
  0%,
  100% {
    height: 6px;
  }
  50% {
    height: 24px;
  }
}
.notice-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 10px;
}
.notice-list li {
  display: flex;
  gap: 12px;
  font-size: 14px;
  align-items: flex-start;
}
.notice-list .ic {
  width: 22px;
  height: 22px;
  border-radius: 6px;
  background: var(--brand-50);
  color: var(--brand);
  display: grid;
  place-items: center;
  font-size: 13px;
  flex-shrink: 0;
  margin-top: 2px;
}
.notice-list b {
  display: block;
}
.notice-list span {
  color: var(--ink-500);
  font-size: 13px;
}
.consent-item {
  display: flex;
  align-items: flex-start;
  padding: 14px 16px;
  border: 1px solid var(--line);
  border-radius: var(--r-md);
  margin-bottom: 10px;
  width: 100%;
  height: auto;
  white-space: normal;
}
.consent-item.is-checked {
  border-color: var(--brand);
  background: var(--brand-50);
}
.c-box {
  margin-left: 8px;
}
.c-box b {
  display: block;
  font-size: 14px;
  font-weight: 600;
}
.c-box span {
  font-size: 12px;
  color: var(--ink-500);
}
.consent-all {
  font-size: 12px;
  color: var(--ink-400);
  line-height: 1.7;
  padding: 4px 16px 0;
  margin: 0;
}
.prep-actions {
  display: flex;
  gap: 12px;
  margin-top: 8px;
}
.start-btn {
  flex: 1;
}
</style>
