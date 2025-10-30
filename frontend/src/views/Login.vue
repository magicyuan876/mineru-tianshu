<template>
  <div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 px-4">
    <div class="max-w-md w-full">
      <!-- Logo 和标题 -->
      <div class="text-center mb-8">
        <h1 class="text-4xl font-bold text-gray-900 mb-2">MinerU Tianshu</h1>
        <p class="text-gray-600">天枢 - 企业级 AI 数据预处理平台</p>
      </div>

      <!-- 登录表单 -->
      <div class="bg-white rounded-2xl shadow-xl p-8">
        <h2 class="text-2xl font-semibold text-gray-900 mb-6">登录</h2>

        <form @submit.prevent="handleLogin" class="space-y-4">
          <!-- 用户名 -->
          <div>
            <label for="username" class="block text-sm font-medium text-gray-700 mb-1">
              用户名
            </label>
            <input
              id="username"
              v-model="form.username"
              type="text"
              required
              class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="请输入用户名"
            />
          </div>

          <!-- 密码 -->
          <div>
            <label for="password" class="block text-sm font-medium text-gray-700 mb-1">
              密码
            </label>
            <input
              id="password"
              v-model="form.password"
              type="password"
              required
              class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="请输入密码"
            />
          </div>

          <!-- 登录按钮 -->
          <button
            type="submit"
            :disabled="authStore.loading"
            class="w-full bg-blue-600 text-white py-2.5 rounded-lg font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <span v-if="!authStore.loading">登录</span>
            <span v-else class="flex items-center justify-center">
              <svg class="animate-spin h-5 w-5 mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              登录中...
            </span>
          </button>
        </form>

        <!-- 注册链接 -->
        <div class="mt-6 text-center">
          <p class="text-sm text-gray-600">
            还没有账号？
            <router-link to="/register" class="text-blue-600 hover:text-blue-700 font-medium">
              立即注册
            </router-link>
          </p>
        </div>

        <!-- 默认账号提示 -->
        <div class="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
          <p class="text-sm text-yellow-800">
            <strong>默认管理员账户：</strong><br>
            用户名: <code class="bg-yellow-100 px-1 rounded">admin</code><br>
            密码: <code class="bg-yellow-100 px-1 rounded">admin123</code><br>
            <span class="text-xs text-yellow-700">⚠️ 首次登录后请立即修改密码</span>
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
import { reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores'

const router = useRouter()
const authStore = useAuthStore()

const form = reactive({
  username: '',
  password: '',
})

async function handleLogin() {
  const success = await authStore.login(form)
  if (success) {
    // 登录成功，跳转到首页
    router.push('/')
  }
}
</script>
