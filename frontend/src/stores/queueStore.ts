/**
 * 队列统计状态管理
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { queueApi } from '@/api'
import type { QueueStats } from '@/api/types'

export const useQueueStore = defineStore('queue', () => {
  // 状态
  const stats = ref<QueueStats>({
    pending: 0,
    processing: 0,
    completed: 0,
    failed: 0,
    cancelled: 0,
  })
  
  const total = ref(0)
  const lastUpdate = ref<string>('')
  const loading = ref(false)
  const error = ref<string | null>(null)
  const autoRefresh = ref(false)
  let refreshTimer: number | null = null

  // 动作
  /**
   * 获取队列统计
   */
  async function fetchStats() {
    loading.value = true
    error.value = null
    
    try {
      const response = await queueApi.getQueueStats()
      // 确保所有字段都有默认值
      stats.value = {
        pending: response.stats.pending || 0,
        processing: response.stats.processing || 0,
        completed: response.stats.completed || 0,
        failed: response.stats.failed || 0,
        cancelled: response.stats.cancelled || 0,
      }
      total.value = response.total
      lastUpdate.value = response.timestamp
      return response
    } catch (err: any) {
      error.value = err.message || '获取队列统计失败'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 启动自动刷新
   */
  function startAutoRefresh(interval: number = 5000) {
    if (autoRefresh.value) return
    
    autoRefresh.value = true
    
    // 立即获取一次
    fetchStats()
    
    // 设置定时刷新
    refreshTimer = window.setInterval(() => {
      fetchStats()
    }, interval)
  }

  /**
   * 停止自动刷新
   */
  function stopAutoRefresh() {
    autoRefresh.value = false
    if (refreshTimer) {
      clearInterval(refreshTimer)
      refreshTimer = null
    }
  }

  /**
   * 重置超时任务
   */
  async function resetStaleTasks(timeoutMinutes: number = 60) {
    loading.value = true
    error.value = null
    
    try {
      const response = await queueApi.resetStaleTasks(timeoutMinutes)
      // 重新获取统计
      await fetchStats()
      return response
    } catch (err: any) {
      error.value = err.message || '重置超时任务失败'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 清理旧任务
   */
  async function cleanupOldTasks(days: number = 7) {
    loading.value = true
    error.value = null
    
    try {
      const response = await queueApi.cleanupOldTasks(days)
      // 重新获取统计
      await fetchStats()
      return response
    } catch (err: any) {
      error.value = err.message || '清理旧任务失败'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 健康检查
   */
  async function checkHealth() {
    try {
      const response = await queueApi.healthCheck()
      return response
    } catch (err: any) {
      error.value = err.message || '健康检查失败'
      throw err
    }
  }

  /**
   * 清空错误
   */
  function clearError() {
    error.value = null
  }

  /**
   * 重置状态
   */
  function reset() {
    stopAutoRefresh()
    stats.value = {
      pending: 0,
      processing: 0,
      completed: 0,
      failed: 0,
      cancelled: 0,
    }
    total.value = 0
    lastUpdate.value = ''
    loading.value = false
    error.value = null
  }

  return {
    // 状态
    stats,
    total,
    lastUpdate,
    loading,
    error,
    autoRefresh,
    
    // 动作
    fetchStats,
    startAutoRefresh,
    stopAutoRefresh,
    resetStaleTasks,
    cleanupOldTasks,
    checkHealth,
    clearError,
    reset,
  }
})

