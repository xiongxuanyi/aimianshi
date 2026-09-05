import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Interview } from '../types'
import { fetchInterviews } from '../api/mock'

/** 面试数据（候选人被邀请的面试列表） */
export const useInterviewStore = defineStore('interview', () => {
  const list = ref<Interview[]>([])
  const loading = ref(false)

  async function loadInterviews(): Promise<void> {
    loading.value = true
    try {
      list.value = await fetchInterviews()
    } finally {
      loading.value = false
    }
  }

  return { list, loading, loadInterviews }
})
