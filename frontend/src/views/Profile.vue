<template>
  <div class="max-w-4xl mx-auto">
    <h1 class="text-3xl font-bold text-gray-900 mb-8">个人资料</h1>

    <!-- 用户信息卡片 -->
    <div class="bg-white rounded-lg shadow-md p-6 mb-6">
      <h2 class="text-xl font-semibold text-gray-900 mb-4">基本信息</h2>

      <div class="space-y-4">
        <!-- 用户名 -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">用户名</label>
          <input
            type="text"
            :value="authStore.user?.username"
            disabled
            class="w-full px-4 py-2 bg-gray-50 border border-gray-300 rounded-lg text-gray-500 cursor-not-allowed"
          />
          <p class="mt-1 text-xs text-gray-500">用户名无法修改</p>
        </div>

        <!-- 邮箱 -->
        <div>
          <label for="email" class="block text-sm font-medium text-gray-700 mb-1">邮箱</label>
          <input
            id="email"
            v-model="form.email"
            type="email"
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        <!-- 全名 -->
        <div>
          <label for="full_name" class="block text-sm font-medium text-gray-700 mb-1">全名</label>
          <input
            id="full_name"
            v-model="form.full_name"
            type="text"
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        <!-- 角色 -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">角色</label>
          <div class="flex items-center">
            <span
              :class="{
                'bg-red-100 text-red-800': authStore.user?.role === 'admin',
                'bg-yellow-100 text-yellow-800': authStore.user?.role === 'manager',
                'bg-blue-100 text-blue-800': authStore.user?.role === 'user',
              }"
              class="px-3 py-1 rounded-full text-sm font-medium"
            >
              {{ roleLabel(authStore.user?.role) }}
            </span>
          </div>
        </div>

        <!-- 更新按钮 -->
        <div class="flex justify-end">
          <button
            @click="handleUpdate"
            :disabled="authStore.loading"
            class="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            保存修改
          </button>
        </div>
      </div>
    </div>

    <!-- 账户信息 -->
    <div class="bg-white rounded-lg shadow-md p-6 mb-6">
      <h2 class="text-xl font-semibold text-gray-900 mb-4">账户信息</h2>

      <div class="space-y-3 text-sm">
        <div class="flex justify-between">
          <span class="text-gray-600">用户 ID:</span>
          <span class="font-mono text-gray-900">{{ authStore.user?.user_id }}</span>
        </div>
        <div class="flex justify-between">
          <span class="text-gray-600">创建时间:</span>
          <span class="text-gray-900">{{ formatDate(authStore.user?.created_at) }}</span>
        </div>
        <div class="flex justify-between">
          <span class="text-gray-600">最后登录:</span>
          <span class="text-gray-900">{{ formatDate(authStore.user?.last_login) || '从未登录' }}</span>
        </div>
        <div class="flex justify-between">
          <span class="text-gray-600">账户状态:</span>
          <span
            :class="authStore.user?.is_active ? 'text-green-600' : 'text-red-600'"
            class="font-medium"
          >
            {{ authStore.user?.is_active ? '激活' : '已禁用' }}
          </span>
        </div>
        <div v-if="authStore.user?.is_sso" class="flex justify-between">
          <span class="text-gray-600">登录方式:</span>
          <span class="text-gray-900">SSO ({{ authStore.user?.sso_provider }})</span>
        </div>
      </div>
    </div>

    <!-- API Token 管理 -->
    <div class="bg-white rounded-lg shadow-md p-6">
      <APIKeyManager />
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, watch } from 'vue'
import { useAuthStore } from '@/stores'
import { formatDate } from '@/utils/format'
import APIKeyManager from '@/components/APIKeyManager.vue'

const authStore = useAuthStore()

const form = reactive({
  email: authStore.user?.email || '',
  full_name: authStore.user?.full_name || '',
})

// 监听用户信息变化
watch(
  () => authStore.user,
  (user) => {
    if (user) {
      form.email = user.email
      form.full_name = user.full_name || ''
    }
  },
  { immediate: true }
)

function roleLabel(role?: string) {
  const labels = {
    admin: '管理员',
    manager: '管理者',
    user: '普通用户',
  }
  return labels[role as keyof typeof labels] || role
}

async function handleUpdate() {
  await authStore.updateProfile({
    email: form.email,
    full_name: form.full_name || undefined,
  })
}
</script>
