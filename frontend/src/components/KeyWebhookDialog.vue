<template>
  <div
    class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
    @click.self="$emit('close')"
  >
    <div class="bg-white rounded-xl shadow-xl max-w-lg w-full mx-4 p-6 max-h-[90vh] overflow-y-auto">
      <div class="mb-1 flex items-center gap-2">
        <Webhook class="w-5 h-5 text-primary-600" />
        <h3 class="text-lg font-semibold text-gray-900">{{ $t('apiKey.webhookTitle') }}</h3>
      </div>
      <p class="text-sm text-gray-500 mb-5">
        {{ $t('apiKey.webhookDesc', { name: keyName }) }}
      </p>

      <div v-if="loading" class="flex justify-center py-8">
        <LoadingSpinner />
      </div>

      <form v-else @submit.prevent="handleSave" class="space-y-4">
        <div class="flex items-center justify-between">
          <label class="text-sm font-medium text-gray-700">{{ $t('apiKey.webhookEnable') }}</label>
          <FormToggle v-model="form.enabled" />
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('webhook.url') }}</label>
          <input
            v-model="form.url"
            type="url"
            :placeholder="$t('webhook.urlPlaceholder')"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('webhook.secret') }}</label>
          <input
            v-model="form.secret"
            type="text"
            :placeholder="secretPlaceholder('secret')"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          />
          <p class="mt-1 text-xs text-gray-400">{{ $t('webhook.secretHelp') }}</p>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('webhook.authType') }}</label>
          <select
            v-model="form.auth_type"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          >
            <option value="none">{{ $t('webhook.authNone') }}</option>
            <option value="bearer">{{ $t('webhook.authBearer') }}</option>
            <option value="basic">{{ $t('webhook.authBasic') }}</option>
            <option value="api_key">{{ $t('webhook.authApiKey') }}</option>
          </select>
        </div>

        <div v-if="form.auth_type === 'bearer'">
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('webhook.authToken') }}</label>
          <input
            v-model="form.auth_token"
            type="text"
            :placeholder="secretPlaceholder('auth_token')"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          />
        </div>

        <div v-if="form.auth_type === 'basic'" class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('webhook.authUsername') }}</label>
            <input
              v-model="form.auth_username"
              type="text"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('webhook.authPassword') }}</label>
            <input
              v-model="form.auth_password"
              type="text"
              :placeholder="secretPlaceholder('auth_password')"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>
        </div>

        <div v-if="form.auth_type === 'api_key'" class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('webhook.authHeaderName') }}</label>
            <input
              v-model="form.auth_header_name"
              type="text"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('webhook.authHeaderValue') }}</label>
            <input
              v-model="form.auth_header_value"
              type="text"
              :placeholder="secretPlaceholder('auth_header_value')"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>
        </div>

        <div class="flex gap-3 pt-2">
          <button
            type="button"
            @click="handleTest"
            :disabled="testing || saving"
            class="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
            :title="$t('webhook.testKeyHint')"
          >
            {{ testing ? $t('webhook.testing') : $t('webhook.testConnection') }}
          </button>
          <button
            type="submit"
            :disabled="saving"
            class="flex-1 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ saving ? $t('webhook.saving') : $t('webhook.save') }}
          </button>
          <button
            type="button"
            @click="$emit('close')"
            class="flex-1 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2"
          >
            {{ $t('common.cancel') }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { Webhook } from 'lucide-vue-next'
import * as authApi from '@/api/authApi'
import type { APIKeyWebhookConfig } from '@/api/types'
import { showToast } from '@/utils/toast'
import FormToggle from './FormToggle.vue'
import LoadingSpinner from './LoadingSpinner.vue'

const props = defineProps<{
  keyId: string
  keyName: string
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'saved'): void
}>()

const { t } = useI18n()
const loading = ref(true)
const saving = ref(false)
const testing = ref(false)

// 敏感字段掩码占位符（与后端约定一致）
const MASK = '********'
// 记录加载时哪些敏感字段是已配置状态（决定占位符文案，不随后续输入变化）
const maskedFields = ref(new Set<string>())

const form = ref<APIKeyWebhookConfig>({
  enabled: false,
  url: '',
  secret: '',
  auth_type: 'none',
  auth_token: '',
  auth_username: '',
  auth_password: '',
  auth_header_name: 'X-API-Key',
  auth_header_value: '',
})

onMounted(async () => {
  try {
    const response = await authApi.getAPIKeyWebhook(props.keyId)
    form.value = response.webhook
    maskedFields.value = new Set(
      (['secret', 'auth_token', 'auth_password', 'auth_header_value'] as const).filter(
        (field) => response.webhook[field] === MASK,
      ),
    )
  } catch (error) {
    console.error('Failed to load key webhook config:', error)
    showToast({ message: t('apiKey.webhookLoadFailed'), type: 'error' })
  } finally {
    loading.value = false
  }
})

/**
 * 敏感字段占位符：已配置提示"留空不修改"，未配置明确显示"未设置"
 */
function secretPlaceholder(field: 'secret' | 'auth_token' | 'auth_password' | 'auth_header_value'): string {
  return maskedFields.value.has(field) ? t('webhook.secretPlaceholder') : t('webhook.secretNotSet')
}

async function handleSave() {
  if (form.value.enabled && !form.value.url.trim()) {
    showToast({ message: t('apiKey.webhookUrlRequired'), type: 'error' })
    return
  }
  try {
    saving.value = true
    await authApi.updateAPIKeyWebhook(props.keyId, form.value)
    showToast({ message: t('apiKey.webhookSaveSuccess'), type: 'success' })
    emit('saved')
    emit('close')
  } catch (error: any) {
    console.error('Failed to save key webhook config:', error)
    const message = error.response?.data?.detail || t('apiKey.webhookSaveFailed')
    showToast({ message, type: 'error' })
  } finally {
    saving.value = false
  }
}

/**
 * 测试投递：使用服务端已保存的配置（表单未保存的修改不参与）
 */
async function handleTest() {
  try {
    testing.value = true
    const result = await authApi.testAPIKeyWebhook(props.keyId)
    if (result.success) {
      showToast({ message: t('webhook.testSuccess', { code: result.status_code }), type: 'success' })
    } else {
      showToast({
        message: result.error || `${t('webhook.testFailed')} (HTTP ${result.status_code ?? '-'})`,
        type: 'error',
      })
    }
  } catch (error: any) {
    console.error('Failed to test key webhook:', error)
    showToast({ message: error.response?.data?.detail || t('webhook.testError'), type: 'error' })
  } finally {
    testing.value = false
  }
}
</script>
