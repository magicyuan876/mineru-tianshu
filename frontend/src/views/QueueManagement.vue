<template>
  <div>
    <!-- 页面标题 -->
    <div class="mb-6">
      <h1 class="text-2xl font-bold text-gray-900">队列管理</h1>
      <p class="mt-1 text-sm text-gray-600">系统监控和管理操作</p>
    </div>

    <div class="space-y-6">
      <!-- 队列统计卡片 -->
      <div>
        <h2 class="text-lg font-semibold text-gray-900 mb-4">队列统计</h2>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <StatCard
            title="待处理"
            :value="queueStore.stats.pending"
            subtitle="等待处理的任务"
            :icon="Clock"
            color="gray"
          />
          <StatCard
            title="处理中"
            :value="queueStore.stats.processing"
            subtitle="正在解析的任务"
            :icon="Loader"
            color="yellow"
          />
          <StatCard
            title="总计"
            :value="queueStore.total"
            subtitle="所有任务总数"
            :icon="Database"
            color="blue"
          />
        </div>
      </div>

      <!-- 历史统计 -->
      <div class="card">
        <h2 class="text-lg font-semibold text-gray-900 mb-4">历史统计</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="p-4 bg-green-50 rounded-lg">
            <div class="flex items-center justify-between">
              <div>
                <p class="text-sm text-gray-600">已完成</p>
                <p class="mt-1 text-2xl font-semibold text-green-600">{{ queueStore.stats.completed }}</p>
              </div>
              <CheckCircle class="w-10 h-10 text-green-500" />
            </div>
          </div>
          <div class="p-4 bg-red-50 rounded-lg">
            <div class="flex items-center justify-between">
              <div>
                <p class="text-sm text-gray-600">失败</p>
                <p class="mt-1 text-2xl font-semibold text-red-600">{{ queueStore.stats.failed }}</p>
              </div>
              <XCircle class="w-10 h-10 text-red-500" />
            </div>
          </div>
        </div>
        <div v-if="queueStore.lastUpdate" class="mt-4 text-xs text-gray-500 text-right">
          最后更新: {{ formatDateTime(queueStore.lastUpdate) }}
        </div>
      </div>

      <!-- 管理操作 -->
      <div class="card">
        <h2 class="text-lg font-semibold text-gray-900 mb-4">管理操作</h2>

        <div class="space-y-4">
          <!-- 重置超时任务 -->
          <div class="flex items-start justify-between p-4 bg-gray-50 rounded-lg">
            <div class="flex-1">
              <h3 class="text-sm font-medium text-gray-900">重置超时任务</h3>
              <p class="mt-1 text-sm text-gray-600">
                将超时的 processing 任务重置为 pending 状态，以便重新处理
              </p>
              <div class="mt-2">
                <label class="text-xs text-gray-500">超时时间（分钟）:</label>
                <input
                  v-model.number="resetStaleTimeout"
                  type="number"
                  min="5"
                  max="180"
                  class="ml-2 w-20 px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>
            </div>
            <button
              @click="handleResetStale"
              :disabled="resetting"
              class="btn btn-secondary flex items-center"
            >
              <RotateCcw :class="{ 'animate-spin': resetting }" class="w-4 h-4 mr-2" />
              {{ resetting ? '重置中...' : '重置' }}
            </button>
          </div>

          <!-- 清理旧任务文件 -->
          <div class="flex items-start justify-between p-4 bg-gray-50 rounded-lg">
            <div class="flex-1">
              <h3 class="text-sm font-medium text-gray-900">清理旧任务文件</h3>
              <p class="mt-1 text-sm text-gray-600">
                清理 N 天前的任务结果文件（保留数据库记录）
              </p>
              <div class="mt-2">
                <label class="text-xs text-gray-500">保留天数:</label>
                <input
                  v-model.number="cleanupFileDays"
                  type="number"
                  min="1"
                  max="90"
                  class="ml-2 w-20 px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>
            </div>
            <button
              @click="handleCleanupFiles"
              :disabled="cleaningFiles"
              class="btn btn-secondary flex items-center"
            >
              <Trash2 :class="{ 'animate-pulse': cleaningFiles }" class="w-4 h-4 mr-2" />
              {{ cleaningFiles ? '清理中...' : '清理文件' }}
            </button>
          </div>

          <!-- 健康检查 -->
          <div class="flex items-start justify-between p-4 bg-gray-50 rounded-lg">
            <div class="flex-1">
              <h3 class="text-sm font-medium text-gray-900">系统健康检查</h3>
              <p class="mt-1 text-sm text-gray-600">
                检查后端服务和数据库连接状态
              </p>
              <div v-if="healthStatus" class="mt-2">
                <div
                  :class="healthStatus.status === 'healthy' ? 'text-green-600' : 'text-red-600'"
                  class="text-xs"
                >
                  状态: {{ healthStatus.status === 'healthy' ? '健康' : '异常' }}
                </div>
              </div>
            </div>
            <button
              @click="handleHealthCheck"
              :disabled="checking"
              class="btn btn-secondary flex items-center"
            >
              <Activity :class="{ 'animate-pulse': checking }" class="w-4 h-4 mr-2" />
              {{ checking ? '检查中...' : '健康检查' }}
            </button>
          </div>
        </div>
      </div>

      <!-- 操作日志 -->
      <div v-if="operationLogs.length > 0" class="card">
        <h2 class="text-lg font-semibold text-gray-900 mb-4">操作日志</h2>
        <div class="space-y-2">
          <div
            v-for="(log, index) in operationLogs"
            :key="index"
            class="flex items-start p-3 bg-gray-50 rounded-lg"
          >
            <component
              :is="log.type === 'success' ? CheckCircle : log.type === 'error' ? XCircle : Info"
              :class="{
                'text-green-600': log.type === 'success',
                'text-red-600': log.type === 'error',
                'text-blue-600': log.type === 'info'
              }"
              class="w-5 h-5 flex-shrink-0 mt-0.5"
            />
            <div class="ml-3 flex-1">
              <p class="text-sm text-gray-900">{{ log.message }}</p>
              <p class="mt-1 text-xs text-gray-500">{{ formatRelativeTime(log.timestamp) }}</p>
            </div>
          </div>
        </div>
        <div class="mt-4 text-center">
          <button
            @click="operationLogs = []"
            class="text-sm text-gray-600 hover:text-gray-900"
          >
            清空日志
          </button>
        </div>
      </div>

      <!-- 确认对话框 -->
      <ConfirmDialog
        v-model="showConfirmDialog"
        :title="confirmDialog.title"
        :message="confirmDialog.message"
        :type="confirmDialog.type"
        @confirm="confirmDialog.onConfirm"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useQueueStore } from '@/stores'
import { formatDateTime, formatRelativeTime } from '@/utils/format'
import StatCard from '@/components/StatCard.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import {
  Clock,
  Loader,
  Database,
  CheckCircle,
  XCircle,
  RotateCcw,
  Trash2,
  Activity,
  Info,
} from 'lucide-vue-next'

const queueStore = useQueueStore()

const resetStaleTimeout = ref(60)
const cleanupFileDays = ref(7)

const resetting = ref(false)
const cleaningFiles = ref(false)
const checking = ref(false)

const healthStatus = ref<any>(null)

interface OperationLog {
  type: 'success' | 'error' | 'info'
  message: string
  timestamp: string
}

const operationLogs = ref<OperationLog[]>([])

function addLog(type: OperationLog['type'], message: string) {
  operationLogs.value.unshift({
    type,
    message,
    timestamp: new Date().toISOString(),
  })
  // 只保留最近10条
  if (operationLogs.value.length > 10) {
    operationLogs.value = operationLogs.value.slice(0, 10)
  }
}

// 确认对话框
const showConfirmDialog = ref(false)
const confirmDialog = reactive({
  title: '',
  message: '',
  type: 'warning' as 'danger' | 'warning' | 'info',
  onConfirm: () => {},
})

async function handleResetStale() {
  confirmDialog.title = '确认重置超时任务'
  confirmDialog.message = `将重置所有超过 ${resetStaleTimeout.value} 分钟的处理中任务。确定继续吗？`
  confirmDialog.type = 'warning'
  confirmDialog.onConfirm = async () => {
    resetting.value = true
    try {
      const response = await queueStore.resetStaleTasks(resetStaleTimeout.value)
      addLog('success', `成功重置 ${response.reset_count || 0} 个超时任务`)
    } catch (err: any) {
      addLog('error', `重置失败: ${err.message}`)
    } finally {
      resetting.value = false
    }
  }
  showConfirmDialog.value = true
}

async function handleCleanupFiles() {
  confirmDialog.title = '确认清理文件'
  confirmDialog.message = `将删除 ${cleanupFileDays.value} 天前的任务结果文件（保留数据库记录）。此操作不可恢复，确定继续吗？`
  confirmDialog.type = 'danger'
  confirmDialog.onConfirm = async () => {
    cleaningFiles.value = true
    try {
      const response = await queueStore.cleanupOldTasks(cleanupFileDays.value)
      addLog('success', `成功清理 ${response.deleted_count || 0} 个旧任务文件`)
    } catch (err: any) {
      addLog('error', `清理失败: ${err.message}`)
    } finally {
      cleaningFiles.value = false
    }
  }
  showConfirmDialog.value = true
}

async function handleHealthCheck() {
  checking.value = true
  try {
    const response = await queueStore.checkHealth()
    healthStatus.value = response
    addLog('success', '系统健康检查通过')
  } catch (err: any) {
    healthStatus.value = { status: 'unhealthy' }
    addLog('error', `健康检查失败: ${err.message}`)
  } finally {
    checking.value = false
  }
}
</script>
