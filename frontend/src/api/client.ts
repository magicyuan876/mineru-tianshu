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

