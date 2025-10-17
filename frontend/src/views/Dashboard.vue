<template>
  <div>
    <!-- 页面标题 -->
    <div class="mb-6">
      <h1 class="text-2xl font-bold text-gray-900">仪表盘</h1>
      <p class="mt-1 text-sm text-gray-600">实时监控文档解析任务状态</p>
    </div>

    <!-- 队列统计卡片 -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
      <StatCard
        title="等待中"
        :value="queueStore.stats.pending"
        subtitle="待处理任务"
        :icon="Clock"
        color="gray"
      />
      <StatCard
        title="处理中"
        :value="queueStore.stats.processing"
        subtitle="正在解析"
        :icon="Loader"
        color="yellow"
      />
      <StatCard
        title="已完成"
        :value="queueStore.stats.completed"
        subtitle="解析成功"
        :icon="CheckCircle"
        color="green"
      />
      <StatCard
        title="失败"
        :value="queueStore.stats.failed"
        subtitle="解析失败"
        :icon="XCircle"
        color="red"
      />
    </div>

    <!-- 快捷操作 -->
    <div class="mb-8">
      <div class="card">
        <h2 class="text-lg font-semibold text-gray-900 mb-4">快捷操作</h2>
        <div class="flex flex-wrap gap-3">
          <router-link to="/tasks/submit" class="btn btn-primary">
            <Upload class="w-4 h-4 mr-2" />
            提交新任务
          </router-link>
          <router-link to="/tasks" class="btn btn-secondary">
            <ListTodo class="w-4 h-4 mr-2" />
            查看任务列表
          </router-link>
          <router-link to="/queue" class="btn btn-secondary">
            <Settings class="w-4 h-4 mr-2" />
            队列管理
          </router-link>
        </div>
      </div>
    </div>

    <!-- 最近任务 -->
    <div class="card">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg font-semibold text-gray-900">最近任务</h2>
        <button
          @click="refreshTasks"
          :disabled="taskStore.loading"
          class="text-sm text-primary-600 hover:text-primary-700 flex items-center"
        >
          <RefreshCw :class="{ 'animate-spin': taskStore.loading }" class="w-4 h-4 mr-1" />
          刷新
        </button>
      </div>

      <div v-if="taskStore.loading && recentTasks.length === 0" class="text-center py-8">
        <LoadingSpinner text="加载中..." />
      </div>

      <div v-else-if="recentTasks.length === 0" class="text-center py-8 text-gray-500">
        <FileQuestion class="w-12 h-12 mx-auto mb-2 text-gray-400" />
        <p>暂无任务</p>
      </div>

      <div v-else class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200">
          <thead>
            <tr class="bg-gray-50">
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                文件名
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                状态
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                创建时间
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                操作
              </th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            <tr v-for="task in recentTasks" :key="task.task_id" class="hover:bg-gray-50">
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="flex items-center">
                  <FileText class="w-5 h-5 text-gray-400 mr-2" />
                  <div class="text-sm font-medium text-gray-900 truncate max-w-xs">
                    {{ task.file_name }}
                  </div>
                </div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <StatusBadge :status="task.status" />
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {{ formatRelativeTime(task.created_at) }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm">
                <router-link
                  :to="`/tasks/${task.task_id}`"
                  class="text-primary-600 hover:text-primary-700 flex items-center"
                >
                  <Eye class="w-4 h-4 mr-1" />
                  查看
                </router-link>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="recentTasks.length > 0" class="mt-4 text-center">
        <router-link to="/tasks" class="text-sm text-primary-600 hover:text-primary-700">
          查看全部任务 →
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useTaskStore, useQueueStore } from '@/stores'
import { formatRelativeTime } from '@/utils/format'
import StatCard from '@/components/StatCard.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'
import {
  Clock,
  Loader,
  CheckCircle,
  XCircle,
  Upload,
  ListTodo,
  Settings,
  RefreshCw,
  FileText,
  Eye,
  FileQuestion,
} from 'lucide-vue-next'

const taskStore = useTaskStore()
const queueStore = useQueueStore()

// 计算最近的任务（最多显示10个）
const recentTasks = computed(() => {
  return taskStore.tasks.slice(0, 10)
})

async function refreshTasks() {
  await taskStore.fetchTasks(undefined, 10)
}

onMounted(async () => {
  // 加载最近任务
  await refreshTasks()
  // 队列统计由 AppLayout 自动刷新
})
</script>

