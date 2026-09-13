<template>
  <div class="w-full">
    <PageHeader :title="$t('profile.title')" />

    <!-- 用户信息卡片 -->
    <div class="bg-white rounded-lg shadow-md p-6 mb-6">
      <h2 class="text-xl font-semibold text-gray-900 mb-4">{{ $t('profile.title') }}</h2>

      <div class="space-y-4">
        <!-- 用户名 -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('profile.username') }}</label>
          <input
            type="text"
            :value="authStore.user?.username"
            disabled
            class="w-full px-4 py-2 bg-gray-50 border border-gray-300 rounded-lg text-gray-500 cursor-not-allowed"
          />
          <p class="mt-1 text-xs text-gray-500">{{ $t('profile.usernameCannotChange') }}</p>
        </div>

        <!-- 邮箱 -->
        <div>
          <label for="email" class="block text-sm font-medium text-gray-700 mb-1">{{ $t('profile.email') }}</label>
          <input
            id="email"
            v-model="form.email"
            type="email"
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        <!-- 全名 -->
        <div>
          <label for="full_name" class="block text-sm font-medium text-gray-700 mb-1">{{ $t('profile.fullName') }}</label>
          <input
            id="full_name"
            v-model="form.full_name"
            type="text"
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        <!-- 角色 -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('profile.role') }}</label>
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
            {{ $t('profile.saveChanges') }}
          </button>
        </div>
      </div>
    </div>

    <!-- 修改密码 -->
    <div v-if="!authStore.user?.is_sso" class="bg-white rounded-lg shadow-md p-6 mb-6">
      <h2 class="text-xl font-semibold text-gray-900 mb-4">{{ $t('profile.changePassword') }}</h2>

      <div class="space-y-4">
        <!-- 旧密码 -->
        <div>
          <label for="old_password" class="block text-sm font-medium text-gray-700 mb-1">
            {{ $t('profile.oldPassword') }} *
          </label>
          <input
            id="old_password"
            v-model="passwordForm.oldPassword"
            type="password"
            required
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            :placeholder="$t('profile.oldPasswordPlaceholder')"
          />
        </div>

        <!-- 新密码 -->
        <div>
          <label for="new_password" class="block text-sm font-medium text-gray-700 mb-1">
            {{ $t('profile.newPassword') }} *
          </label>
          <input
            id="new_password"
            v-model="passwordForm.newPassword"
            type="password"
            required
            minlength="8"
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            :placeholder="$t('profile.newPasswordPlaceholder')"
          />
          <p class="mt-1 text-xs text-gray-500">{{ $t('profile.passwordRequirement') }}</p>
        </div>

        <!-- 确认新密码 -->
        <div>
          <label for="confirm_password" class="block text-sm font-medium text-gray-700 mb-1">
            {{ $t('profile.confirmNewPassword') }} *
          </label>
          <input
            id="confirm_password"
            v-model="passwordForm.confirmPassword"
            type="password"
            required
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            :placeholder="$t('profile.confirmPasswordPlaceholder')"
          />
          <p v-if="passwordForm.confirmPassword && passwordForm.newPassword !== passwordForm.confirmPassword" class="mt-1 text-xs text-red-600">
            {{ $t('profile.passwordMismatch') }}
          </p>
        </div>

        <!-- 修改密码按钮 -->
        <div class="flex justify-end">
          <button
            @click="handleChangePassword"
            :disabled="authStore.loading || !isPasswordFormValid"
            class="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ $t('profile.changePasswordButton') }}
          </button>
        </div>
      </div>
    </div>

    <!-- 账户信息 -->
    <div class="bg-white rounded-lg shadow-md p-6 mb-6">
      <h2 class="text-xl font-semibold text-gray-900 mb-4">{{ $t('profile.accountInfo') }}</h2>

      <div class="space-y-3 text-sm">
        <div class="flex justify-between">
          <span class="text-gray-600">{{ $t('profile.userId') }}:</span>
          <span class="font-mono text-gray-900">{{ authStore.user?.user_id }}</span>
        </div>
        <div class="flex justify-between">
          <span class="text-gray-600">{{ $t('profile.createdAt') }}:</span>
          <span class="text-gray-900">{{ formatDate(authStore.user?.created_at) }}</span>
        </div>
        <div class="flex justify-between">
          <span class="text-gray-600">{{ $t('profile.lastLogin') }}:</span>
          <span class="text-gray-900">{{ formatDate(authStore.user?.last_login) || $t('profile.neverLoggedIn') }}</span>
        </div>
        <div class="flex justify-between">
          <span class="text-gray-600">{{ $t('profile.accountStatus') }}:</span>
          <span
            :class="authStore.user?.is_active ? 'text-green-600' : 'text-red-600'"
            class="font-medium"
          >
            {{ authStore.user?.is_active ? $t('profile.active') : $t('profile.disabled') }}
          </span>
        </div>
        <div v-if="authStore.user?.is_sso" class="flex justify-between">
          <span class="text-gray-600">{{ $t('profile.loginMethod') }}:</span>
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
import { reactive, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores'
import { formatDate } from '@/utils/format'
import APIKeyManager from '@/components/APIKeyManager.vue'
import PageHeader from '@/components/PageHeader.vue'

const { t } = useI18n()
const authStore = useAuthStore()

const form = reactive({
  email: authStore.user?.email || '',
  full_name: authStore.user?.full_name || '',
})

const passwordForm = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: '',
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

// 密码表单验证
const isPasswordFormValid = computed(() => {
  return (
    passwordForm.oldPassword.length > 0 &&
    passwordForm.newPassword.length >= 8 &&
    passwordForm.confirmPassword.length > 0 &&
    passwordForm.newPassword === passwordForm.confirmPassword
  )
})

function roleLabel(role?: string) {
  const roleMap: Record<string, string> = {
    admin: t('profile.roleAdmin'),
    manager: t('profile.roleManager'),
    user: t('profile.roleUser'),
  }
  return roleMap[role || ''] || role
}

async function handleUpdate() {
  await authStore.updateProfile({
    email: form.email,
    full_name: form.full_name || undefined,
  })
}

async function handleChangePassword() {
  const success = await authStore.changePassword(passwordForm.oldPassword, passwordForm.newPassword)

  if (success) {
    // 清空表单
    passwordForm.oldPassword = ''
    passwordForm.newPassword = ''
    passwordForm.confirmPassword = ''
  }
}
</script>
