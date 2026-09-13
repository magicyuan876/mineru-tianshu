/**
 * Vue Router 配置
 */
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore, useSystemStore } from '@/stores'
import i18n from '@/locales'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    // 登录页
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/Login.vue'),
      meta: { titleKey: 'common.login', public: true }
    },
    // 注册页
    {
      path: '/register',
      name: 'register',
      component: () => import('@/views/Register.vue'),
      meta: { titleKey: 'common.register', public: true }
    },
    // 主应用
    {
      path: '/',
      component: () => import('@/layouts/AppLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          name: 'dashboard',
          component: () => import('@/views/Dashboard.vue'),
          meta: { titleKey: 'nav.dashboard' }
        },
        {
          path: 'tasks',
          name: 'task-list',
          component: () => import('@/views/TaskList.vue'),
          meta: { titleKey: 'nav.taskList' }
        },
        {
          path: 'tasks/submit',
          name: 'task-submit',
          component: () => import('@/views/TaskSubmit.vue'),
          meta: { titleKey: 'nav.submitTask' }
        },
        {
          path: 'tasks/:id',
          name: 'task-detail',
          component: () => import('@/views/TaskDetail.vue'),
          meta: { titleKey: 'task.taskDetail' }
        },
        {
          path: 'queue',
          name: 'queue-management',
          component: () => import('@/views/QueueManagement.vue'),
          meta: { titleKey: 'nav.queueManagement' }
        },
        {
          path: 'profile',
          name: 'profile',
          component: () => import('@/views/Profile.vue'),
          meta: { titleKey: 'common.profile' }
        },
        {
          path: 'users',
          name: 'user-management',
          component: () => import('@/views/UserManagement.vue'),
          meta: { titleKey: 'nav.userManagement', requiresAdmin: true }
        },
        {
          path: 'system-config',
          name: 'system-config',
          component: () => import('@/views/SystemConfig.vue'),
          meta: { titleKey: 'nav.systemConfig', requiresAdmin: true }
        },
        {
          path: 'api-docs',
          name: 'api-docs',
          component: () => import('@/views/ApiDocsScalar.vue'),
          meta: { titleKey: 'nav.apiDocs' }
        }
      ]
    },
  ]
})

// 全局导航守卫
router.beforeEach(async (to, _from, next) => {
  const authStore = useAuthStore()
  const systemStore = useSystemStore()

  // 确保系统配置已加载（用于页面标题）
  if (!systemStore.config.system_name || systemStore.config.system_name === 'MinerU Tianshu') {
    await systemStore.loadConfig()
  }

  // 设置页面标题
  if (to.meta.titleKey) {
    systemStore.updatePageTitle(i18n.global.t(to.meta.titleKey as string))
  } else {
    document.title = systemStore.config.system_name
  }

  // 🔥 关键修复：如果有 token 但没有用户信息，先初始化
  // 这解决了刷新页面时的竞态条件问题
  if (authStore.token && !authStore.user) {
    await authStore.initialize()
  }

  // 公开页面（登录、注册）
  if (to.meta.public) {
    // 如果已登录，重定向到首页
    if (authStore.isAuthenticated) {
      next('/')
    } else {
      next()
    }
    return
  }

  // 需要认证的页面
  if (to.meta.requiresAuth || to.matched.some(record => record.meta.requiresAuth)) {
    if (!authStore.isAuthenticated) {
      // 未登录，重定向到登录页
      next({
        path: '/login',
        query: { redirect: to.fullPath }
      })
      return
    }

    // 检查是否需要管理员权限
    if (to.meta.requiresAdmin && !authStore.isAdmin) {
      // 非管理员无权访问
      next('/')
      return
    }

    next()
  } else {
    next()
  }
})

export default router
