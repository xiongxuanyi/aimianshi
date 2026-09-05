<template>
  <div class="chat-wrap">
    <div class="card chat-shell">
      <!-- 顶栏：AI 面试官 + 进度 / 计时 / 操作 -->
      <div class="chat-header">
        <div class="ai-presence">
          <div class="ai-avatar">
            <svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
            </svg>
          </div>
          <div class="who">
            <b>AI 面试官 <span class="online">在线</span></b>
            <div class="post">{{ interview?.position }} · {{ interview?.company }}</div>
          </div>
        </div>
        <div class="chat-meta">
          <span class="pill">{{ qLabel }}</span>
          <span class="pill clock">{{ clock }}</span>
          <button class="icon-btn" :class="{ active: ttsOn }" title="开关朗读面试官问题" @click="toggleTTS">
            {{ ttsOn ? '🔊' : '🔇' }}
          </button>
          <button class="icon-btn danger" title="结束面试" @click="endDialog = true">⏹</button>
        </div>
      </div>

      <!-- 进度条 -->
      <div class="chat-progress">
        <div class="fill" :style="{ width: progressPct + '%' }"></div>
      </div>

      <!-- 消息区 -->
      <div ref="chatBodyRef" class="chat-body">
        <div v-for="(msg, idx) in messages" :key="idx" class="msg" :class="msg.role">
          <div v-if="msg.role === 'ai'" class="m-avatar ai">
            <svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
            </svg>
          </div>
          <div class="bubble" :class="msg.role">
            <span v-if="msg.typing && !msg.text" class="typing-dots"><i></i><i></i><i></i></span>
            <span v-else>{{ msg.text }}</span>
          </div>
          <div v-if="msg.role === 'user'" class="m-avatar user">{{ avatarText }}</div>
        </div>
      </div>

      <!-- 输入区 -->
      <div class="chat-input">
        <div class="row">
          <button class="mic-btn" title="按住说话（语音输入）" @mousedown="onMicDown" @mouseup="onMicUp" @mouseleave="onMicUp">
            🎙️
          </button>
          <div class="ta-wrap">
            <textarea
              ref="textareaRef"
              v-model="input"
              rows="1"
              maxlength="3000"
              placeholder="在此输入你的回答，或按住左侧 🎙️ 语音作答…"
              @keydown="onKeydown"
              @input="autoResize"
            ></textarea>
            <div class="counter">{{ input.length }}/3000</div>
          </div>
          <button class="send-btn" :disabled="!canSend" @click="send">发送</button>
        </div>
        <div class="hints">
          <span><kbd>Enter</kbd> 发送 · <kbd>Shift</kbd>+<kbd>Enter</kbd> 换行</span>
          <span class="tts" @click="toggleTTS">{{ ttsOn ? '🔊 AI 问题朗读已开启' : '🔇 AI 问题朗读已关闭' }}</span>
        </div>
      </div>
    </div>
  </div>

  <!-- 结束面试确认 -->
  <el-dialog v-model="endDialog" title="确认结束面试？" width="420px" align-center>
    <p class="dlg-text">提交后将立即进入评分，无法继续作答。请确认你已答完所有问题。</p>
    <template #footer>
      <el-button @click="endDialog = false">再想想</el-button>
      <el-button type="danger" @click="confirmEnd">确认提交</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { fetchInterview, getInterviewScript } from '../api/mock'
import type { ChatMessage, ChatTurn, Interview } from '../types'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const interview = ref<Interview>()
const messages = ref<ChatMessage[]>([])
const script = ref<ChatTurn[]>([])
const totalQuestions = ref(6)
const turnIndex = ref(0)
const aiBusy = ref(false)
const qProgress = ref(0)
const clock = ref('00:00')
const ttsOn = ref(true)
const endDialog = ref(false)
const input = ref('')

const chatBodyRef = ref<HTMLElement>()
const textareaRef = ref<HTMLTextAreaElement>()

let seconds = 0
let timer: ReturnType<typeof setInterval> | null = null
let holdTimer: ReturnType<typeof setTimeout> | null = null

const avatarText = computed(() => (auth.userName ? auth.userName.slice(0, 1) : '候'))
const canSend = computed(() => input.value.trim().length > 0 && !aiBusy.value)
const qLabel = computed(() =>
  qProgress.value === 0 ? '准备开始' : `第 ${qProgress.value} / ${totalQuestions.value} 题`,
)
const progressPct = computed(() =>
  totalQuestions.value === 0 ? 0 : Math.round((qProgress.value / totalQuestions.value) * 100),
)

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function scrollToBottom(): void {
  nextTick(() => {
    const el = chatBodyRef.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

function startTimer(): void {
  timer = setInterval(() => {
    seconds++
    clock.value =
      String(Math.floor(seconds / 60)).padStart(2, '0') + ':' + String(seconds % 60).padStart(2, '0')
  }, 1000)
}

/** AI 消息：先显示「正在输入」再逐字输出，模拟流式返回 */
async function pushAi(text: string): Promise<void> {
  const msg = reactive<ChatMessage>({ role: 'ai', text: '', typing: true })
  messages.value.push(msg)
  scrollToBottom()
  await sleep(450)
  await new Promise<void>((resolve) => {
    let i = 0
    const t = setInterval(() => {
      msg.text = text.slice(0, ++i)
      scrollToBottom()
      if (i >= text.length) {
        clearInterval(t)
        msg.typing = false
        resolve()
      }
    }, 16)
  })
}

async function playTurn(): Promise<void> {
  const turn = script.value[turnIndex.value]
  if (!turn) return
  aiBusy.value = true
  await pushAi(turn.text)
  qProgress.value = turn.q
  turnIndex.value++
  aiBusy.value = false
}

function pushUser(text: string): void {
  messages.value.push({ role: 'user', text })
  scrollToBottom()
}

function send(): void {
  const val = input.value.trim()
  if (!val || aiBusy.value) return
  pushUser(val)
  input.value = ''
  resetTextarea()
  if (turnIndex.value < script.value.length) {
    playTurn()
  } else {
    pushAi('（请点击右上角「结束面试」按钮提交本次面试）')
  }
}

function resetTextarea(): void {
  nextTick(() => {
    const el = textareaRef.value
    if (el) el.style.height = 'auto'
  })
}

function autoResize(): void {
  const el = textareaRef.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 120) + 'px'
}

function onKeydown(e: KeyboardEvent): void {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    send()
  }
}

function toggleTTS(): void {
  ttsOn.value = !ttsOn.value
  ElMessage.success(ttsOn.value ? '已开启 AI 问题朗读' : '已关闭 AI 问题朗读')
}

function confirmEnd(): void {
  endDialog.value = false
  if (timer) clearInterval(timer)
  router.push('/complete')
}

/** 语音输入（按住说话，原型以定时器模拟一段语音转写结果） */
function onMicDown(): void {
  holdTimer = setTimeout(() => {
    pushUser(
      '我理解这个岗位需要扎实的 Java 基础和并发处理能力，我在上一家公司主导过订单中心的重构，' +
        '把峰值 QPS 从 800 提升到了 3000 以上，主要做了分库分表和缓存预热。',
    )
    if (!aiBusy.value && turnIndex.value < script.value.length) playTurn()
  }, 1600)
}
function onMicUp(): void {
  if (holdTimer) {
    clearTimeout(holdTimer)
    holdTimer = null
  }
}

onMounted(async () => {
  interview.value = await fetchInterview(route.params.id as string)
  if (!interview.value) {
    ElMessage.error('未找到该面试')
    router.replace('/hall')
    return
  }
  const s = getInterviewScript()
  script.value = s.turns
  totalQuestions.value = s.total
  startTimer()
  await playTurn() // 开场白
  await playTurn() // 第一题
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
  if (holdTimer) clearTimeout(holdTimer)
})
</script>

<style scoped>
.chat-wrap {
  max-width: 960px;
  margin: 0 auto;
}
.chat-shell {
  overflow: hidden;
  display: flex;
  flex-direction: column;
  height: calc(100vh - 96px);
  min-height: 560px;
}
.chat-header {
  padding: 16px 22px;
  border-bottom: 1px solid var(--line-soft);
  display: flex;
  align-items: center;
  gap: 14px;
  flex-shrink: 0;
}
.ai-presence {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
}
.ai-avatar {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: linear-gradient(135deg, var(--brand), var(--ai));
  color: #fff;
  display: grid;
  place-items: center;
  flex-shrink: 0;
  box-shadow: var(--shadow-md);
}
.ai-avatar svg {
  width: 24px;
  height: 24px;
}
.who b {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 15px;
}
.who .online {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  font-weight: 600;
  color: var(--success);
}
.who .online::before {
  content: '';
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--success);
  box-shadow: 0 0 0 3px rgba(5, 150, 105, 0.15);
}
.who .post {
  font-size: 12px;
  color: var(--ink-500);
  margin-top: 1px;
}
.chat-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}
.pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  background: var(--bg);
  border: 1px solid var(--line);
  color: var(--ink-700);
}
.pill.clock {
  font-variant-numeric: tabular-nums;
}
.icon-btn {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  border: 1px solid var(--line);
  background: #fff;
  color: var(--ink-700);
  display: grid;
  place-items: center;
  font-size: 15px;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}
.icon-btn:hover {
  background: var(--bg);
}
.icon-btn.active {
  background: var(--brand-50);
  border-color: var(--brand);
  color: var(--brand);
}
.icon-btn.danger {
  color: var(--danger);
}
.chat-progress {
  height: 4px;
  background: var(--line-soft);
  flex-shrink: 0;
}
.chat-progress .fill {
  height: 100%;
  width: 0;
  background: linear-gradient(90deg, var(--brand), var(--ai));
  transition: width 0.5s ease;
}
.chat-body {
  flex: 1;
  overflow-y: auto;
  padding: 24px 22px;
  background: linear-gradient(180deg, #fbfbfe 0%, var(--bg) 100%);
}
.msg {
  display: flex;
  gap: 10px;
  margin-bottom: 18px;
}
.msg .bubble {
  max-width: 76%;
  padding: 12px 16px;
  border-radius: 14px;
  font-size: 14px;
  line-height: 1.75;
  word-break: break-word;
}
.msg.ai {
  justify-content: flex-start;
}
.msg.ai .bubble {
  background: #fff;
  border: 1px solid var(--line-soft);
  border-top-left-radius: 4px;
  box-shadow: var(--shadow-sm);
}
.msg.user {
  justify-content: flex-end;
}
.msg.user .bubble {
  background: linear-gradient(135deg, var(--brand), var(--brand-700));
  color: #fff;
  border-top-right-radius: 4px;
  box-shadow: var(--shadow-md);
}
.m-avatar {
  width: 34px;
  height: 34px;
  border-radius: 9px;
  flex-shrink: 0;
  display: grid;
  place-items: center;
  color: #fff;
  margin-top: 2px;
  font-size: 13px;
  font-weight: 700;
}
.m-avatar.ai {
  background: linear-gradient(135deg, var(--brand), var(--ai));
}
.m-avatar.ai svg {
  width: 18px;
  height: 18px;
}
.m-avatar.user {
  background: linear-gradient(135deg, #94a3b8, #64748b);
}
.typing-dots {
  display: flex;
  gap: 4px;
  padding: 4px 2px;
}
.typing-dots i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--ink-400);
  animation: blink 1.2s infinite;
}
.typing-dots i:nth-child(2) {
  animation-delay: 0.15s;
}
.typing-dots i:nth-child(3) {
  animation-delay: 0.3s;
}
@keyframes blink {
  0%,
  100% {
    opacity: 0.25;
  }
  50% {
    opacity: 1;
  }
}
.chat-input {
  padding: 14px 18px;
  border-top: 1px solid var(--line-soft);
  background: #fff;
  flex-shrink: 0;
}
.chat-input .row {
  display: flex;
  align-items: flex-end;
  gap: 10px;
}
.mic-btn {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  border: 1px solid var(--line);
  background: #fff;
  font-size: 18px;
  cursor: pointer;
  flex-shrink: 0;
  display: grid;
  place-items: center;
  transition: background 0.15s;
}
.mic-btn:active {
  background: var(--danger-bg);
}
.ta-wrap {
  flex: 1;
  position: relative;
}
.ta-wrap textarea {
  width: 100%;
  resize: none;
  border: 1px solid var(--line);
  border-radius: var(--r-md);
  padding: 11px 14px 24px;
  font-size: 14px;
  line-height: 1.6;
  outline: none;
  font-family: inherit;
  color: inherit;
  max-height: 120px;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.ta-wrap textarea:focus {
  border-color: var(--brand);
  box-shadow: 0 0 0 3px var(--brand-50);
}
.counter {
  position: absolute;
  right: 12px;
  bottom: 6px;
  font-size: 11px;
  color: var(--ink-400);
}
.send-btn {
  height: 42px;
  padding: 0 22px;
  border-radius: 12px;
  border: none;
  background: linear-gradient(135deg, var(--brand), var(--brand-700));
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: var(--shadow-md);
  flex-shrink: 0;
}
.send-btn:hover:not(:disabled) {
  filter: brightness(1.05);
}
.send-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
  box-shadow: none;
}
.hints {
  display: flex;
  align-items: center;
  gap: 14px;
  font-size: 11px;
  color: var(--ink-400);
  margin-top: 8px;
}
.hints kbd {
  padding: 1px 6px;
  border-radius: 5px;
  background: var(--bg);
  border: 1px solid var(--line);
  font-family: inherit;
  font-size: 10px;
}
.tts {
  margin-left: auto;
  font-size: 12px;
  color: var(--ink-500);
  cursor: pointer;
  user-select: none;
}
.tts:hover {
  color: var(--brand);
}
.dlg-text {
  margin: 0;
  color: var(--ink-500);
  font-size: 14px;
  line-height: 1.7;
}
</style>
