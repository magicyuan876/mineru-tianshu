<template>
  <div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 px-4">
    <div class="max-w-md w-full">
      <!-- Logo 和标题 -->
      <div class="text-center mb-8">
        <h1 class="text-4xl font-bold text-gray-900 mb-2">MinerU Tianshu</h1>
        <p class="text-gray-600">天枢 - 企业级 AI 数据预处理平台</p>
      </div>

      <!-- 注册表单 -->
      <div class="bg-white rounded-2xl shadow-xl p-8">
        <h2 class="text-2xl font-semibold text-gray-900 mb-6">注册新账号</h2>

        <form @submit.prevent="handleRegister" class="space-y-4">
          <!-- 用户名 -->
          <div>
            <label for="username" class="block text-sm font-medium text-gray-700 mb-1">
              用户名 *
            </label>
            <input
              id="username"
              v-model="form.username"
              type="text"
              required
              pattern="[a-zA-Z0-9_-]{3,50}"
              class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="3-50个字符，支持字母、数字、下划线"
            />
            <p class="mt-1 text-xs text-gray-500">只能包含字母、数字、下划线和连字符</p>
          </div>

          <!-- 邮箱 -->
          <div>
            <label for="email" class="block text-sm font-medium text-gray-700 mb-1">
              邮箱 *
            </label>
            <input
              id="email"
              v-model="form.email"
              type="email"
              required
              class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="your@email.com"
            />
          </div>

          <!-- 全名 -->
          <div>
            <label for="full_name" class="block text-sm font-medium text-gray-700 mb-1">
              全名 (可选)
            </label>
            <input
              id="full_name"
              v-model="form.full_name"
              type="text"
              maxlength="100"
              class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="张三"
            />
          </div>

          <!-- 密码 -->
          <div>
            <label for="password" class="block text-sm font-medium text-gray-700 mb-1">
              密码 *
            </label>
            <input
              id="password"
              v-model="form.password"
              type="password"
              required
              minlength="8"
              maxlength="100"
              class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="至少8个字符"
            />
            <p class="mt-1 text-xs text-gray-500">建议使用大小写字母、数字和特殊字符的组合</p>
          </div>

          <!-- 确认密码 -->
          <div>
            <label for="confirm_password" class="block text-sm font-medium text-gray-700 mb-1">
              确认密码 *
            </label>
            <input
              id="confirm_password"
              v-model="confirmPassword"
              type="password"
              required
              class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="再次输入密码"
            />
            <p v-if="confirmPassword && confirmPassword !== form.password" class="mt-1 text-xs text-red-600">
              两次密码输入不一致
            </p>
          </div>

          <!-- 注册按钮 -->
          <button
            type="submit"
            :disabled="authStore.loading || (confirmPassword && confirmPassword !== form.password)"
            class="w-full bg-blue-600 text-white py-2.5 rounded-lg font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors mt-6"
          >
            <span v-if="!authStore.loading">注册</span>
            <span v-else class="flex items-center justify-center">
              <svg class="animate-spin h-5 w-5 mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              注册中...
            </span>
          </button>
        </form>

        <!-- 登录链接 -->
        <div class="mt-6 text-center">
          <p class="text-sm text-gray-600">
            已有账号？
            <router-link to="/login" class="text-blue-600 hover:text-blue-700 font-medium">
              立即登录
            </router-link>
          </p>
        </div>
      </div>

      <!-- 版权信息 -->
      <div class="mt-8 text-center text-sm text-gray-600">
        <p>MinerU Tianshu v2.0 - 支持企业级认证授权</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores'

const router = useRouter()
const authStore = useAuthStore()

const form = reactive({
  username: '',
  email: '',
  password: '',
  full_name: '',
})

const confirmPassword = ref('')

async function handleRegister() {
  if (confirmPassword.value !== form.password) {
    return
  }

  const success = await authStore.register(form)
  if (success) {
    // 注册成功，跳转到登录页
    router.push('/login')
  }
}
</script>
