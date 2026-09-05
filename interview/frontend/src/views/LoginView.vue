<template>
  <div class="login">
    <div class="brand-panel">
      <div class="logo">
        <div class="mark">
          <svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
          </svg>
        </div>
        <div>
          <h1>面试大师</h1>
          <div class="sub">InterviewMaster · 候选人端</div>
        </div>
      </div>

      <div class="headline">
        <h2>你的 AI 面试官<br />公正、专业、随时可约</h2>
        <p>无需下载任何软件。通过企业发送的邀请链接进入，与 AI 面试官进行一场自然、真实的对话面试，全程语音可选，作答更从容。</p>
      </div>

      <div class="features">
        <div class="feature"><div class="ic">🕐</div><div><b>约 30 分钟，灵活安排</b><span>收到邀请后，在有效期内随时参加，无需预约排队。</span></div></div>
        <div class="feature"><div class="ic">🎙️</div><div><b>文字 + 语音作答</b><span>打字或直接说话，AI 会自动转写，选择你最舒服的方式。</span></div></div>
        <div class="feature"><div class="ic">🛡️</div><div><b>隐私授权透明可控</b><span>录音与转写需你明确授权，数据按《个人信息保护法》最小化处理。</span></div></div>
      </div>

      <div class="foot">© 2026 InterviewMaster · 面向企业招聘的 AI 初筛面试工具</div>
    </div>

    <div class="form-panel">
      <div class="box">
        <h2>欢迎回来 👋</h2>
        <p class="lead">登录后查看你的面试邀请与结果</p>

        <form @submit.prevent="handleLogin">
          <div class="row">
            <label class="field-label">手机号 / 邮箱</label>
            <el-input v-model="account" size="large" placeholder="请输入手机号或邮箱" clearable />
          </div>
          <div class="row">
            <label class="field-label">密码</label>
            <el-input
              v-model="password"
              type="password"
              size="large"
              placeholder="请输入密码"
              show-password
              @keyup.enter="handleLogin"
            />
            <div class="hint"><a href="#" @click.prevent="notify">忘记密码？</a></div>
          </div>

          <el-button type="primary" size="large" class="btn-block" native-type="submit">登 录</el-button>
        </form>

        <div class="divider">或</div>
        <el-button size="large" class="btn-block" @click="handleInvite">🎫 使用面试邀请码进入</el-button>

        <p class="switch">还没有账号？<a href="#" @click.prevent="notify">立即注册</a></p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'

const account = ref('')
const password = ref('')
const router = useRouter()
const auth = useAuthStore()

function notify() {
  ElMessage.info('演示环境：该功能暂未开放')
}

function handleInvite() {
  ElMessage.info('演示环境：已使用邀请码进入')
  handleLogin()
}

function handleLogin() {
  if (!account.value.trim()) {
    ElMessage.warning('请输入手机号或邮箱')
    return
  }
  auth.login(account.value)
  ElMessage.success('登录成功，欢迎回来 👋')
  router.push('/hall')
}
</script>

<style scoped>
.login {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 1.05fr 1fr;
}
.brand-panel {
  position: relative;
  overflow: hidden;
  color: #fff;
  background: linear-gradient(150deg, #312e81 0%, #4f46e5 48%, #7c3aed 100%);
  padding: 64px 72px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}
.brand-panel::before {
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(600px 400px at 85% -10%, rgba(255, 255, 255, 0.18), transparent 60%),
    radial-gradient(500px 380px at -10% 110%, rgba(255, 255, 255, 0.12), transparent 60%);
}
.brand-panel::after {
  content: '';
  position: absolute;
  inset: 0;
  opacity: 0.5;
  background-image: linear-gradient(rgba(255, 255, 255, 0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.05) 1px, transparent 1px);
  background-size: 42px 42px;
  mask-image: radial-gradient(700px 500px at 30% 20%, #000 0%, transparent 70%);
}
.brand-panel > * {
  position: relative;
  z-index: 1;
}
.logo {
  display: flex;
  align-items: center;
  gap: 12px;
}
.logo .mark {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.16);
  backdrop-filter: blur(6px);
  display: grid;
  place-items: center;
  border: 1px solid rgba(255, 255, 255, 0.2);
}
.logo .mark svg {
  width: 25px;
  height: 25px;
}
.logo h1 {
  font-size: 24px;
  font-weight: 700;
  margin: 0;
  letter-spacing: 0.5px;
}
.logo .sub {
  font-size: 13px;
  opacity: 0.8;
  margin-top: 2px;
}
.headline {
  margin: 44px 0;
}
.headline h2 {
  font-size: 34px;
  font-weight: 800;
  line-height: 1.35;
  margin: 0 0 16px;
  letter-spacing: 0.5px;
}
.headline p {
  font-size: 15px;
  opacity: 0.86;
  line-height: 1.8;
  max-width: 440px;
  margin: 0;
}
.features {
  display: grid;
  gap: 14px;
}
.feature {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}
.feature .ic {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.14);
  display: grid;
  place-items: center;
  font-size: 15px;
  flex-shrink: 0;
}
.feature b {
  display: block;
  font-size: 14px;
}
.feature span {
  font-size: 13px;
  opacity: 0.78;
}
.foot {
  font-size: 12px;
  opacity: 0.55;
}

.form-panel {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px;
}
.box {
  width: 100%;
  max-width: 400px;
}
.box h2 {
  font-size: 24px;
  font-weight: 700;
  margin: 0 0 6px;
}
.lead {
  color: var(--ink-500);
  margin: 0 0 32px;
  font-size: 14px;
}
.row {
  margin-bottom: 20px;
}
.field-label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: var(--ink-700);
  margin-bottom: 6px;
}
.hint {
  font-size: 12px;
  color: var(--ink-400);
  margin-top: 8px;
  text-align: right;
}
.divider {
  display: flex;
  align-items: center;
  gap: 14px;
  margin: 24px 0;
  color: var(--ink-400);
  font-size: 12px;
}
.divider::before,
.divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--line);
}
.switch {
  text-align: center;
  font-size: 14px;
  color: var(--ink-500);
  margin-top: 24px;
}
.btn-block {
  width: 100%;
}
</style>
