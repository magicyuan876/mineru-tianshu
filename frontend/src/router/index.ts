/**
 * Vue Router 配置
 */
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    // 登录页
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/Login.vue'),
      meta: { title: '登录', public: true }
    },
    // 注册页
    {
      path: '/register',
      name: 'register',
      component: () => import('@/views/Register.vue'),
      meta: { title: '注册', public: true }
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
          meta: { title: '仪表盘' }
        },
        {
          path: 'tasks',
          name: 'task-list',
          component: () => import('@/views/TaskList.vue'),
          meta: { title: '任务列表' }
        },
        {
          path: 'tasks/submit',
          name: 'task-submit',
          component: () => import('@/views/TaskSubmit.vue'),
          meta: { title: '提交任务' }
        },
        {
          path: 'tasks/:id',
          name: 'task-detail',
          component: () => import('@/views/TaskDetail.vue'),
          meta: { title: '任务详情' }
        },
        {
          path: 'queue',
          name: 'queue-management',
          component: () => import('@/views/QueueManagement.vue'),
          meta: { title: '队列管理' }
        },
        {
          path: 'profile',
          name: 'profile',
          component: () => import('@/views/Profile.vue'),
          meta: { title: '个人资料' }
        },
        {
          path: 'users',
          name: 'user-management',
          component: () => import('@/views/UserManagement.vue'),
          meta: { title: '用户管理', requiresAdmin: true }
        }
      ]
    },
  ]
})

// 全局导航守卫
router.beforeEach(async (to, from, next) => {
  // 设置页面标题
  if (to.meta.title) {
    document.title = `${to.meta.title} - MinerU Tianshu`
  } else {
    document.title = 'MinerU Tianshu - 文档解析服务'
  }

  const authStore = useAuthStore()

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
