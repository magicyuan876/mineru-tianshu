<template>
  <div class="w-full">
    <PageHeader :title="$t('queue.title')" :description="$t('queue.stats')" />

    <div class="space-y-6">
      <!-- 队列统计卡片 -->
      <div>
        <h2 class="text-lg font-semibold text-gray-900 mb-4">{{ $t('queue.stats') }}</h2>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <StatCard
            :title="$t('queue.pending')"
            :value="queueStore.stats.pending"
            :subtitle="$t('queue.pending')"
            :icon="Clock"
            color="gray"
          />
          <StatCard
            :title="$t('queue.processing')"
            :value="queueStore.stats.processing"
            :subtitle="$t('queue.processing')"
            :icon="Loader"
            color="yellow"
          />
          <StatCard
            :title="$t('queue.total')"
            :value="queueStore.total"
            :subtitle="$t('queue.allTasks')"
            :icon="Database"
            color="blue"
          />
        </div>
      </div>

      <!-- 历史统计 -->
      <div class="card">
        <h2 class="text-lg font-semibold text-gray-900 mb-4">{{ $t('queue.historyStats') }}</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="p-4 bg-green-50 rounded-lg">
            <div class="flex items-center justify-between">
              <div>
                <p class="text-sm text-gray-600">{{ $t('queue.completed') }}</p>
                <p class="mt-1 text-2xl font-semibold text-green-600">{{ queueStore.stats.completed }}</p>
              </div>
              <CheckCircle class="w-10 h-10 text-green-500" />
            </div>
          </div>
          <div class="p-4 bg-red-50 rounded-lg">
            <div class="flex items-center justify-between">
              <div>
                <p class="text-sm text-gray-600">{{ $t('queue.failed') }}</p>
                <p class="mt-1 text-2xl font-semibold text-red-600">{{ queueStore.stats.failed }}</p>
              </div>
              <XCircle class="w-10 h-10 text-red-500" />
            </div>
          </div>
        </div>
        <div v-if="queueStore.lastUpdate" class="mt-4 text-xs text-gray-500 text-right">
          {{ $t('queue.lastUpdate') }}: {{ formatDateTime(queueStore.lastUpdate) }}
        </div>
      </div>

      <!-- 管理操作 -->
      <div class="card">
        <h2 class="text-lg font-semibold text-gray-900 mb-4">{{ $t('queue.management') }}</h2>

        <div class="space-y-4">
          <!-- 重置超时任务 -->
          <div class="flex items-start justify-between p-4 bg-gray-50 rounded-lg">
            <div class="flex-1">
              <h3 class="text-sm font-medium text-gray-900">{{ $t('queue.resetStale') }}</h3>
              <p class="mt-1 text-sm text-gray-600">
                {{ $t('queue.resetStaleDesc') }}
              </p>
              <div class="mt-2">
                <label class="text-xs text-gray-500">{{ $t('queue.timeoutMinutes') }}:</label>
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
              {{ resetting ? $t('queue.resetting') : $t('queue.reset') }}
            </button>
          </div>

          <!-- 清理旧任务 -->
          <div class="flex items-start justify-between p-4 bg-gray-50 rounded-lg">
            <div class="flex-1">
              <h3 class="text-sm font-medium text-gray-900">{{ $t('queue.cleanupOld') }}</h3>
              <p class="mt-1 text-sm text-gray-600">
                {{ $t('queue.cleanupOldDesc') }}
              </p>
              <div class="mt-2">
                <label class="text-xs text-gray-500">{{ $t('queue.retentionDays') }}:</label>
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
              {{ cleaningFiles ? $t('queue.cleaning') : $t('queue.cleanupTask') }}
            </button>
          </div>

          <!-- 健康检查 -->
          <div class="flex items-start justify-between p-4 bg-gray-50 rounded-lg">
            <div class="flex-1">
              <h3 class="text-sm font-medium text-gray-900">{{ $t('queue.healthCheck') }}</h3>
              <p class="mt-1 text-sm text-gray-600">
                {{ $t('queue.healthCheckDesc') }}
              </p>
              <div v-if="healthStatus" class="mt-2">
                <div
                  :class="healthStatus.status === 'healthy' ? 'text-green-600' : 'text-red-600'"
                  class="text-xs"
                >
                  {{ $t('queue.statusLabel') }}: {{ healthStatus.status === 'healthy' ? $t('queue.healthy') : $t('queue.unhealthy') }}
                </div>
              </div>
            </div>
            <button
              @click="handleHealthCheck"
              :disabled="checking"
              class="btn btn-secondary flex items-center"
            >
              <Activity :class="{ 'animate-pulse': checking }" class="w-4 h-4 mr-2" />
              {{ checking ? $t('queue.checking') : $t('queue.healthCheck') }}
            </button>
          </div>
        </div>
      </div>

      <!-- 操作日志 -->
      <div v-if="operationLogs.length > 0" class="card">
        <h2 class="text-lg font-semibold text-gray-900 mb-4">{{ $t('queue.operationLog') }}</h2>
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
            {{ $t('queue.clearLog') }}
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
import { useI18n } from 'vue-i18n'
import { useQueueStore } from '@/stores'
import { formatDateTime, formatRelativeTime } from '@/utils/format'

const { t } = useI18n()
import StatCard from '@/components/StatCard.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import PageHeader from '@/components/PageHeader.vue'
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
  confirmDialog.title = t('queue.confirmResetStale')
  confirmDialog.message = t('queue.confirmResetStaleMsg', { timeout: resetStaleTimeout.value })
  confirmDialog.type = 'warning'
  confirmDialog.onConfirm = async () => {
    resetting.value = true
    try {
      const response = await queueStore.resetStaleTasks(resetStaleTimeout.value)
      addLog('success', t('queue.resetSuccess', { count: response.reset_count || 0 }))
    } catch (err: any) {
      addLog('error', `${t('queue.resetFailed')}: ${err.message}`)
    } finally {
      resetting.value = false
    }
  }
  showConfirmDialog.value = true
}

async function handleCleanupFiles() {
  confirmDialog.title = t('queue.confirmCleanup')
  confirmDialog.message = t('queue.confirmCleanupMsg', { days: cleanupFileDays.value })
  confirmDialog.type = 'danger'
  confirmDialog.onConfirm = async () => {
    cleaningFiles.value = true
    try {
      const response = await queueStore.cleanupOldTasks(cleanupFileDays.value)
      addLog('success', t('queue.cleanupSuccess', { count: response.deleted_count || 0 }))
    } catch (err: any) {
      addLog('error', `${t('queue.cleanupFailed')}: ${err.message}`)
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
    addLog('success', t('queue.healthCheckSuccess'))
  } catch (err: any) {
    healthStatus.value = { status: 'unhealthy' }
    addLog('error', `${t('queue.healthCheckFailed')}: ${err.message}`)
  } finally {
    checking.value = false
  }
}
</script>
