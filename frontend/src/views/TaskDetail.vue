<template>
  <div>
    <!-- 返回按钮 -->
    <div class="mb-4">
      <button
        @click="$router.back()"
        class="text-sm text-gray-600 hover:text-gray-900 flex items-center"
      >
        <ArrowLeft class="w-4 h-4 mr-1" />
        返回
      </button>
    </div>

    <!-- 页面标题 -->
    <div class="mb-6">
      <h1 class="text-2xl font-bold text-gray-900">任务详情</h1>
      <p class="mt-1 text-sm text-gray-600">查看任务状态和解析结果</p>
    </div>

    <div v-if="loading && !task" class="text-center py-12">
      <LoadingSpinner size="lg" text="加载中..." />
    </div>

    <div v-else-if="error" class="card bg-red-50 border-red-200">
      <div class="flex items-center">
        <AlertCircle class="w-6 h-6 text-red-600" />
        <p class="ml-3 text-red-800">{{ error }}</p>
      </div>
    </div>

    <div v-else-if="task" class="space-y-6">
      <!-- 基本信息卡片 -->
      <div class="card">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-lg font-semibold text-gray-900">基本信息</h2>
          <StatusBadge :status="task.status" />
        </div>

        <dl class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <dt class="text-sm font-medium text-gray-500">任务 ID</dt>
            <dd class="mt-1 text-sm text-gray-900 font-mono">{{ task.task_id }}</dd>
          </div>
          <div>
            <dt class="text-sm font-medium text-gray-500">文件名</dt>
            <dd class="mt-1 text-sm text-gray-900">{{ task.file_name }}</dd>
          </div>
          <div>
            <dt class="text-sm font-medium text-gray-500">处理后端</dt>
            <dd class="mt-1 text-sm text-gray-900">{{ task.backend }}</dd>
          </div>
          <div>
            <dt class="text-sm font-medium text-gray-500">优先级</dt>
            <dd class="mt-1 text-sm text-gray-900">{{ task.priority }}</dd>
          </div>
          <div>
            <dt class="text-sm font-medium text-gray-500">创建时间</dt>
            <dd class="mt-1 text-sm text-gray-900">{{ formatDateTime(task.created_at) }}</dd>
          </div>
          <div>
            <dt class="text-sm font-medium text-gray-500">开始时间</dt>
            <dd class="mt-1 text-sm text-gray-900">{{ formatDateTime(task.started_at) }}</dd>
          </div>
          <div>
            <dt class="text-sm font-medium text-gray-500">完成时间</dt>
            <dd class="mt-1 text-sm text-gray-900">{{ formatDateTime(task.completed_at) }}</dd>
          </div>
          <div>
            <dt class="text-sm font-medium text-gray-500">Worker ID</dt>
            <dd class="mt-1 text-sm text-gray-900 font-mono">{{ task.worker_id || '-' }}</dd>
          </div>
          <div v-if="task.started_at && task.completed_at">
            <dt class="text-sm font-medium text-gray-500">处理时长</dt>
            <dd class="mt-1 text-sm text-gray-900">{{ formatDuration(task.started_at, task.completed_at) }}</dd>
          </div>
          <div>
            <dt class="text-sm font-medium text-gray-500">重试次数</dt>
            <dd class="mt-1 text-sm text-gray-900">{{ task.retry_count }}</dd>
          </div>
        </dl>

        <!-- 错误信息 -->
        <div v-if="task.error_message" class="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
          <div class="flex items-start">
            <AlertCircle class="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            <div class="ml-3">
              <h4 class="text-sm font-medium text-red-800">错误信息</h4>
              <p class="mt-1 text-sm text-red-700 font-mono">{{ task.error_message }}</p>
            </div>
          </div>
        </div>

        <!-- 操作按钮 -->
        <div class="mt-6 flex gap-3">
          <button
            v-if="task.status === 'pending'"
            @click="handleCancel"
            :disabled="cancelling"
            class="btn btn-secondary flex items-center"
          >
            <X class="w-4 h-4 mr-2" />
            取消任务
          </button>
          <button
            v-if="task.status === 'completed' && task.data"
            @click="downloadMarkdown"
            class="btn btn-primary flex items-center"
          >
            <Download class="w-4 h-4 mr-2" />
            下载 Markdown
          </button>
          <button
            @click="refreshTask"
            :disabled="loading"
            class="btn btn-secondary flex items-center"
          >
            <RefreshCw :class="{ 'animate-spin': loading }" class="w-4 h-4 mr-2" />
            刷新
          </button>
        </div>
      </div>

      <!-- 状态时间轴 -->
      <div class="card">
        <h2 class="text-lg font-semibold text-gray-900 mb-4">状态时间轴</h2>
        <div class="relative">
          <div class="absolute left-4 top-0 bottom-0 w-0.5 bg-gray-200"></div>
          
          <div class="space-y-4">
            <!-- 创建 -->
            <div class="relative flex items-start">
              <div class="absolute left-0 w-8 h-8 rounded-full bg-green-100 flex items-center justify-center">
                <CheckCircle class="w-5 h-5 text-green-600" />
              </div>
              <div class="ml-12">
                <h3 class="text-sm font-medium text-gray-900">任务创建</h3>
                <p class="mt-1 text-sm text-gray-500">{{ formatDateTime(task.created_at) }}</p>
              </div>
            </div>

            <!-- 处理中 -->
            <div class="relative flex items-start">
              <div :class="task.started_at ? 'bg-green-100' : 'bg-gray-100'" class="absolute left-0 w-8 h-8 rounded-full flex items-center justify-center">
                <component
                  :is="task.started_at ? CheckCircle : Circle"
                  :class="task.started_at ? 'text-green-600' : 'text-gray-400'"
                  class="w-5 h-5"
                />
              </div>
              <div class="ml-12">
                <h3 class="text-sm font-medium text-gray-900">开始处理</h3>
                <p class="mt-1 text-sm text-gray-500">{{ formatDateTime(task.started_at) }}</p>
              </div>
            </div>

            <!-- 完成 -->
            <div class="relative flex items-start">
              <div
                :class="task.completed_at ? (task.status === 'completed' ? 'bg-green-100' : 'bg-red-100') : 'bg-gray-100'"
                class="absolute left-0 w-8 h-8 rounded-full flex items-center justify-center"
              >
                <component
                  :is="task.completed_at ? (task.status === 'completed' ? CheckCircle : XCircle) : Circle"
                  :class="task.completed_at ? (task.status === 'completed' ? 'text-green-600' : 'text-red-600') : 'text-gray-400'"
                  class="w-5 h-5"
                />
              </div>
              <div class="ml-12">
                <h3 class="text-sm font-medium text-gray-900">
                  {{ task.status === 'completed' ? '完成' : task.status === 'failed' ? '失败' : '待完成' }}
                </h3>
                <p class="mt-1 text-sm text-gray-500">{{ formatDateTime(task.completed_at) }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Markdown 预览 -->
      <div v-if="task.status === 'completed' && task.data" class="card">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-lg font-semibold text-gray-900">解析结果</h2>
          <div class="flex items-center gap-2 text-sm text-gray-500">
            <FileText class="w-4 h-4" />
            {{ task.data.markdown_file }}
          </div>
        </div>
        <MarkdownViewer :content="task.data.content" />
      </div>

      <!-- 处理中提示 -->
      <div v-if="task.status === 'processing'" class="card bg-yellow-50 border-yellow-200">
        <div class="flex items-center">
          <Loader class="w-6 h-6 text-yellow-600 animate-spin" />
          <div class="ml-3">
            <h3 class="text-sm font-medium text-yellow-800">任务处理中</h3>
            <p class="mt-1 text-sm text-yellow-700">页面会自动刷新，请稍候...</p>
          </div>
        </div>
      </div>

      <!-- 等待中提示 -->
      <div v-if="task.status === 'pending'" class="card bg-gray-50 border-gray-200">
        <div class="flex items-center">
          <Clock class="w-6 h-6 text-gray-600" />
          <div class="ml-3">
            <h3 class="text-sm font-medium text-gray-800">任务等待中</h3>
            <p class="mt-1 text-sm text-gray-700">任务正在队列中等待处理...</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTaskStore } from '@/stores'
import { formatDateTime, formatDuration } from '@/utils/format'
import StatusBadge from '@/components/StatusBadge.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'
import MarkdownViewer from '@/components/MarkdownViewer.vue'
import {
  ArrowLeft,
  AlertCircle,
  CheckCircle,
  XCircle,
  Circle,
  X,
  Download,
  RefreshCw,
  FileText,
  Loader,
  Clock,
} from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const taskStore = useTaskStore()

const taskId = computed(() => route.params.id as string)
const task = computed(() => taskStore.currentTask)
const loading = ref(false)
const error = ref('')
const cancelling = ref(false)
let stopPolling: (() => void) | null = null

async function refreshTask() {
  loading.value = true
  error.value = ''
  try {
    await taskStore.fetchTaskStatus(taskId.value)
  } catch (err: any) {
    error.value = err.message || '加载任务失败'
  } finally {
    loading.value = false
  }
}

async function handleCancel() {
  if (!confirm('确定要取消此任务吗？')) return
  
  cancelling.value = true
  try {
    await taskStore.cancelTask(taskId.value)
    await refreshTask()
  } catch (err: any) {
    alert(`取消失败: ${err.message}`)
  } finally {
    cancelling.value = false
  }
}

function downloadMarkdown() {
  if (!task.value?.data?.content) return
  
  const blob = new Blob([task.value.data.content], { type: 'text/markdown' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = task.value.data.markdown_file || `${taskId.value}.md`
  a.click()
  URL.revokeObjectURL(url)
}

onMounted(async () => {
  await refreshTask()
  
  // 如果任务未完成，启动轮询
  if (task.value && (task.value.status === 'pending' || task.value.status === 'processing')) {
    stopPolling = taskStore.pollTaskStatus(taskId.value, 2000, async (updatedTask) => {
      // 轮询回调
      if (updatedTask.status === 'completed' || updatedTask.status === 'failed') {
        // 任务完成，停止轮询
        if (stopPolling) {
          stopPolling()
          stopPolling = null
        }
      }
    })
  }
})

onUnmounted(() => {
  if (stopPolling) {
    stopPolling()
    stopPolling = null
  }
})
</script>

