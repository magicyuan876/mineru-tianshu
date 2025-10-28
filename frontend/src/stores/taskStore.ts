/**
 * 任务状态管理
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { taskApi } from '@/api'
import type { Task, SubmitTaskRequest, TaskStatus } from '@/api/types'

export const useTaskStore = defineStore('task', () => {
  // 状态
  const tasks = ref<Task[]>([])
  const currentTask = ref<Task | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // 计算属性
  const pendingTasks = computed(() =>
    tasks.value.filter(t => t.status === 'pending')
  )

  const processingTasks = computed(() =>
    tasks.value.filter(t => t.status === 'processing')
  )

  const completedTasks = computed(() =>
    tasks.value.filter(t => t.status === 'completed')
  )

  const failedTasks = computed(() =>
    tasks.value.filter(t => t.status === 'failed')
  )

  // 动作
  /**
   * 提交任务
   */
  async function submitTask(request: SubmitTaskRequest) {
    loading.value = true
    error.value = null

    try {
      const response = await taskApi.submitTask(request)

      // 添加到任务列表
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
      return response
    } catch (err: any) {
      error.value = err.message || '提交任务失败'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 获取任务状态
   */
  async function fetchTaskStatus(
    taskId: string,
    uploadImages: boolean = false,
    format: 'markdown' | 'json' | 'both' = 'markdown'
  ) {
    loading.value = true
    error.value = null

    try {
      const response = await taskApi.getTaskStatus(taskId, uploadImages, format)
      currentTask.value = {
        task_id: response.task_id,
        file_name: response.file_name,
        status: response.status,
        backend: response.backend,
        priority: response.priority,
        error_message: response.error_message,
        created_at: response.created_at,
        started_at: response.started_at,
        completed_at: response.completed_at,
        worker_id: response.worker_id,
        retry_count: response.retry_count,
        result_path: null,
        data: response.data,
      }

      // 更新任务列表中的任务
      const index = tasks.value.findIndex(t => t.task_id === taskId)
      if (index !== -1) {
        tasks.value[index] = currentTask.value
      }

      return response
    } catch (err: any) {
      error.value = err.message || '获取任务状态失败'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 取消任务
   */
  async function cancelTask(taskId: string) {
    loading.value = true
    error.value = null

    try {
      await taskApi.cancelTask(taskId)

      // 更新任务状态
      const task = tasks.value.find(t => t.task_id === taskId)
      if (task) {
        task.status = 'cancelled'
      }

      if (currentTask.value?.task_id === taskId) {
        currentTask.value.status = 'cancelled'
      }
    } catch (err: any) {
      error.value = err.message || '取消任务失败'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 获取任务列表
   */
  async function fetchTasks(status?: TaskStatus, limit: number = 100) {
    loading.value = true
    error.value = null

    try {
      const response = await taskApi.listTasks(status, limit)
      tasks.value = response.tasks
      return response
    } catch (err: any) {
      error.value = err.message || '获取任务列表失败'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 轮询任务状态
   */
  function pollTaskStatus(
    taskId: string,
    interval: number = 2000,
    onUpdate?: (task: Task) => void,
    format: 'markdown' | 'json' | 'both' = 'markdown'
  ): () => void {
    let timerId: number | null = null
    let stopped = false

    const poll = async () => {
      if (stopped) return

      try {
        const response = await fetchTaskStatus(taskId, false, format)

        if (onUpdate && currentTask.value) {
          onUpdate(currentTask.value)
        }

        // 如果任务完成或失败，停止轮询
        if (response.status === 'completed' || response.status === 'failed' || response.status === 'cancelled') {
          stopped = true
          return
        }

        // 继续轮询
        if (!stopped) {
          timerId = window.setTimeout(poll, interval)
        }
      } catch (err) {
        console.error('轮询任务状态失败:', err)
        // 发生错误时也停止轮询
        stopped = true
      }
    }

    // 开始轮询
    poll()

    // 返回停止函数
    return () => {
      stopped = true
      if (timerId) {
        clearTimeout(timerId)
        timerId = null
      }
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
    tasks.value = []
    currentTask.value = null
    loading.value = false
    error.value = null
  }

  return {
    // 状态
    tasks,
    currentTask,
    loading,
    error,

    // 计算属性
    pendingTasks,
    processingTasks,
    completedTasks,
    failedTasks,

    // 动作
    submitTask,
    fetchTaskStatus,
    cancelTask,
    fetchTasks,
    pollTaskStatus,
    clearError,
    reset,
  }
})
