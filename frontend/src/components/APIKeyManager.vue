<template>
  <div class="space-y-6">
    <!-- 标题和创建按钮 -->
    <div class="flex justify-between items-center">
      <h3 class="text-lg font-semibold text-gray-900">{{ $t('apiKey.title') }}</h3>
      <button
        @click="showCreateDialog = true"
        class="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
      >
        {{ $t('apiKey.createNew') }}
      </button>
    </div>

    <!-- Token 列表 -->
    <div v-if="loading" class="flex justify-center py-8">
      <LoadingSpinner />
    </div>

    <div v-else-if="apiKeys.length === 0" class="text-center py-8 text-gray-500">
      <p>{{ $t('apiKey.noTokens') }}</p>
      <p class="text-sm mt-2">{{ $t('apiKey.noTokensDesc') }}</p>
    </div>

    <div v-else class="space-y-3">
      <div
        v-for="key in apiKeys"
        :key="key.key_id"
        class="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
      >
        <div class="flex items-start justify-between">
          <div class="flex-1">
            <div class="flex items-center gap-3">
              <h4 class="text-base font-medium text-gray-900">{{ key.name }}</h4>
              <span
                :class="isExpired(key.expires_at) ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'"
                class="px-2 py-0.5 text-xs font-medium rounded"
              >
                {{ isExpired(key.expires_at) ? $t('apiKey.expired') : $t('apiKey.valid') }}
              </span>
              <span
                v-if="key.webhook_enabled"
                class="px-2 py-0.5 text-xs font-medium rounded bg-indigo-100 text-indigo-700"
                :title="key.webhook_url"
              >
                {{ $t('apiKey.webhookConfigured') }}
              </span>
            </div>

            <div class="mt-2 space-y-1 text-sm text-gray-600">
              <div class="flex items-center gap-2">
                <Key class="w-4 h-4" />
                <code class="bg-gray-100 px-2 py-0.5 rounded font-mono">{{ key.prefix }}...</code>
              </div>
              <div class="flex items-center gap-2">
                <Calendar class="w-4 h-4" />
                <span>{{ $t('apiKey.createdAt') }} {{ formatDate(key.created_at) }}</span>
              </div>
              <div v-if="key.expires_at" class="flex items-center gap-2">
                <Clock class="w-4 h-4" />
                <span>{{ $t('apiKey.expiresAtLabel') }} {{ formatDate(key.expires_at) }}</span>
              </div>
            </div>
          </div>

          <div class="ml-4 flex items-center gap-1">
            <button
              @click="webhookTarget = key"
              class="p-2 text-gray-500 hover:bg-gray-100 hover:text-primary-600 rounded-lg transition-colors"
              :title="$t('apiKey.webhookTitle')"
            >
              <Webhook class="w-4 h-4" />
            </button>
            <button
              @click="confirmDelete(key)"
              class="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
              :title="$t('common.delete')"
            >
              <Trash2 class="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Key 级 Webhook 回调配置对话框 -->
    <KeyWebhookDialog
      v-if="webhookTarget"
      :key-id="webhookTarget.key_id"
      :key-name="webhookTarget.name"
      @close="webhookTarget = null"
      @saved="loadAPIKeys"
    />

    <!-- 创建 Token 对话框 -->
    <div
      v-if="showCreateDialog"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      @click.self="showCreateDialog = false"
    >
      <div class="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
        <h3 class="text-lg font-semibold text-gray-900 mb-4">{{ $t('apiKey.createNew') }}</h3>

        <form @submit.prevent="handleCreate" class="space-y-4">
          <div>
            <label for="token-name" class="block text-sm font-medium text-gray-700 mb-1">
              {{ $t('apiKey.tokenName') }}
            </label>
            <input
              id="token-name"
              v-model="createForm.name"
              type="text"
              required
              :placeholder="$t('apiKey.tokenNamePlaceholder')"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          <div>
            <label for="token-expires" class="block text-sm font-medium text-gray-700 mb-1">
              {{ $t('apiKey.expiresAt') }}
            </label>
            <select
              id="token-expires"
              v-model="createForm.expires_days"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option :value="30">{{ $t('apiKey.days30') }}</option>
              <option :value="90">{{ $t('apiKey.days90') }}</option>
              <option :value="180">{{ $t('apiKey.days180') }}</option>
              <option :value="365">{{ $t('apiKey.days365') }}</option>
              <option :value="10950">{{ $t('apiKey.years30') }}</option>
            </select>
          </div>

          <div class="flex gap-3 pt-4">
            <button
              type="submit"
              :disabled="creating"
              class="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {{ creating ? $t('apiKey.creating') : $t('apiKey.create') }}
            </button>
            <button
              type="button"
              @click="showCreateDialog = false"
              class="flex-1 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2"
            >
              {{ $t('common.cancel') }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Token 创建成功对话框 -->
    <div
      v-if="newToken"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      @click.self="newToken = null"
    >
      <div class="bg-white rounded-lg shadow-xl max-w-lg w-full mx-4 p-6">
        <div class="flex items-center gap-3 mb-4">
          <div class="p-2 bg-green-100 rounded-full">
            <CheckCircle class="w-6 h-6 text-green-600" />
          </div>
          <h3 class="text-lg font-semibold text-gray-900">{{ $t('apiKey.createSuccessTitle') }}</h3>
        </div>

        <div class="mb-4">
          <p class="text-sm text-gray-600 mb-2">
            {{ $t('apiKey.createSuccessDesc') }}
          </p>
          <div class="flex items-center gap-2 bg-gray-100 p-3 rounded-lg">
            <code class="flex-1 text-sm font-mono break-all">{{ newToken }}</code>
            <button
              @click="copyToken"
              class="p-2 text-gray-600 hover:text-blue-600 transition-colors"
              :title="$t('common.copy')"
            >
              <Copy class="w-4 h-4" />
            </button>
          </div>
        </div>

        <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-3 mb-4">
          <p class="text-xs text-yellow-800">
            {{ $t('apiKey.createSuccessWarning') }}
          </p>
        </div>

        <button
          @click="newToken = null"
          class="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
        >
          {{ $t('apiKey.saved') }}
        </button>
      </div>
    </div>

    <!-- 删除确认对话框 -->
    <ConfirmDialog
      :model-value="!!deleteTarget"
      :title="$t('apiKey.confirmDelete')"
      :message="$t('apiKey.confirmDeleteMsg', { name: deleteTarget?.name })"
      :confirm-text="$t('common.delete')"
      :cancel-text="$t('common.cancel')"
      @confirm="handleDelete"
      @cancel="deleteTarget = null"
      @update:model-value="(v) => { if (!v) deleteTarget = null }"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { Key, Calendar, Clock, Trash2, CheckCircle, Copy, Webhook } from 'lucide-vue-next'
import * as authApi from '@/api/authApi'
import type { APIKeyResponse } from '@/api/types'
import { formatDate } from '@/utils/format'
import { showToast } from '@/utils/toast'
import LoadingSpinner from './LoadingSpinner.vue'
import ConfirmDialog from './ConfirmDialog.vue'
import KeyWebhookDialog from './KeyWebhookDialog.vue'

const { t } = useI18n()
const loading = ref(false)
const creating = ref(false)
const apiKeys = ref<any[]>([])
const showCreateDialog = ref(false)
const newToken = ref<string | null>(null)
const deleteTarget = ref<any | null>(null)
const webhookTarget = ref<any | null>(null)

const createForm = ref({
  name: '',
  expires_days: 90,
})

// 检查是否过期
function isExpired(expiresAt?: string): boolean {
  if (!expiresAt) return false
  return new Date(expiresAt) < new Date()
}

// 加载 API Keys
async function loadAPIKeys() {
  try {
    loading.value = true
    const response = await authApi.getAPIKeys()
    apiKeys.value = response.api_keys || []
  } catch (error: any) {
    console.error('Failed to load API keys:', error)
    showToast({ message: t('apiKey.loadFailed'), type: 'error' })
  } finally {
    loading.value = false
  }
}

// 创建 Token
async function handleCreate() {
  try {
    creating.value = true
    const response = await authApi.createAPIKey({
      name: createForm.value.name,
      expires_days: createForm.value.expires_days,
    })

    newToken.value = response.api_key
    showCreateDialog.value = false
    createForm.value = { name: '', expires_days: 90 }

    // 重新加载列表
    await loadAPIKeys()
    showToast({ message: t('apiKey.createSuccess'), type: 'success' })
  } catch (error: any) {
    console.error('Failed to create API key:', error)
    const message = error.response?.data?.detail || t('apiKey.createFailed')
    showToast({ message, type: 'error' })
  } finally {
    creating.value = false
  }
}

// 确认删除
function confirmDelete(key: any) {
  deleteTarget.value = key
}

// 删除 Token
async function handleDelete() {
  if (!deleteTarget.value) return

  try {
    await authApi.deleteAPIKey(deleteTarget.value.key_id)
    showToast({ message: t('apiKey.deleteSuccess'), type: 'success' })
    deleteTarget.value = null
    await loadAPIKeys()
  } catch (error: any) {
    console.error('Failed to delete API key:', error)
    const message = error.response?.data?.detail || t('apiKey.deleteFailed')
    showToast({ message, type: 'error' })
  }
}

// 复制 Token
async function copyToken() {
  if (!newToken.value) return

  try {
    await navigator.clipboard.writeText(newToken.value)
    showToast({ message: t('apiKey.copied'), type: 'success' })
  } catch (error) {
    console.error('Failed to copy:', error)
    showToast({ message: t('apiKey.copyFailed'), type: 'error' })
  }
}

onMounted(() => {
  loadAPIKeys()
})
</script>
