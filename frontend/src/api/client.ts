/**
 * API 客户端配置
 */
import axios, { AxiosInstance } from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

// 创建 axios 实例
export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000, // 5 分钟超时
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    // 添加 Token 到请求头
    const token = localStorage.getItem('auth_token')
    if (token) {
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

// 响应拦截器
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
        // 清除 Token
        localStorage.removeItem('auth_token')

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
