<template>
  <div class="max-w-7xl mx-auto">
    <div class="flex justify-between items-center mb-8">
      <h1 class="text-3xl font-bold text-gray-900">用户管理</h1>
      <button
        @click="showCreateDialog = true"
        class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
      >
        创建用户
      </button>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="flex justify-center py-12">
      <LoadingSpinner />
    </div>

    <!-- 用户列表 -->
    <div v-else class="bg-white rounded-lg shadow-md overflow-hidden">
      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                用户
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                邮箱
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                角色
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                状态
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                创建时间
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                最后登录
              </th>
              <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                操作
              </th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            <tr v-for="user in users" :key="user.user_id" class="hover:bg-gray-50">
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="flex items-center">
                  <div class="flex-shrink-0 h-10 w-10">
                    <div class="h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center">
                      <User class="h-5 w-5 text-blue-600" />
                    </div>
                  </div>
                  <div class="ml-4">
                    <div class="text-sm font-medium text-gray-900">{{ user.username }}</div>
                    <div v-if="user.full_name" class="text-sm text-gray-500">{{ user.full_name }}</div>
                  </div>
                </div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm text-gray-900">{{ user.email }}</div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <span
                  :class="{
                    'bg-red-100 text-red-800': user.role === 'admin',
                    'bg-yellow-100 text-yellow-800': user.role === 'manager',
                    'bg-blue-100 text-blue-800': user.role === 'user',
                  }"
                  class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full"
                >
                  {{ roleLabel(user.role) }}
                </span>
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <span
                  :class="user.is_active ? 'text-green-600' : 'text-red-600'"
                  class="px-2 inline-flex text-xs leading-5 font-semibold"
                >
                  {{ user.is_active ? '激活' : '禁用' }}
                </span>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {{ formatDate(user.created_at) }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {{ user.last_login ? formatDate(user.last_login) : '从未' }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                <div class="flex items-center justify-end gap-2">
                  <button
                    @click="editUser(user)"
                    class="text-blue-600 hover:text-blue-900"
                    title="编辑"
                  >
                    <Edit2 class="w-4 h-4" />
                  </button>
                  <button
                    v-if="user.user_id !== authStore.user?.user_id"
                    @click="confirmDelete(user)"
                    class="text-red-600 hover:text-red-900"
                    title="删除"
                  >
                    <Trash2 class="w-4 h-4" />
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 空状态 -->
      <div v-if="users.length === 0" class="text-center py-12 text-gray-500">
        <User class="w-12 h-12 mx-auto mb-4 text-gray-400" />
        <p>暂无用户</p>
      </div>
    </div>

    <!-- 创建用户对话框 -->
    <div
      v-if="showCreateDialog"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      @click.self="showCreateDialog = false"
    >
      <div class="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
        <h3 class="text-lg font-semibold text-gray-900 mb-4">创建新用户</h3>

        <form @submit.prevent="handleCreate" class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">用户名</label>
            <input
              v-model="createForm.username"
              type="text"
              required
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">邮箱</label>
            <input
              v-model="createForm.email"
              type="email"
              required
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">密码</label>
            <input
              v-model="createForm.password"
              type="password"
              required
              minlength="6"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">全名（可选）</label>
            <input
              v-model="createForm.full_name"
              type="text"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">角色</label>
            <select
              v-model="createForm.role"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="user">普通用户</option>
              <option value="manager">管理者</option>
              <option value="admin">管理员</option>
            </select>
          </div>

          <div class="flex gap-3 pt-4">
            <button
              type="submit"
              :disabled="submitting"
              class="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {{ submitting ? '创建中...' : '创建' }}
            </button>
            <button
              type="button"
              @click="showCreateDialog = false"
              class="flex-1 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
            >
              取消
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- 编辑用户对话框 -->
    <div
      v-if="showEditDialog"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      @click.self="showEditDialog = false"
    >
      <div class="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
        <h3 class="text-lg font-semibold text-gray-900 mb-4">编辑用户</h3>

        <form @submit.prevent="handleUpdate" class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">用户名</label>
            <input
              :value="editForm.username"
              type="text"
              disabled
              class="w-full px-3 py-2 bg-gray-50 border border-gray-300 rounded-lg text-gray-500 cursor-not-allowed"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">邮箱</label>
            <input
              v-model="editForm.email"
              type="email"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">全名</label>
            <input
              v-model="editForm.full_name"
              type="text"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">角色</label>
            <select
              v-model="editForm.role"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="user">普通用户</option>
              <option value="manager">管理者</option>
              <option value="admin">管理员</option>
            </select>
          </div>

          <div>
            <label class="flex items-center gap-2">
              <input
                v-model="editForm.is_active"
                type="checkbox"
                class="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span class="text-sm font-medium text-gray-700">账户激活</span>
            </label>
          </div>

          <div class="flex gap-3 pt-4">
            <button
              type="submit"
              :disabled="submitting"
              class="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {{ submitting ? '保存中...' : '保存' }}
            </button>
            <button
              type="button"
              @click="showEditDialog = false"
              class="flex-1 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
            >
              取消
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- 删除确认对话框 -->
    <ConfirmDialog
      :model-value="!!deleteTarget"
      title="删除用户"
      :message="`确定要删除用户「${deleteTarget?.username}」吗？此操作无法撤销。`"
      confirm-text="删除"
      cancel-text="取消"
      @confirm="handleDelete"
      @cancel="deleteTarget = null"
      @update:model-value="(v) => { if (!v) deleteTarget = null }"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { User, Edit2, Trash2 } from 'lucide-vue-next'
import { useAuthStore } from '@/stores'
import * as authApi from '@/api/authApi'
import type { User as UserType } from '@/api/types'
import { formatDate } from '@/utils/format'
import { showToast } from '@/utils/toast'
import LoadingSpinner from '@/components/LoadingSpinner.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'

const authStore = useAuthStore()
const loading = ref(false)
const submitting = ref(false)
const users = ref<UserType[]>([])
const showCreateDialog = ref(false)
const showEditDialog = ref(false)
const deleteTarget = ref<UserType | null>(null)

const createForm = ref({
  username: '',
  email: '',
  password: '',
  full_name: '',
  role: 'user' as 'user' | 'manager' | 'admin',
})

const editForm = ref({
  user_id: '',
  username: '',
  email: '',
  full_name: '',
  role: 'user' as 'user' | 'manager' | 'admin',
  is_active: true,
})

function roleLabel(role: string) {
  const labels = {
    admin: '管理员',
    manager: '管理者',
    user: '普通用户',
  }
  return labels[role as keyof typeof labels] || role
}

// 加载用户列表
async function loadUsers() {
  try {
    loading.value = true
    users.value = await authApi.getAllUsers()
  } catch (error: any) {
    console.error('Failed to load users:', error)
    showToast({ message: '加载用户列表失败', type: 'error' })
  } finally {
    loading.value = false
  }
}

// 创建用户
async function handleCreate() {
  try {
    submitting.value = true
    await authApi.createUser(createForm.value)
    showToast({ message: '用户创建成功', type: 'success' })
    showCreateDialog.value = false
    createForm.value = {
      username: '',
      email: '',
      password: '',
      full_name: '',
      role: 'user',
    }
    await loadUsers()
  } catch (error: any) {
    console.error('Failed to create user:', error)
    const message = error.response?.data?.detail || '创建用户失败'
    showToast({ message, type: 'error' })
  } finally {
    submitting.value = false
  }
}

// 编辑用户
function editUser(user: UserType) {
  editForm.value = {
    user_id: user.user_id,
    username: user.username,
    email: user.email,
    full_name: user.full_name || '',
    role: user.role,
    is_active: user.is_active,
  }
  showEditDialog.value = true
}

// 更新用户
async function handleUpdate() {
  try {
    submitting.value = true
    await authApi.updateUser(editForm.value.user_id, {
      email: editForm.value.email,
      full_name: editForm.value.full_name || undefined,
      role: editForm.value.role,
      is_active: editForm.value.is_active,
    })
    showToast({ message: '用户信息已更新', type: 'success' })
    showEditDialog.value = false
    await loadUsers()
  } catch (error: any) {
    console.error('Failed to update user:', error)
    const message = error.response?.data?.detail || '更新用户失败'
    showToast({ message, type: 'error' })
  } finally {
    submitting.value = false
  }
}

// 确认删除
function confirmDelete(user: UserType) {
  deleteTarget.value = user
}

// 删除用户
async function handleDelete() {
  if (!deleteTarget.value) return

  try {
    await authApi.deleteUser(deleteTarget.value.user_id)
    showToast({ message: '用户已删除', type: 'success' })
    deleteTarget.value = null
    await loadUsers()
  } catch (error: any) {
    console.error('Failed to delete user:', error)
    const message = error.response?.data?.detail || '删除用户失败'
    showToast({ message, type: 'error' })
  }
}

onMounted(() => {
  loadUsers()
})
</script>
