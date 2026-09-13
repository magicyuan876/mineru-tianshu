/**
 * 认证 API
 */
import { apiClient } from './client'
import type {
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  PasswordChangeRequest,
  User,
  APIKeyCreate,
  APIKeyResponse,
  APIKeyListResponse,
  APIKeyWebhookConfig,
  APIKeyWebhookResponse,
  AdminAPIKeyListResponse,
  WebhookTestResult,
} from './types'

/**
 * 用户登录
 */
export async function login(credentials: LoginRequest): Promise<LoginResponse> {
  const response = await apiClient.post<LoginResponse>('/api/v1/auth/login', credentials)
  return response.data
}

/**
 * 用户注册
 */
export async function register(userData: RegisterRequest): Promise<User> {
  const response = await apiClient.post<User>('/api/v1/auth/register', userData)
  return response.data
}

/**
 * 用户登出（通知后端吊销当前 Token）
 */
export async function logout(): Promise<void> {
  await apiClient.post('/api/v1/auth/logout')
}

/**
 * 获取当前用户信息
 */
export async function getCurrentUser(): Promise<User> {
  const response = await apiClient.get<User>('/api/v1/auth/me')
  return response.data
}

/**
 * 更新当前用户信息
 */
export async function updateCurrentUser(data: Partial<User>): Promise<User> {
  const response = await apiClient.patch<User>('/api/v1/auth/me', data)
  return response.data
}

/**
 * 修改密码
 */
export async function changePassword(data: PasswordChangeRequest): Promise<void> {
  await apiClient.post('/api/v1/auth/me/change-password', data)
}

/**
 * 创建 API Key
 */
export async function createAPIKey(data: APIKeyCreate): Promise<APIKeyResponse> {
  const response = await apiClient.post<APIKeyResponse>('/api/v1/auth/apikeys', data)
  return response.data
}

/**
 * 获取 API Key 列表
 */
export async function getAPIKeys(): Promise<APIKeyListResponse> {
  const response = await apiClient.get<APIKeyListResponse>('/api/v1/auth/apikeys')
  return response.data
}

/**
 * 删除 API Key
 */
export async function deleteAPIKey(keyId: string): Promise<void> {
  await apiClient.delete(`/api/v1/auth/apikeys/${keyId}`)
}

/**
 * 读取 Key 级 Webhook 回调配置（敏感字段为掩码）
 */
export async function getAPIKeyWebhook(keyId: string): Promise<APIKeyWebhookResponse> {
  const response = await apiClient.get<APIKeyWebhookResponse>(`/api/v1/auth/apikeys/${keyId}/webhook`)
  return response.data
}

/**
 * 更新 Key 级 Webhook 回调配置（掩码/缺省表示保持原值）
 */
export async function updateAPIKeyWebhook(
  keyId: string,
  data: APIKeyWebhookConfig
): Promise<APIKeyWebhookResponse> {
  const response = await apiClient.put<APIKeyWebhookResponse>(`/api/v1/auth/apikeys/${keyId}/webhook`, data)
  return response.data
}

/**
 * 获取全部 API Key 列表（管理员，含归属用户与回调配置摘要）
 */
export async function getAllAPIKeys(): Promise<AdminAPIKeyListResponse> {
  const response = await apiClient.get<AdminAPIKeyListResponse>('/api/v1/auth/admin/apikeys')
  return response.data
}

/**
 * 用该 Key 已保存的回调配置投递一条测试通知
 */
export async function testAPIKeyWebhook(keyId: string): Promise<WebhookTestResult> {
  const response = await apiClient.post<WebhookTestResult>(`/api/v1/auth/apikeys/${keyId}/webhook/test`)
  return response.data
}

/**
 * 获取所有用户列表 (管理员)
 */
export async function getAllUsers(): Promise<User[]> {
  const response = await apiClient.get<User[]>('/api/v1/auth/users')
  return response.data
}

/**
 * 创建用户 (管理员)
 */
export async function createUser(userData: RegisterRequest): Promise<User> {
  const response = await apiClient.post<User>('/api/v1/auth/users', userData)
  return response.data
}

/**
 * 更新用户 (管理员)
 */
export async function updateUser(userId: string, data: Partial<User>): Promise<User> {
  const response = await apiClient.patch<User>(`/api/v1/auth/users/${userId}`, data)
  return response.data
}

/**
 * 删除用户 (管理员)
 */
export async function deleteUser(userId: string): Promise<void> {
  await apiClient.delete(`/api/v1/auth/users/${userId}`)
}

/**
 * 检查 SSO 状态
 */
export async function getSSOStatus(): Promise<{ enabled: boolean; type: string | null }> {
  const response = await apiClient.get<{ enabled: boolean; type: string | null }>(
    '/api/v1/auth/sso/enabled'
  )
  return response.data
}
