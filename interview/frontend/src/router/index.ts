import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

import AppLayout from '../layouts/AppLayout.vue'
import LoginView from '../views/LoginView.vue'
import HallView from '../views/HallView.vue'
import PrepView from '../views/PrepView.vue'
import InterviewView from '../views/InterviewView.vue'
import CompleteView from '../views/CompleteView.vue'
import ResultView from '../views/ResultView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'login', component: LoginView },
    {
      path: '/',
      component: AppLayout,
      meta: { requiresAuth: true },
      children: [
        { path: '', redirect: '/hall' },
        { path: 'hall', name: 'hall', component: HallView },
        { path: 'prep/:id', name: 'prep', component: PrepView },
        { path: 'interview/:id', name: 'interview', component: InterviewView },
        { path: 'complete', name: 'complete', component: CompleteView },
        { path: 'result/:id', name: 'result', component: ResultView },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/hall' },
  ],
})

// 登录守卫：未登录跳转登录页，已登录访问登录页跳转大厅
router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isLoggedIn) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.name === 'login' && auth.isLoggedIn) {
    return { path: '/hall' }
  }
  return true
})

export default router
