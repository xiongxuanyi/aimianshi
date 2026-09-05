import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

const TOKEN_KEY = 'im_token'
const USER_KEY = 'im_user'

/**
 * 候选人登录态。
 * 演示环境：任意账号密码均可登录，登录态持久化到 localStorage。
 */
export const useAuthStore = defineStore('auth', () => {
  const token = ref<string>(localStorage.getItem(TOKEN_KEY) || '')
  const userName = ref<string>(localStorage.getItem(USER_KEY) || '')

  const isLoggedIn = computed(() => !!token.value)

  /** 登录：邮箱取前缀、手机号取原值 */
  function login(account: string): void {
    const acc = account.trim()
    token.value = 'mock-token-' + Date.now()
    userName.value = acc.includes('@') ? acc.split('@')[0] : acc
    localStorage.setItem(TOKEN_KEY, token.value)
    localStorage.setItem(USER_KEY, userName.value)
  }

  function logout(): void {
    token.value = ''
    userName.value = ''
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  }

  return { token, userName, isLoggedIn, login, logout }
})
