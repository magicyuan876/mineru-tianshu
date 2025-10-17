/**
 * 任务相关 API
 */
import apiClient from './client'
import type {
  SubmitTaskRequest,
  SubmitTaskResponse,
  TaskStatusResponse,
  TaskListResponse,
  ApiResponse,
  TaskStatus,
} from './types'

/**
 * 提交任务
 */
export async function submitTask(request: SubmitTaskRequest): Promise<SubmitTaskResponse> {
  const formData = new FormData()
  formData.append('file', request.file)
  formData.append('backend', request.backend || 'pipeline')
  formData.append('lang', request.lang || 'ch')
  formData.append('method', request.method || 'auto')
  formData.append('formula_enable', String(request.formula_enable ?? true))
  formData.append('table_enable', String(request.table_enable ?? true))
  formData.append('priority', String(request.priority || 0))

  const response = await apiClient.post<SubmitTaskResponse>(
    '/api/v1/tasks/submit',
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }
  )
  return response.data
}

/**
 * 查询任务状态
 */
export async function getTaskStatus(
  taskId: string,
  uploadImages: boolean = false
): Promise<TaskStatusResponse> {
  const response = await apiClient.get<TaskStatusResponse>(
    `/api/v1/tasks/${taskId}`,
    {
      params: { upload_images: uploadImages },
    }
  )
  return response.data
}

/**
 * 取消任务
 */
export async function cancelTask(taskId: string): Promise<ApiResponse> {
  const response = await apiClient.delete<ApiResponse>(`/api/v1/tasks/${taskId}`)
  return response.data
}

/**
 * 获取任务列表
 */
export async function listTasks(
  status?: TaskStatus,
  limit: number = 100
): Promise<TaskListResponse> {
  const response = await apiClient.get<TaskListResponse>('/api/v1/queue/tasks', {
    params: { status, limit },
  })
  return response.data
}

