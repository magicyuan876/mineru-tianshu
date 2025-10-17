/**
 * 队列管理 API
 */
import apiClient from './client'
import type { QueueStatsResponse, ApiResponse } from './types'

/**
 * 获取队列统计
 */
export async function getQueueStats(): Promise<QueueStatsResponse> {
  const response = await apiClient.get<QueueStatsResponse>('/api/v1/queue/stats')
  return response.data
}

/**
 * 重置超时任务
 */
export async function resetStaleTasks(timeoutMinutes: number = 60): Promise<ApiResponse> {
  const response = await apiClient.post<ApiResponse>('/api/v1/admin/reset-stale', null, {
    params: { timeout_minutes: timeoutMinutes },
  })
  return response.data
}

/**
 * 清理旧任务
 */
export async function cleanupOldTasks(days: number = 7): Promise<ApiResponse> {
  const response = await apiClient.post<ApiResponse>('/api/v1/admin/cleanup', null, {
    params: { days },
  })
  return response.data
}

/**
 * 健康检查
 */
export async function healthCheck(): Promise<ApiResponse> {
  const response = await apiClient.get<ApiResponse>('/api/v1/health')
  return response.data
}

