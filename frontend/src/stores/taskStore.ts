/**
 * 任务状态管理 Store
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { taskApi } from '@/api'
// ✅ 修复：导入 TaskStatus 类型
import type { Task, SubmitTaskRequest, TaskQueryParams, TaskStatus } from '@/api/types'

export const useTaskStore = defineStore('task', () => {
  // ----------------------------------------------------------------
  // State (状态)
  // ----------------------------------------------------------------
  const tasks = ref<Task[]>([])
  const total = ref(0)
  const currentTask = ref<Task | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // ----------------------------------------------------------------
  // Getters (计算属性)
  // ----------------------------------------------------------------
  const pendingTasks = computed(() => tasks.value.filter(t => t.status === 'pending'))
  const processingTasks = computed(() => tasks.value.filter(t => t.status === 'processing'))
  const completedTasks = computed(() => tasks.value.filter(t => t.status === 'completed'))
  const failedTasks = computed(() => tasks.value.filter(t => t.status === 'failed'))

  // ----------------------------------------------------------------
  // Actions (动作)
  // ----------------------------------------------------------------

  /**
   * 提交任务
   */
  async function submitTask(request: SubmitTaskRequest) {
    loading.value = true
    error.value = null
    try {
      const response = await taskApi.submitTask(request)
      // 乐观更新：添加到列表顶部
      const newTask: Task = {
        task_id: response.task_id,
        file_name: response.file_name,
        status: response.status,
        backend: request.backend || 'pipeline',
        priority: request.priority || 0,
        error_message: null,
        created_at: response.created_at,
        started_at: null,
        completed_at: null,
        worker_id: null,
        retry_count: 0,
        result_path: null,
      }
      tasks.value.unshift(newTask)
      total.value += 1
      return response
    } catch (err: any) {
      error.value = err.message || '提交任务失败'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 获取任务列表
   */
  async function fetchTasks(params: TaskQueryParams) {
    loading.value = true
    error.value = null
    try {
      const response = await taskApi.listTasks(params)
      tasks.value = response.tasks
      total.value = response.total
      return response
    } catch (err: any) {
      error.value = err.message || '获取任务列表失败'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 获取单任务详情
   */
  async function fetchTaskStatus(taskId: string, uploadImages = false, format: 'markdown' | 'json' | 'both' = 'markdown') {
    // 仅当首次加载或强制刷新时显示 loading，避免轮询闪烁
    if (!currentTask.value || currentTask.value.task_id !== taskId) {
       loading.value = true
    }
    error.value = null

    try {
      const response = await taskApi.getTaskStatus(taskId, uploadImages, format)
      
      const updatedTask: Task = {
        ...response, // 自动展开 API 响应中的所有字段
        result_path: response.result_path || null
      }

      currentTask.value = updatedTask

      // 同步更新列表中的状态，保持数据一致性
      const index = tasks.value.findIndex(t => t.task_id === taskId)
      if (index !== -1) {
        tasks.value[index] = { ...tasks.value[index], ...updatedTask }
      }
      return response
    } catch (err: any) {
      error.value = err.message || '获取任务详情失败'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 取消任务
   */
  async function cancelTask(taskId: string) {
    try {
      await taskApi.cancelTask(taskId)
      // 本地状态更新
      updateLocalTaskStatus(taskId, 'cancelled')
    } catch (err: any) {
      error.value = err.message || '取消任务失败'
      throw err
    }
  }

  // =================================================================
  // 新增核心 Action：重试、暂停、恢复、清理
  // =================================================================

  /**
   * 重试任务
   */
  async function retryTask(taskId: string) {
    try {
      await taskApi.retryTask(taskId)
      // 重试后状态变为 pending，清除错误信息
      const task = tasks.value.find(t => t.task_id === taskId)
      if (task) {
        task.status = 'pending'
        task.error_message = null
      }
      if (currentTask.value?.task_id === taskId) {
        currentTask.value.status = 'pending'
        currentTask.value.error_message = null
      }
    } catch (err: any) {
      error.value = err.message || '重试任务失败'
      throw err
    }
  }

  /**
   * 暂停任务
   */
  async function pauseTask(taskId: string) {
    try {
      await taskApi.pauseTask(taskId)
      updateLocalTaskStatus(taskId, 'paused')
    } catch (err: any) {
      error.value = err.message || '暂停任务失败'
      throw err
    }
  }

  /**
   * 恢复任务
   */
  async function resumeTask(taskId: string) {
    try {
      await taskApi.resumeTask(taskId)
      updateLocalTaskStatus(taskId, 'pending')
    } catch (err: any) {
      error.value = err.message || '恢复任务失败'
      throw err
    }
  }

  /**
   * 清理任务缓存
   */
  async function clearTaskCache(taskId: string) {
    try {
      await taskApi.clearTaskCache(taskId)
      // 更新本地状态标记
      const task = tasks.value.find(t => t.task_id === taskId)
      if (task) task.result_path = 'CLEARED'
      if (currentTask.value?.task_id === taskId) currentTask.value.result_path = 'CLEARED'
    } catch (err: any) {
      error.value = err.message || '清理缓存失败'
      throw err
    }
  }

  /**
   * 一键清理失败任务
   */
  async function clearFailedTasks() {
    try {
      const res = await taskApi.clearFailedTasks()
      // 从本地列表中移除 failed 状态的任务
      tasks.value = tasks.value.filter(t => t.status !== 'failed')
      // 更新总数 (防止分页数据不准)
      total.value = Math.max(0, total.value - res.deleted_count)
    } catch (err: any) {
      error.value = err.message || '清理失败任务失败'
      throw err
    }
  }

  // ----------------------------------------------------------------
  // 辅助函数
  // ----------------------------------------------------------------

  /**
   * 辅助：更新本地任务状态
   * ✅ 修复：将 status 参数类型从 string 改为 TaskStatus
   */
  function updateLocalTaskStatus(taskId: string, status: TaskStatus) {
    const task = tasks.value.find(t => t.task_id === taskId)
    if (task) task.status = status
    if (currentTask.value?.task_id === taskId) currentTask.value.status = status
  }

  /**
   * 轮询逻辑
   */
  function pollTaskStatus(taskId: string, interval = 2000, onUpdate?: (task: Task) => void) {
    let timerId: number | null = null
    let stopped = false

    const poll = async () => {
      if (stopped) return
      try {
        await fetchTaskStatus(taskId)
        if (currentTask.value && onUpdate) onUpdate(currentTask.value)
        
        const status = currentTask.value?.status
        if (['completed', 'failed', 'cancelled'].includes(status || '')) {
          stopped = true
          return
        }
        if (!stopped) timerId = window.setTimeout(poll, interval)
      } catch (err) {
        // 出错停止轮询，防止无限报错
        stopped = true
      }
    }
    
    poll()
    return () => { stopped = true; if (timerId) clearTimeout(timerId) }
  }

  /**
   * 清空错误
   */
  function clearError() {
    error.value = null
  }

  function reset() {
    tasks.value = []
    total.value = 0
    currentTask.value = null
    loading.value = false
    error.value = null
  }

  return {
    tasks,
    total,
    currentTask,
    loading,
    error,
    pendingTasks,
    processingTasks,
    completedTasks,
    failedTasks,
    submitTask,
    fetchTaskStatus,
    fetchTasks,
    cancelTask,
    retryTask,      
    pauseTask,      
    resumeTask,     
    clearTaskCache, 
    clearFailedTasks,
    pollTaskStatus,
    clearError,
    reset
  }
})
