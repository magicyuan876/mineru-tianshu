<template>
  <div class="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
    <!-- 顶部导航栏 -->
    <nav class="bg-white/80 backdrop-blur-md shadow-sm border-b border-gray-200/50 sticky top-0 z-40">
      <div class="w-full px-4 sm:px-6 lg:px-10 2xl:px-16">
        <div class="flex items-center justify-between gap-3 h-16 lg:h-20">
          <!-- 左 zone：Logo + 导航链接；min-w-0 + 内部横向滚动，任何视口下都不与右 zone 重叠 -->
          <div class="flex items-center min-w-0 flex-1 h-full">
            <!-- Logo -->
            <div class="flex-shrink-0 flex items-center">
              <router-link to="/" class="flex items-center gap-2 group">
                <img
                  v-if="systemStore.config.system_logo"
                  :src="systemStore.config.system_logo"
                  :alt="`${systemStore.config.system_name} Logo`"
                  class="h-8 lg:h-10 transition-transform group-hover:scale-105"
                  @error="handleLogoError"
                />
                <img
                  v-else
                  src="/logo.svg"
                  :alt="`${systemStore.config.system_name} Logo`"
                  class="h-8 lg:h-10 transition-transform group-hover:scale-105"
                />
              </router-link>
            </div>

            <!-- 导航链接：空间不足时横向滚动而非挤压右 zone -->
            <div class="hidden md:flex items-center gap-0.5 lg:gap-1 ml-4 lg:ml-6 min-w-0 overflow-x-auto scrollbar-hide">
              <router-link
                v-for="item in navItems"
                :key="item.path"
                :to="item.path"
                :class="isActive(item.path) ? activeClass : inactiveClass"
                class="inline-flex items-center h-9 px-2.5 lg:px-3 text-sm font-medium rounded-lg transition-colors duration-200 whitespace-nowrap flex-shrink-0"
              >
                <component :is="item.icon" class="w-4 h-4 lg:w-5 lg:h-5 lg:mr-2" />
                <span class="hidden lg:inline">{{ $t(item.i18nKey) }}</span>
              </router-link>
            </div>
          </div>

          <!-- 右 zone：flex-shrink-0 绝不收缩 -->
          <div class="flex items-center gap-2 flex-shrink-0">
            <!-- 队列统计摘要：≥2xl 才显示，主流宽度下优先保证导航空间（信息降级） -->
            <div v-if="queueStore.stats" class="hidden 2xl:flex items-center gap-3 h-9 px-3 bg-gray-50 rounded-lg border border-gray-200/50">
              <div class="flex items-center gap-1.5">
                <div class="w-2 h-2 rounded-full bg-yellow-400 animate-pulse"></div>
                <span class="text-xs font-medium text-gray-700">{{ $t('queue.processing') }}</span>
                <span class="text-xs font-bold text-yellow-600 tabular-nums">{{ queueStore.stats.processing }}</span>
              </div>
              <div class="w-px h-3 bg-gray-300"></div>
              <div class="flex items-center gap-1.5">
                <div class="w-2 h-2 rounded-full bg-gray-400"></div>
                <span class="text-xs font-medium text-gray-700">{{ $t('queue.pending') }}</span>
                <span class="text-xs font-bold text-gray-600 tabular-nums">{{ queueStore.stats.pending }}</span>
              </div>
            </div>

            <!-- GitHub Star 按钮：≥xl 显示 -->
            <a
              v-if="systemStore.config.show_github_star"
              href="https://github.com/magicyuan876/mineru-tianshu"
              target="_blank"
              rel="noopener noreferrer"
              class="hidden xl:flex items-center gap-1.5 h-9 px-3 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 hover:text-gray-900 hover:border-gray-400 transition-colors duration-200 shadow-sm"
              title="Star on GitHub"
            >
              <Github class="w-4 h-4" />
              <span class="hidden 2xl:inline">Star</span>
            </a>

            <!-- 刷新按钮 -->
            <button
              @click="refreshStats"
              :disabled="queueStore.loading"
              class="h-9 w-9 grid place-items-center text-gray-600 hover:text-primary-600 hover:bg-gray-100 rounded-lg transition-colors duration-200"
              :title="$t('queue.refresh')"
            >
              <RefreshCw :class="{ 'animate-spin': queueStore.loading }" class="w-4 h-4 lg:w-5 lg:h-5" />
            </button>

            <!-- 语言切换 -->
            <div class="relative hidden sm:block" ref="langMenuRef">
              <button
                @click="langMenuOpen = !langMenuOpen"
                class="flex items-center gap-1.5 h-9 px-2.5 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg transition-colors duration-200 border border-transparent hover:border-gray-300"
                :title="$t('common.language')"
              >
                <Languages class="w-4 h-4 lg:w-5 lg:h-5" />
                <span class="hidden 2xl:inline">{{ localeStore.currentLocaleName }}</span>
                <ChevronDown :class="{ 'rotate-180': langMenuOpen }" class="w-3.5 h-3.5 transition-transform duration-200" />
              </button>

              <!-- 语言下拉菜单 -->
              <div
                v-if="langMenuOpen"
                class="absolute right-0 mt-3 w-48 bg-white rounded-xl shadow-xl border border-gray-200/50 py-2 z-50 backdrop-blur-sm"
              >
                <button
                  v-for="locale in localeStore.availableLocales"
                  :key="locale.value"
                  @click="handleChangeLocale(locale.value)"
                  :class="{
                    'bg-primary-50 text-primary-600 font-semibold': localeStore.currentLocale === locale.value,
                    'text-gray-700 hover:bg-gray-50': localeStore.currentLocale !== locale.value,
                  }"
                  class="w-full flex items-center gap-3 px-4 py-2.5 text-sm transition-all duration-200"
                >
                  <Check
                    v-if="localeStore.currentLocale === locale.value"
                    class="w-4 h-4 flex-shrink-0"
                  />
                  <span :class="{ 'ml-7': localeStore.currentLocale !== locale.value }">
                    {{ locale.label }}
                  </span>
                </button>
              </div>
            </div>

            <!-- 用户菜单 -->
            <div class="relative hidden sm:block" ref="userMenuRef">
              <button
                @click="userMenuOpen = !userMenuOpen"
                class="flex items-center gap-2 h-10 px-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg transition-colors duration-200 border border-transparent hover:border-gray-300"
              >
                <div class="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center text-white font-semibold shadow-sm">
                  {{ authStore.user?.username?.charAt(0).toUpperCase() }}
                </div>
                <span class="hidden 2xl:inline">{{ authStore.user?.username }}</span>
                <ChevronDown :class="{ 'rotate-180': userMenuOpen }" class="w-3.5 h-3.5 transition-transform duration-200" />
              </button>

              <!-- 下拉菜单 -->
              <div
                v-if="userMenuOpen"
                class="absolute right-0 mt-3 w-64 bg-white rounded-xl shadow-xl border border-gray-200/50 py-2 z-50 backdrop-blur-sm"
              >
                <div class="px-4 py-3 border-b border-gray-100">
                  <p class="text-sm font-semibold text-gray-900">{{ authStore.user?.username }}</p>
                  <p class="text-xs text-gray-500 mt-0.5">{{ authStore.user?.email }}</p>
                  <span
                    :class="{
                      'bg-gradient-to-r from-red-500 to-red-600 text-white': authStore.user?.role === 'admin',
                      'bg-gradient-to-r from-yellow-500 to-yellow-600 text-white': authStore.user?.role === 'manager',
                      'bg-gradient-to-r from-blue-500 to-blue-600 text-white': authStore.user?.role === 'user',
                    }"
                    class="inline-block mt-2 px-2.5 py-1 text-xs font-semibold rounded-md shadow-sm"
                  >
                    {{ roleLabel(authStore.user?.role) }}
                  </span>
                </div>

                <router-link
                  to="/profile"
                  @click="userMenuOpen = false"
                  class="flex items-center gap-3 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors duration-200"
                >
                  <UserIcon class="w-4 h-4" />
                  <span>{{ $t('common.profile') }}</span>
                </router-link>

                <router-link
                  v-if="authStore.isAdmin"
                  to="/users"
                  @click="userMenuOpen = false"
                  class="flex items-center gap-3 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors duration-200"
                >
                  <Users class="w-4 h-4" />
                  <span>{{ $t('nav.userManagement') }}</span>
                </router-link>

                <router-link
                  v-if="authStore.isAdmin"
                  to="/system-config"
                  @click="userMenuOpen = false"
                  class="flex items-center gap-3 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors duration-200"
                >
                  <Settings class="w-4 h-4" />
                  <span>{{ $t('nav.systemConfig') }}</span>
                </router-link>

                <div class="border-t border-gray-200 my-2"></div>

                <button
                  @click="handleLogout"
                  class="w-full flex items-center gap-2 px-4 py-2 text-sm text-red-600 hover:bg-red-50"
                >
                  <LogOut class="w-4 h-4" />
                  <span>{{ $t('common.logout') }}</span>
                </button>
              </div>
            </div>

            <!-- 移动端菜单按钮 -->
            <button
              @click="mobileMenuOpen = !mobileMenuOpen"
              class="md:hidden h-10 w-10 grid place-items-center text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors duration-200"
            >
              <Menu v-if="!mobileMenuOpen" class="w-6 h-6" />
              <X v-else class="w-6 h-6" />
            </button>
          </div>
        </div>
      </div>

      <!-- 移动端菜单 -->
      <div v-if="mobileMenuOpen" class="md:hidden border-t border-gray-200 bg-white">
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
            {{ $t(item.i18nKey) }}
          </router-link>

          <!-- 移动端队列统计 -->
          <div v-if="queueStore.stats" class="px-3 py-3 bg-gray-50 rounded-md mx-2 mt-2">
            <div class="flex items-center justify-around text-sm">
              <div class="flex items-center gap-2">
                <div class="w-2 h-2 rounded-full bg-yellow-400 animate-pulse"></div>
                <span class="text-gray-700">{{ $t('queue.processing') }}</span>
                <span class="font-bold text-yellow-600">{{ queueStore.stats.processing }}</span>
              </div>
              <div class="w-px h-4 bg-gray-300"></div>
              <div class="flex items-center gap-2">
                <div class="w-2 h-2 rounded-full bg-gray-400"></div>
                <span class="text-gray-700">{{ $t('queue.pending') }}</span>
                <span class="font-bold text-gray-600">{{ queueStore.stats.pending }}</span>
              </div>
            </div>
          </div>

          <!-- 移动端语言切换 -->
          <div class="sm:hidden px-3 py-2">
            <div class="text-xs font-medium text-gray-500 mb-2">{{ $t('common.language') }}</div>
            <div class="flex gap-2">
              <button
                v-for="locale in localeStore.availableLocales"
                :key="locale.value"
                @click="handleChangeLocale(locale.value)"
                :class="{
                  'bg-primary-600 text-white': localeStore.currentLocale === locale.value,
                  'bg-gray-100 text-gray-700': localeStore.currentLocale !== locale.value,
                }"
                class="flex-1 px-3 py-2 text-sm font-medium rounded-lg transition-all duration-200"
              >
                {{ locale.label }}
              </button>
            </div>
          </div>

          <!-- 移动端用户信息 -->
          <div class="sm:hidden px-3 py-3 border-t border-gray-200 mt-2">
            <div class="flex items-center gap-3 mb-3">
              <div class="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center text-white font-semibold shadow-sm">
                {{ authStore.user?.username?.charAt(0).toUpperCase() }}
              </div>
              <div>
                <p class="text-sm font-semibold text-gray-900">{{ authStore.user?.username }}</p>
                <p class="text-xs text-gray-500">{{ authStore.user?.email }}</p>
              </div>
            </div>
            <router-link
              to="/profile"
              @click="mobileMenuOpen = false"
              class="flex items-center gap-2 px-3 py-2 text-sm text-gray-700 bg-gray-50 rounded-lg mb-2"
            >
              <UserIcon class="w-4 h-4" />
              <span>{{ $t('common.profile') }}</span>
            </router-link>
            <router-link
              v-if="authStore.isAdmin"
              to="/users"
              @click="mobileMenuOpen = false"
              class="flex items-center gap-2 px-3 py-2 text-sm text-gray-700 bg-gray-50 rounded-lg mb-2"
            >
              <Users class="w-4 h-4" />
              <span>{{ $t('nav.userManagement') }}</span>
            </router-link>
            <router-link
              v-if="authStore.isAdmin"
              to="/system-config"
              @click="mobileMenuOpen = false"
              class="flex items-center gap-2 px-3 py-2 text-sm text-gray-700 bg-gray-50 rounded-lg mb-2"
            >
              <Settings class="w-4 h-4" />
              <span>{{ $t('nav.systemConfig') }}</span>
            </router-link>
            <button
              @click="handleLogout"
              class="w-full flex items-center gap-2 px-3 py-2 text-sm text-red-600 bg-red-50 rounded-lg"
            >
              <LogOut class="w-4 h-4" />
              <span>{{ $t('common.logout') }}</span>
            </button>
          </div>
        </div>
      </div>
    </nav>

    <!-- 主内容区域：流式 gutter，max-w-[2200px] 仅为 4K 以上超宽屏保护，不是内容宽度限制 -->
    <main class="w-full px-4 sm:px-6 lg:px-10 2xl:px-16 py-6 lg:py-10 max-w-[2200px] mx-auto">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>

    <!-- 页脚 -->
    <footer class="bg-white border-t border-gray-200 mt-auto">
      <div class="w-full max-w-[2200px] mx-auto px-4 sm:px-6 lg:px-10 2xl:px-16 py-6">
        <div class="flex flex-col items-center gap-3">
          <!-- GitHub Star 提示 -->
          <div v-if="systemStore.config.show_github_star" class="flex items-center gap-2 text-sm">
            <span class="text-gray-600">{{ $t('footer.likeProject') }}</span>
            <a
              href="https://github.com/magicyuan876/mineru-tianshu"
              target="_blank"
              rel="noopener noreferrer"
              class="inline-flex items-center gap-1.5 px-3 py-1 text-sm font-medium text-white bg-gray-800 rounded-md hover:bg-gray-700 transition-colors"
            >
              <Github class="w-4 h-4" />
              <span>{{ $t('footer.starOnGitHub') }}</span>
              <Star class="w-3.5 h-3.5 fill-yellow-400 text-yellow-400" />
            </a>
          </div>

          <!-- 版权信息 -->
          <p class="text-center text-sm text-gray-500">
            © 2024 {{ systemStore.config.system_name }} - {{ $t('footer.copyright').split(' - ')[1] }}
          </p>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useQueueStore, useAuthStore, useLocaleStore, useSystemStore } from '@/stores'
import type { SupportLocale } from '@/locales'
import {
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
  BookOpen,
  Languages,
  Check,
} from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const { locale, t } = useI18n()
const queueStore = useQueueStore()
const authStore = useAuthStore()
const localeStore = useLocaleStore()
const systemStore = useSystemStore()
const mobileMenuOpen = ref(false)
const userMenuOpen = ref(false)
const langMenuOpen = ref(false)
const userMenuRef = ref<HTMLElement | null>(null)
const langMenuRef = ref<HTMLElement | null>(null)

const navItems = [
  { i18nKey: 'nav.dashboard', path: '/', icon: LayoutDashboard },
  { i18nKey: 'nav.taskList', path: '/tasks', icon: ListTodo },
  { i18nKey: 'nav.submitTask', path: '/tasks/submit', icon: Upload },
  { i18nKey: 'nav.queueManagement', path: '/queue', icon: Settings },
  { i18nKey: 'nav.apiDocs', path: '/api-docs', icon: BookOpen },
]

const activeClass = 'text-primary-600 border-b-2 border-primary-600'
const inactiveClass = 'text-gray-600 hover:text-gray-900 border-b-2 border-transparent'
const activeMobileClass = 'bg-primary-50 text-primary-600'
const inactiveMobileClass = 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'

function isActive(path: string): boolean {
  // 首页特殊处理：只有完全匹配才激活
  if (path === '/') {
    return route.path === '/'
  }

  // 其他路径：精确匹配才激活
  // 这样 /tasks 只匹配 /tasks，不会匹配 /tasks/submit
  // 而 /tasks/submit 会精确匹配 /tasks/submit
  return route.path === path
}

function roleLabel(role?: string) {
  const labels = {
    admin: t('profile.roleAdmin'),
    manager: t('profile.roleManager'),
    user: t('profile.roleUser'),
  }
  return labels[role as keyof typeof labels] || role
}

function refreshStats() {
  queueStore.fetchStats()
}

// 切换语言
function handleChangeLocale(newLocale: SupportLocale) {
  localeStore.setLocale(newLocale)
  locale.value = newLocale
  langMenuOpen.value = false
}

// 退出登录
function handleLogout() {
  userMenuOpen.value = false
  authStore.logout()
  router.push('/login')
}

// 处理 Logo 加载错误
function handleLogoError(event: Event) {
  const img = event.target as HTMLImageElement
  // 加载失败时使用默认 logo
  img.src = '/logo.svg'
  console.warn('Failed to load custom logo, using default logo')
}

// 点击外部关闭菜单
function handleClickOutside(event: MouseEvent) {
  if (userMenuRef.value && !userMenuRef.value.contains(event.target as Node)) {
    userMenuOpen.value = false
  }
  if (langMenuRef.value && !langMenuRef.value.contains(event.target as Node)) {
    langMenuOpen.value = false
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
  // 加载系统配置
  systemStore.loadConfig()

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
