/**
 * API 客户端配置
 */
import axios, { AxiosInstance } from 'axios'

/**
 * 获取 API Base URL
 *
 * 优先级：
 * 1. 环境变量 VITE_API_BASE_URL
 * 2. 生产环境：使用当前域名 + 8000 端口
 * 3. 开发环境：http://localhost:8000
 */
function getApiBaseUrl(): string {
  let baseUrl = ''

  // 1. 优先使用环境变量
  if (import.meta.env.VITE_API_BASE_URL) {
    baseUrl = import.meta.env.VITE_API_BASE_URL
  }
  // 2. 生产环境：自动使用当前域名 + 后端端口
  else if (import.meta.env.PROD) {
    const protocol = window.location.protocol // http: or https:
    const hostname = window.location.hostname // 域名或 IP
    const apiPort = import.meta.env.VITE_API_PORT || '8000' // 后端端口，默认 8000
    baseUrl = `${protocol}//${hostname}:${apiPort}`
  }
  // 3. 开发环境：使用 localhost
  else {
    baseUrl = 'http://localhost:8000'
  }

  // ✅ [核心修复]：把 BaseURL 洗得干干净净，只留纯域名！
  // 坚决不在这里加 /api/v1，防止和请求路径发生双重拼接
  return baseUrl
    .replace(/\/+$/, '')         // 移除末尾所有斜杠
    .replace(/\/api\/v1$/, '')   // 剥离 /api/v1
    .replace(/\/v1$/, '')        // 剥离 /v1
    .replace(/\/api$/, '')       // 剥离 /api
}

const API_BASE_URL = getApiBaseUrl()

// 创建 axios 实例
export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000, // 5 分钟超时，适应大文件长耗时任务
  headers: {
    'Content-Type': 'application/json',
  },
})

// 打印 API Base URL（方便调试）
console.log('🌐 Clean API Base URL:', API_BASE_URL)

// ==========================================
// 请求拦截器
// ==========================================
apiClient.interceptors.request.use(
  (config) => {
    // ✅ [核心修复 Bug 1]：动态清洗请求路径，终结 /api/v1/api/v1 的惨剧
    if (config.url && !config.url.startsWith('http')) {
      // 1. 去掉开头的斜杠
      let cleanUrl = config.url.replace(/^\/+/, '')

      // 2. 无情剥离代码里可能硬编码的冗余前缀
      cleanUrl = cleanUrl.replace(/^(api\/v1\/|api\/|v1\/)/, '')

      // 3. 强制、唯一地组合为标准的绝对 API 路径
      config.url = `/api/v1/${cleanUrl}`
    }

    // ✅ 兼容处理：可能存的是 auth_token，也可能存的是 token，做个兜底
    const token = localStorage.getItem('auth_token') || localStorage.getItem('token')

    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }

    // 调试：打印请求参数
    if (config.url?.includes('/tasks/')) {
      console.log('API Request:', config.method?.toUpperCase(), config.url, 'params:', config.params)
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// ==========================================
// 响应拦截器
// ==========================================
apiClient.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    if (error.response) {
      // 服务器返回错误
      console.error('API Error:', error.response.status, error.response.data)

      // 401 未授权 - Token 可能已过期
      if (error.response.status === 401) {
        // 清除 Token (双重清除防遗漏)
        localStorage.removeItem('auth_token')
        localStorage.removeItem('token')

        // 如果不是登录/注册页面，跳转到登录页
        if (!window.location.pathname.includes('/login') && !window.location.pathname.includes('/register')) {
          window.location.href = '/login'
        }
      }

      // 403 权限不足
      if (error.response.status === 403) {
        console.error('Permission denied:', error.response.data.detail)
      }
    } else if (error.request) {
      // 请求发送但没有响应
      console.error('Network Error:', error.message)
    } else {
      // 其他错误
      console.error('Error:', error.message)
    }
    return Promise.reject(error)
  }
)

export default apiClient
