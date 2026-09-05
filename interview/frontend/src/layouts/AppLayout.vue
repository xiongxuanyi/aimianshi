<template>
  <header class="topbar">
    <div class="inner">
      <div class="left">
        <BrandLogo subtitle="候选人端" />
      </div>
      <div class="user">
        <div class="meta">
          <b>{{ auth.userName || '候选人' }}</b>
          <span>求职者</span>
        </div>
        <div class="avatar">{{ avatarText }}</div>
        <button class="logout" @click="handleLogout">退出</button>
      </div>
    </div>
  </header>

  <main class="app">
    <router-view />
  </main>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import BrandLogo from '../components/BrandLogo.vue'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()

const avatarText = computed(() => (auth.userName ? auth.userName.slice(0, 1) : '候'))

function handleLogout() {
  auth.logout()
  ElMessage.success('已退出登录')
  router.push('/login')
}
</script>

<style scoped>
.topbar {
  position: sticky;
  top: 0;
  z-index: 40;
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--line-soft);
}
.inner {
  max-width: 1120px;
  margin: 0 auto;
  height: 64px;
  padding: 0 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.left {
  display: flex;
  align-items: center;
}
.user {
  display: flex;
  align-items: center;
  gap: 10px;
}
.meta {
  text-align: right;
  line-height: 1.25;
}
.meta b {
  display: block;
  font-size: 13px;
}
.meta span {
  font-size: 11px;
  color: var(--ink-400);
}
.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--brand), var(--ai));
  color: #fff;
  display: grid;
  place-items: center;
  font-size: 14px;
  font-weight: 700;
}
.logout {
  font-size: 13px;
  color: var(--ink-500);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 6px 12px;
  background: #fff;
  cursor: pointer;
}
.logout:hover {
  background: var(--bg);
  color: var(--ink-700);
}
.app {
  max-width: 1120px;
  margin: 0 auto;
  padding: 32px 24px 80px;
}
</style>
