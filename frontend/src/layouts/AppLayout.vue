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
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useQueueStore } from '@/stores'
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
} from 'lucide-vue-next'

const route = useRoute()
const queueStore = useQueueStore()
const mobileMenuOpen = ref(false)

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

function refreshStats() {
  queueStore.fetchStats()
}

onMounted(() => {
  // 启动自动刷新队列统计
  queueStore.startAutoRefresh(5000)
})

onUnmounted(() => {
  // 停止自动刷新
  queueStore.stopAutoRefresh()
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

