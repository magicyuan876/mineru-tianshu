/**
 * API 类型定义
 */

// 任务状态
export type TaskStatus = 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled'

// 后端类型
export type Backend = 'pipeline' | 'vlm-transformers' | 'vlm-vllm-engine' | 'deepseek-ocr' | 'paddleocr-vl' | 'sensevoice' | 'video'

// 语言类型
export type Language = 'auto' | 'ch' | 'en' | 'korean' | 'japan'

// 解析方法
export type ParseMethod = 'auto' | 'txt' | 'ocr'

// 任务配置选项
export interface TaskOptions {
  lang: Language
  method: ParseMethod
  formula_enable: boolean
  table_enable: boolean
}

// 任务提交请求
export interface SubmitTaskRequest {
  file: File
  backend?: Backend
  lang?: Language
  method?: ParseMethod
  formula_enable?: boolean
  table_enable?: boolean
  priority?: number
  // DeepSeek OCR 专属参数
  deepseek_resolution?: string
  deepseek_prompt_type?: string
  deepseek_cache_dir?: string
  // Video 专属参数
  keep_audio?: boolean
  enable_keyframe_ocr?: boolean
  ocr_backend?: string
  keep_keyframes?: boolean
  // 水印去除参数
  remove_watermark?: boolean
  watermark_conf_threshold?: number
  watermark_dilation?: number
}

// 任务信息
export interface Task {
  task_id: string
  file_name: string
  status: TaskStatus
  backend: Backend
  priority: number
  error_message: string | null
  created_at: string
  started_at: string | null
  completed_at: string | null
  worker_id: string | null
  retry_count: number
  result_path: string | null
  data?: {
    markdown_file: string
    content: string
    images_uploaded: boolean
    has_images: boolean | null
    json_file?: string
    json_content?: any
    json_available?: boolean
  } | null
}

// 任务提交响应
export interface SubmitTaskResponse {
  success: boolean
  task_id: string
  status: TaskStatus
  message: string
  file_name: string
  created_at: string
}

// 任务状态响应
export interface TaskStatusResponse {
  success: boolean
  task_id: string
  status: TaskStatus
  file_name: string
  backend: Backend
  priority: number
  error_message: string | null
  created_at: string
  started_at: string | null
  completed_at: string | null
  worker_id: string | null
  retry_count: number
  data?: {
    markdown_file: string
    content: string
    images_uploaded: boolean
    has_images: boolean | null
    json_file?: string
    json_content?: any
    json_available?: boolean
  } | null
  message?: string
}

// 队列统计
export interface QueueStats {
  pending: number
  processing: number
  completed: number
  failed: number
  cancelled: number
}

// 队列统计响应
export interface QueueStatsResponse {
  success: boolean
  stats: QueueStats
  total: number
  timestamp: string
}

// 任务列表响应
export interface TaskListResponse {
  success: boolean
  count: number
  tasks: Task[]
}

// 通用响应
export interface ApiResponse<T = any> {
  success: boolean
  message?: string
  data?: T
}

