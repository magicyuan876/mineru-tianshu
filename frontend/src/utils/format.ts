/**
 * 格式化工具函数
 */
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import utc from 'dayjs/plugin/utc'
import timezone from 'dayjs/plugin/timezone'
import 'dayjs/locale/zh-cn'

dayjs.extend(relativeTime)
dayjs.extend(utc)
dayjs.extend(timezone)
dayjs.locale('zh-cn')

/**
 * 格式化日期时间
 * 将 UTC 时间转换为本地时间显示
 */
export function formatDateTime(date: string | null | undefined): string {
  if (!date) return '-'
  // 后端返回的是 UTC 时间，需要转换为本地时间
  return dayjs.utc(date).local().format('YYYY-MM-DD HH:mm:ss')
}

/**
 * 格式化日期（简化版，用于用户信息等场景）
 */
export function formatDate(date: string | null | undefined): string {
  if (!date) return '-'
  // 后端返回的是 UTC 时间，需要转换为本地时间
  return dayjs.utc(date).local().format('YYYY-MM-DD HH:mm:ss')
}

/**
 * 格式化相对时间
 */
export function formatRelativeTime(date: string | null | undefined): string {
  if (!date) return '-'
  // 后端返回的是 UTC 时间，需要转换为本地时间
  return dayjs.utc(date).local().fromNow()
}

/**
 * 格式化文件大小
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B'

  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))

  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

/**
 * 格式化持续时间
 */
export function formatDuration(startTime: string | null, endTime: string | null): string {
  if (!startTime || !endTime) return '-'

  // 后端返回的是 UTC 时间
  const start = dayjs.utc(startTime)
  const end = dayjs.utc(endTime)
  const seconds = end.diff(start, 'second')

  if (seconds < 60) {
    return `${seconds}秒`
  } else if (seconds < 3600) {
    const minutes = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${minutes}分${secs}秒`
  } else {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    return `${hours}小时${minutes}分`
  }
}

/**
 * 格式化 Backend 名称
 */
export function formatBackendName(backend: string): string {
  const backendNames: Record<string, string> = {
    'pipeline': 'MinerU Pipeline',
    'deepseek-ocr': 'DeepSeek OCR',
    'paddleocr-vl': 'PaddleOCR-VL',
    'vlm-transformers': 'VLM Transformers',
    'vlm-vllm-engine': 'VLM vLLM Engine',
  }
  return backendNames[backend] || backend
}
