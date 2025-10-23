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
  const baseInterval = 5000 // 基础轮询间隔：5秒
  const maxInterval = 60000 // 最大轮询间隔：60秒
  let currentInterval = baseInterval
  let consecutiveNoChange = 0 // 连续无变化次数

  // 动作
  /**
   * 获取队列统计
   */
  async function fetchStats() {
    // 防止并发请求
    if (loading.value) return
    
    loading.value = true
    error.value = null
    
    try {
      const response = await queueApi.getQueueStats()
      
      // 检测是否有变化
      const hasChange = 
        stats.value.pending !== (response.stats.pending || 0) ||
        stats.value.processing !== (response.stats.processing || 0) ||
        stats.value.completed !== (response.stats.completed || 0) ||
        stats.value.failed !== (response.stats.failed || 0) ||
        stats.value.cancelled !== (response.stats.cancelled || 0)
      
      // 更新统计
      stats.value = {
        pending: response.stats.pending || 0,
        processing: response.stats.processing || 0,
        completed: response.stats.completed || 0,
        failed: response.stats.failed || 0,
        cancelled: response.stats.cancelled || 0,
      }
      total.value = response.total
      lastUpdate.value = response.timestamp
      
      // 自适应轮询间隔
      if (hasChange) {
        // 有变化，重置为基础间隔
        consecutiveNoChange = 0
        if (currentInterval !== baseInterval) {
          currentInterval = baseInterval
          // 重新启动定时器（如果正在自动刷新）
          if (autoRefresh.value && refreshTimer) {
            clearInterval(refreshTimer)
            refreshTimer = window.setInterval(() => {
              fetchStats()
            }, currentInterval)
          }
        }
      } else {
        // 无变化，逐渐增加间隔
        consecutiveNoChange++
        if (consecutiveNoChange >= 3) { // 连续3次无变化
          const newInterval = Math.min(currentInterval * 1.5, maxInterval)
          if (newInterval !== currentInterval) {
            currentInterval = newInterval
            // 重新启动定时器
            if (autoRefresh.value && refreshTimer) {
              clearInterval(refreshTimer)
              refreshTimer = window.setInterval(() => {
                fetchStats()
              }, currentInterval)
            }
          }
          consecutiveNoChange = 0 // 重置计数
        }
      }
      
      return response
    } catch (err: any) {
      error.value = err.message || '获取队列统计失败'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 启动自动刷新（智能轮询）
   */
  function startAutoRefresh(interval: number = baseInterval) {
    if (autoRefresh.value) return
    
    autoRefresh.value = true
    currentInterval = interval
    consecutiveNoChange = 0
    
    // 立即获取一次
    fetchStats()
    
    // 设置定时刷新
    refreshTimer = window.setInterval(() => {
      fetchStats()
    }, currentInterval)
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
    currentInterval = baseInterval
    consecutiveNoChange = 0
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

