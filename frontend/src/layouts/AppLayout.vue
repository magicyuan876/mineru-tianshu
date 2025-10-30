<template>
  <div class="min-h-screen bg-gray-50">
    <!-- 顶部导航栏 -->
    <nav class="bg-white shadow-sm border-b border-gray-200">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between h-16">
          <!-- 左侧：Logo 和导航链接 -->
          <div class="flex">
            <!-- Logo -->
            <div class="flex-shrink-0 flex items-center">
              <router-link to="/" class="flex items-center gap-2">
                <Sparkles class="h-8 w-8 text-primary-600" />
                <span class="text-xl font-bold text-gray-900">MinerU Tianshu</span>
              </router-link>
            </div>

            <!-- 导航链接 -->
            <div class="hidden sm:ml-8 sm:flex sm:space-x-4">
              <router-link
                v-for="item in navItems"
                :key="item.path"
                :to="item.path"
                :class="isActive(item.path) ? activeClass : inactiveClass"
                class="inline-flex items-center px-3 py-2 text-sm font-medium transition-colors"
              >
                <component :is="item.icon" class="w-4 h-4 mr-2" />
                {{ item.name }}
              </router-link>
            </div>
          </div>

          <!-- 右侧：系统状态和操作 -->
          <div class="flex items-center gap-4">
            <!-- 队列统计摘要 -->
            <div v-if="queueStore.stats" class="hidden md:flex items-center gap-3 text-sm">
              <div class="flex items-center gap-1">
                <div class="w-2 h-2 rounded-full bg-yellow-400"></div>
                <span class="text-gray-600">处理中: {{ queueStore.stats.processing }}</span>
              </div>
              <div class="flex items-center gap-1">
                <div class="w-2 h-2 rounded-full bg-gray-400"></div>
                <span class="text-gray-600">等待: {{ queueStore.stats.pending }}</span>
              </div>
            </div>

            <!-- GitHub Star 按钮 -->
            <a
              href="https://github.com/magicyuan876/mineru-tianshu"
              target="_blank"
              rel="noopener noreferrer"
              class="hidden sm:flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 hover:text-gray-900 transition-colors"
              title="Star on GitHub"
            >
              <Github class="w-4 h-4" />
              <span>Star</span>
            </a>

            <!-- 刷新按钮 -->
            <button
              @click="refreshStats"
              :disabled="queueStore.loading"
              class="p-2 text-gray-600 hover:text-primary-600 transition-colors"
              title="刷新统计"
            >
              <RefreshCw :class="{ 'animate-spin': queueStore.loading }" class="w-5 h-5" />
            </button>

            <!-- 用户菜单 -->
            <div class="relative hidden sm:block" ref="userMenuRef">
              <button
                @click="userMenuOpen = !userMenuOpen"
                class="flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 rounded-lg transition-colors"
              >
                <div class="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center">
                  <UserIcon class="w-4 h-4 text-blue-600" />
                </div>
                <span class="hidden lg:block">{{ authStore.user?.username }}</span>
                <ChevronDown :class="{ 'rotate-180': userMenuOpen }" class="w-4 h-4 transition-transform" />
              </button>

              <!-- 下拉菜单 -->
              <div
                v-if="userMenuOpen"
                class="absolute right-0 mt-2 w-56 bg-white rounded-lg shadow-lg border border-gray-200 py-2 z-50"
              >
                <div class="px-4 py-2 border-b border-gray-200">
                  <p class="text-sm font-medium text-gray-900">{{ authStore.user?.username }}</p>
                  <p class="text-xs text-gray-500">{{ authStore.user?.email }}</p>
                  <span
                    :class="{
                      'bg-red-100 text-red-800': authStore.user?.role === 'admin',
                      'bg-yellow-100 text-yellow-800': authStore.user?.role === 'manager',
                      'bg-blue-100 text-blue-800': authStore.user?.role === 'user',
                    }"
                    class="inline-block mt-1 px-2 py-0.5 text-xs font-medium rounded"
                  >
                    {{ roleLabel(authStore.user?.role) }}
                  </span>
                </div>

                <router-link
                  to="/profile"
                  @click="userMenuOpen = false"
                  class="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                >
                  <UserIcon class="w-4 h-4" />
                  <span>个人资料</span>
                </router-link>

                <router-link
                  v-if="authStore.isAdmin"
                  to="/users"
                  @click="userMenuOpen = false"
                  class="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                >
                  <Users class="w-4 h-4" />
                  <span>用户管理</span>
                </router-link>

                <div class="border-t border-gray-200 my-2"></div>

                <button
                  @click="handleLogout"
                  class="w-full flex items-center gap-2 px-4 py-2 text-sm text-red-600 hover:bg-red-50"
                >
                  <LogOut class="w-4 h-4" />
                  <span>退出登录</span>
                </button>
              </div>
            </div>

            <!-- 移动端菜单按钮 -->
            <button
              @click="mobileMenuOpen = !mobileMenuOpen"
              class="sm:hidden p-2 text-gray-600 hover:text-gray-900"
            >
              <Menu v-if="!mobileMenuOpen" class="w-6 h-6" />
              <X v-else class="w-6 h-6" />
            </button>
          </div>
        </div>
      </div>

      <!-- 移动端菜单 -->
      <div v-if="mobileMenuOpen" class="sm:hidden border-t border-gray-200">
        <div class="px-2 pt-2 pb-3 space-y-1">
          <router-link
            v-for="item in navItems"
            :key="item.path"
            :to="item.path"
            @click="mobileMenuOpen = false"
            :class="isActive(item.path) ? activeMobileClass : inactiveMobileClass"
            class="flex items-center px-3 py-2 text-base font-medium rounded-md"
          >
            <component :is="item.icon" class="w-5 h-5 mr-3" />
            {{ item.name }}
          </router-link>
        </div>
      </div>
    </nav>

    <!-- 主内容区域 -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>

    <!-- 页脚 -->
    <footer class="bg-white border-t border-gray-200 mt-auto">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div class="flex flex-col items-center gap-3">
          <!-- GitHub Star 提示 -->
          <div class="flex items-center gap-2 text-sm">
            <span class="text-gray-600">喜欢这个项目？</span>
            <a
              href="https://github.com/magicyuan876/mineru-tianshu"
              target="_blank"
              rel="noopener noreferrer"
              class="inline-flex items-center gap-1.5 px-3 py-1 text-sm font-medium text-white bg-gray-800 rounded-md hover:bg-gray-700 transition-colors"
            >
              <Github class="w-4 h-4" />
              <span>Star on GitHub</span>
              <Star class="w-3.5 h-3.5 fill-yellow-400 text-yellow-400" />
            </a>
          </div>

          <!-- 版权信息 -->
          <p class="text-center text-sm text-gray-500">
            © 2024 MinerU Tianshu - 天枢文档解析服务
          </p>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQueueStore, useAuthStore } from '@/stores'
import {
  Sparkles,
  LayoutDashboard,
  ListTodo,
  Upload,
  Settings,
  Menu,
  X,
  RefreshCw,
  Github,
  Star,
  User as UserIcon,
  Users,
  ChevronDown,
  LogOut,
} from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const queueStore = useQueueStore()
const authStore = useAuthStore()
const mobileMenuOpen = ref(false)
const userMenuOpen = ref(false)
const userMenuRef = ref<HTMLElement | null>(null)

const navItems = [
  { name: '仪表盘', path: '/', icon: LayoutDashboard },
  { name: '任务列表', path: '/tasks', icon: ListTodo },
  { name: '提交任务', path: '/tasks/submit', icon: Upload },
  { name: '队列管理', path: '/queue', icon: Settings },
]

const activeClass = 'text-primary-600 border-b-2 border-primary-600'
const inactiveClass = 'text-gray-600 hover:text-gray-900 border-b-2 border-transparent'
const activeMobileClass = 'bg-primary-50 text-primary-600'
const inactiveMobileClass = 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'

function isActive(path: string): boolean {
  if (path === '/') {
    return route.path === '/'
  }
  return route.path.startsWith(path)
}

function roleLabel(role?: string) {
  const labels = {
    admin: '管理员',
    manager: '管理者',
    user: '普通用户',
  }
  return labels[role as keyof typeof labels] || role
}

function refreshStats() {
  queueStore.fetchStats()
}

// 退出登录
function handleLogout() {
  userMenuOpen.value = false
  authStore.logout()
  router.push('/login')
}

// 点击外部关闭用户菜单
function handleClickOutside(event: MouseEvent) {
  if (userMenuRef.value && !userMenuRef.value.contains(event.target as Node)) {
    userMenuOpen.value = false
  }
}

// 页面可见性检测
function handleVisibilityChange() {
  if (document.hidden) {
    // 页面不可见，停止轮询
    console.log('页面不可见，暂停轮询')
    queueStore.stopAutoRefresh()
  } else {
    // 页面可见，恢复轮询
    console.log('页面可见，恢复轮询')
    queueStore.startAutoRefresh(5000)
  }
}

onMounted(() => {
  // 启动自动刷新队列统计（智能轮询）
  queueStore.startAutoRefresh(5000)

  // 监听页面可见性变化
  document.addEventListener('visibilitychange', handleVisibilityChange)

  // 监听点击外部关闭菜单
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  // 停止自动刷新
  queueStore.stopAutoRefresh()

  // 移除监听器
  document.removeEventListener('visibilitychange', handleVisibilityChange)
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
