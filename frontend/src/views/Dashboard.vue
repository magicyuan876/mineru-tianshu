<template>
  <div>
    <!-- 页面标题 -->
    <div class="mb-6 lg:mb-10">
      <h1 class="text-2xl lg:text-3xl xl:text-4xl font-bold text-gray-900 tracking-tight">{{ $t('dashboard.title') }}</h1>
      <p class="mt-2 lg:mt-3 text-base lg:text-lg text-gray-600">{{ $t('dashboard.systemStatus') }}</p>
    </div>

    <!-- 队列统计卡片 -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 lg:gap-6 mb-6 lg:mb-8">
      <StatCard
        :title="$t('status.pending')"
        :value="queueStore.stats.pending"
        :subtitle="$t('dashboard.pendingTasks')"
        :icon="Clock"
        color="gray"
      />
      <StatCard
        :title="$t('status.processing')"
        :value="queueStore.stats.processing"
        :subtitle="$t('dashboard.processingTasks')"
        :icon="Loader"
        color="yellow"
      />
      <StatCard
        :title="$t('status.completed')"
        :value="queueStore.stats.completed"
        :subtitle="$t('dashboard.completedTasks')"
        :icon="CheckCircle"
        color="green"
      />
      <StatCard
        :title="$t('status.failed')"
        :value="queueStore.stats.failed"
        :subtitle="$t('dashboard.failedTasks')"
        :icon="XCircle"
        color="red"
      />
    </div>

    <!-- 快捷操作 -->
    <div class="mb-6 lg:mb-8">
      <div class="card">
        <h2 class="text-base lg:text-lg font-semibold text-gray-900 mb-3 lg:mb-4">{{ $t('common.actions') }}</h2>
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-2 lg:gap-3">
          <router-link to="/tasks/submit" class="btn btn-primary flex items-center justify-center">
            <Upload class="w-4 h-4 mr-2" />
            {{ $t('task.submitTask') }}
          </router-link>
          <router-link to="/tasks" class="btn btn-secondary flex items-center justify-center">
            <ListTodo class="w-4 h-4 mr-2" />
            {{ $t('task.taskList') }}
          </router-link>
          <router-link to="/queue" class="btn btn-secondary flex items-center justify-center">
            <Settings class="w-4 h-4 mr-2" />
            {{ $t('queue.title') }}
          </router-link>
        </div>
      </div>
    </div>

    <!-- 引擎信息 -->
    <div class="mb-6 lg:mb-8">
      <EngineInfo />
    </div>

    <!-- 最近任务 -->
    <div class="card">
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
        <h2 class="text-base lg:text-lg font-semibold text-gray-900">{{ $t('dashboard.recentTasks') }}</h2>
        <button
          @click="refreshTasks"
          :disabled="taskStore.loading"
          class="text-sm text-primary-600 hover:text-primary-700 flex items-center justify-center sm:justify-start"
        >
          <RefreshCw :class="{ 'animate-spin': taskStore.loading }" class="w-4 h-4 mr-1" />
          {{ $t('common.refresh') }}
        </button>
      </div>

      <div v-if="taskStore.loading && recentTasks.length === 0" class="text-center py-8">
        <LoadingSpinner :text="$t('common.loading')" />
      </div>

      <div v-else-if="recentTasks.length === 0" class="text-center py-8 text-gray-500">
        <FileQuestion class="w-12 h-12 mx-auto mb-2 text-gray-400" />
        <p>{{ $t('task.noTasks') }}</p>
      </div>

      <div v-else class="overflow-x-auto -mx-4 sm:-mx-6 lg:-mx-8">
        <div class="inline-block min-w-full align-middle px-4 sm:px-6 lg:px-8">
          <table class="min-w-full divide-y divide-gray-200">
          <thead>
            <tr class="bg-gray-50">
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                {{ $t('task.fileName') }}
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                {{ $t('task.status') }}
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                {{ $t('task.createdAt') }}
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                {{ $t('task.actions') }}
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
import EngineInfo from '@/components/EngineInfo.vue'
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
