<template>
  <div class="max-w-4xl mx-auto">
    <div class="mb-8">
      <h1 class="text-3xl font-bold text-gray-900">{{ $t('systemConfig.title') }}</h1>
      <p class="mt-2 text-sm text-gray-600">{{ $t('systemConfig.description') }}</p>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="flex justify-center py-12">
      <LoadingSpinner />
    </div>

    <!-- 配置表单 -->
    <div v-else class="bg-white rounded-lg shadow-md p-6">
      <form @submit.prevent="handleSubmit" class="space-y-6">
        <!-- 系统名称 -->
        <div>
          <label for="system_name" class="block text-sm font-medium text-gray-700 mb-2">
            {{ $t('systemConfig.systemName') }}
          </label>
          <input
            id="system_name"
            v-model="formData.system_name"
            type="text"
            required
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            :placeholder="$t('systemConfig.systemNamePlaceholder')"
          />
          <p class="mt-1 text-xs text-gray-500">{{ $t('systemConfig.systemNameHelp') }}</p>
        </div>

        <!-- Logo URL -->
        <div>
          <label for="system_logo" class="block text-sm font-medium text-gray-700 mb-2">
            {{ $t('systemConfig.systemLogo') }}
          </label>

          <!-- 文件上传区域 -->
          <div class="space-y-3">
            <!-- 隐藏的文件输入 -->
            <input
              ref="logoFileInput"
              type="file"
              accept="image/png,image/jpeg,image/jpg,image/svg+xml,image/gif,image/webp"
              class="hidden"
              @change="handleFileSelect"
            />

            <!-- 上传按钮 -->
            <div class="flex items-center space-x-3">
              <button
                type="button"
                @click="triggerFileSelect"
                :disabled="uploading"
                class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <span v-if="uploading">{{ $t('systemConfig.uploading') }}</span>
                <span v-else>{{ $t('systemConfig.uploadLogo') }}</span>
              </button>

              <button
                v-if="formData.system_logo"
                type="button"
                @click="clearLogo"
                :disabled="uploading"
                class="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {{ $t('systemConfig.clearLogo') }}
              </button>
            </div>

            <!-- URL 输入框（可选） -->
            <div>
              <label class="block text-xs text-gray-600 mb-1">
                {{ $t('systemConfig.orEnterUrl') }}
              </label>
              <input
                id="system_logo"
                v-model="formData.system_logo"
                type="url"
                class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                :placeholder="$t('systemConfig.systemLogoPlaceholder')"
              />
            </div>
          </div>

          <p class="mt-1 text-xs text-gray-500">{{ $t('systemConfig.systemLogoHelp') }}</p>

          <!-- Logo 预览 -->
          <div v-if="logoPreviewUrl" class="mt-3">
            <p class="text-sm text-gray-700 mb-2">{{ $t('systemConfig.logoPreview') }}</p>
            <img
              :src="logoPreviewUrl"
              alt="Logo Preview"
              class="h-16 object-contain border border-gray-200 rounded-lg p-2"
              @error="handleImageError"
            />
          </div>
        </div>

        <!-- GitHub Star 显示 -->
        <div>
          <label class="flex items-center">
            <input
              v-model="formData.show_github_star"
              type="checkbox"
              class="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
            />
            <span class="ml-2 text-sm font-medium text-gray-700">
              {{ $t('systemConfig.showGithubStar') }}
            </span>
          </label>
          <p class="mt-1 ml-6 text-xs text-gray-500">{{ $t('systemConfig.showGithubStarHelp') }}</p>
        </div>

        <!-- 允许用户注册 -->
        <div>
          <label class="flex items-center">
            <input
              v-model="formData.allow_registration"
              type="checkbox"
              class="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
            />
            <span class="ml-2 text-sm font-medium text-gray-700">
              {{ $t('systemConfig.allowRegistration') }}
            </span>
          </label>
          <p class="mt-1 ml-6 text-xs text-gray-500">{{ $t('systemConfig.allowRegistrationHelp') }}</p>
        </div>

        <!-- 注册邀请码 -->
        <div>
          <label for="registration_invite_code" class="block text-sm font-medium text-gray-700 mb-2">
            {{ $t('systemConfig.inviteCode') }}
          </label>
          <input
            id="registration_invite_code"
            v-model="formData.registration_invite_code"
            type="text"
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            :placeholder="$t('systemConfig.inviteCodePlaceholder')"
          />
          <p class="mt-1 text-xs text-gray-500">{{ $t('systemConfig.inviteCodeHelp') }}</p>
        </div>

        <!-- 按钮组 -->
        <div class="flex justify-end space-x-4 pt-4 border-t border-gray-200">
          <button
            type="button"
            @click="resetForm"
            class="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2"
            :disabled="saving"
          >
            {{ $t('systemConfig.reset') }}
          </button>
          <button
            type="submit"
            class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
            :disabled="saving"
          >
            <span v-if="saving">{{ $t('systemConfig.saving') }}</span>
            <span v-else>{{ $t('systemConfig.save') }}</span>
          </button>
        </div>
      </form>

      <!-- 当前配置预览 -->
      <div class="mt-8 pt-6 border-t border-gray-200">
        <h2 class="text-lg font-semibold text-gray-900 mb-4">{{ $t('systemConfig.currentConfig') }}</h2>
        <div class="bg-gray-50 rounded-lg p-4 space-y-2">
          <div class="flex justify-between">
            <span class="text-sm text-gray-600">{{ $t('systemConfig.systemName') }}:</span>
            <span class="text-sm font-medium text-gray-900">{{ originalConfig.system_name }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-sm text-gray-600">{{ $t('systemConfig.systemLogo') }}:</span>
            <span class="text-sm font-medium text-gray-900">
              {{ originalConfig.system_logo || $t('systemConfig.default') }}
            </span>
          </div>
          <div class="flex justify-between">
            <span class="text-sm text-gray-600">{{ $t('systemConfig.showGithubStar') }}:</span>
            <span class="text-sm font-medium text-gray-900">
              {{ originalConfig.show_github_star ? $t('common.yes') : $t('common.no') }}
            </span>
          </div>
          <div class="flex justify-between">
            <span class="text-sm text-gray-600">{{ $t('systemConfig.allowRegistration') }}:</span>
            <span class="text-sm font-medium text-gray-900">
              {{ originalConfig.allow_registration ? $t('common.yes') : $t('common.no') }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- 图片描述（多模态大模型）配置 -->
    <div v-if="!loading" class="mt-6 bg-white rounded-lg shadow-md p-6">
      <h2 class="text-lg font-semibold text-gray-900 mb-1">{{ $t('imageCaption.title') }}</h2>
      <p class="mb-6 text-sm text-gray-600">{{ $t('imageCaption.description') }}</p>

      <form @submit.prevent="handleImageCaptionSubmit" class="space-y-6">
        <!-- 启用开关 -->
        <div>
          <label class="flex items-center">
            <input
              v-model="imageCaptionForm.enabled"
              type="checkbox"
              class="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
            />
            <span class="ml-2 text-sm font-medium text-gray-700">
              {{ $t('imageCaption.enabled') }}
            </span>
          </label>
          <p class="mt-1 ml-6 text-xs text-gray-500">{{ $t('imageCaption.enabledHelp') }}</p>
        </div>

        <!-- API Base -->
        <div>
          <label for="image_caption_api_base" class="block text-sm font-medium text-gray-700 mb-2">
            {{ $t('imageCaption.apiBase') }}
          </label>
          <input
            id="image_caption_api_base"
            v-model="imageCaptionForm.api_base"
            type="text"
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            :placeholder="$t('imageCaption.apiBasePlaceholder')"
          />
        </div>

        <!-- API Key -->
        <div>
          <label for="image_caption_api_key" class="block text-sm font-medium text-gray-700 mb-2">
            {{ $t('imageCaption.apiKey') }}
          </label>
          <input
            id="image_caption_api_key"
            v-model="imageCaptionForm.api_key"
            type="password"
            autocomplete="new-password"
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            :placeholder="$t('imageCaption.apiKeyPlaceholder')"
          />
        </div>

        <!-- 模型名 -->
        <div>
          <label for="image_caption_model" class="block text-sm font-medium text-gray-700 mb-2">
            {{ $t('imageCaption.model') }}
          </label>
          <input
            id="image_caption_model"
            v-model="imageCaptionForm.model"
            type="text"
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            :placeholder="$t('imageCaption.modelPlaceholder')"
          />
        </div>

        <!-- Prompt -->
        <div>
          <label for="image_caption_prompt" class="block text-sm font-medium text-gray-700 mb-2">
            {{ $t('imageCaption.prompt') }}
          </label>
          <textarea
            id="image_caption_prompt"
            v-model="imageCaptionForm.prompt"
            rows="3"
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            :placeholder="$t('imageCaption.promptPlaceholder')"
          ></textarea>
        </div>

        <!-- 最大图片数 / 并发数 / 超时秒数 -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label for="image_caption_max_images" class="block text-sm font-medium text-gray-700 mb-2">
              {{ $t('imageCaption.maxImages') }}
            </label>
            <input
              id="image_caption_max_images"
              v-model.number="imageCaptionForm.max_images"
              type="number"
              min="1"
              class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <div>
            <label for="image_caption_concurrency" class="block text-sm font-medium text-gray-700 mb-2">
              {{ $t('imageCaption.concurrency') }}
            </label>
            <input
              id="image_caption_concurrency"
              v-model.number="imageCaptionForm.concurrency"
              type="number"
              min="1"
              class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <p class="mt-1 text-xs text-gray-500">{{ $t('imageCaption.concurrencyHelp') }}</p>
          </div>
          <div>
            <label for="image_caption_timeout" class="block text-sm font-medium text-gray-700 mb-2">
              {{ $t('imageCaption.timeout') }}
            </label>
            <input
              id="image_caption_timeout"
              v-model.number="imageCaptionForm.timeout"
              type="number"
              min="1"
              class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>

        <!-- 按钮组 -->
        <div class="flex justify-between pt-4 border-t border-gray-200">
          <button
            type="button"
            @click="handleTestImageCaption"
            :disabled="imageCaptionTesting || imageCaptionSaving"
            class="px-4 py-2 border border-blue-600 text-blue-600 rounded-lg hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span v-if="imageCaptionTesting">{{ $t('imageCaption.testing') }}</span>
            <span v-else>{{ $t('imageCaption.testConnection') }}</span>
          </button>
          <button
            type="submit"
            class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
            :disabled="imageCaptionSaving || imageCaptionTesting"
          >
            <span v-if="imageCaptionSaving">{{ $t('imageCaption.saving') }}</span>
            <span v-else>{{ $t('imageCaption.save') }}</span>
          </button>
        </div>
      </form>
    </div>

    <!-- Webhook 通知配置 -->
    <div v-if="!loading" class="mt-6 bg-white rounded-lg shadow-md p-6">
      <h2 class="text-lg font-semibold text-gray-900 mb-1">{{ $t('webhook.title') }}</h2>
      <p class="mb-6 text-sm text-gray-600">{{ $t('webhook.description') }}</p>

      <form @submit.prevent="handleWebhookSubmit" class="space-y-6">
        <!-- 启用开关 -->
        <div>
          <label class="flex items-center">
            <input
              v-model="webhookForm.enabled"
              type="checkbox"
              class="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
            />
            <span class="ml-2 text-sm font-medium text-gray-700">
              {{ $t('webhook.enabled') }}
            </span>
          </label>
          <p class="mt-1 ml-6 text-xs text-gray-500">{{ $t('webhook.enabledHelp') }}</p>
        </div>

        <!-- 回调地址 -->
        <div>
          <label for="webhook_url" class="block text-sm font-medium text-gray-700 mb-2">
            {{ $t('webhook.url') }}
          </label>
          <input
            id="webhook_url"
            v-model="webhookForm.url"
            type="text"
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            :placeholder="$t('webhook.urlPlaceholder')"
          />
        </div>

        <!-- 签名密钥 -->
        <div>
          <label for="webhook_secret" class="block text-sm font-medium text-gray-700 mb-2">
            {{ $t('webhook.secret') }}
          </label>
          <input
            id="webhook_secret"
            v-model="webhookForm.secret"
            type="password"
            autocomplete="new-password"
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            :placeholder="$t('webhook.secretPlaceholder')"
          />
        </div>

        <!-- 鉴权方式 -->
        <div>
          <label for="webhook_auth_type" class="block text-sm font-medium text-gray-700 mb-2">
            {{ $t('webhook.authType') }}
          </label>
          <select
            id="webhook_auth_type"
            v-model="webhookForm.auth_type"
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="none">{{ $t('webhook.authNone') }}</option>
            <option value="bearer">{{ $t('webhook.authBearer') }}</option>
            <option value="basic">{{ $t('webhook.authBasic') }}</option>
            <option value="api_key">{{ $t('webhook.authApiKey') }}</option>
          </select>
        </div>

        <!-- Bearer Token -->
        <div v-if="webhookForm.auth_type === 'bearer'">
          <label for="webhook_auth_token" class="block text-sm font-medium text-gray-700 mb-2">
            {{ $t('webhook.authToken') }}
          </label>
          <input
            id="webhook_auth_token"
            v-model="webhookForm.auth_token"
            type="password"
            autocomplete="new-password"
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            :placeholder="$t('webhook.authSecretPlaceholder')"
          />
        </div>

        <!-- HTTP Basic -->
        <div v-if="webhookForm.auth_type === 'basic'" class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label for="webhook_auth_username" class="block text-sm font-medium text-gray-700 mb-2">
              {{ $t('webhook.authUsername') }}
            </label>
            <input
              id="webhook_auth_username"
              v-model="webhookForm.auth_username"
              type="text"
              class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <div>
            <label for="webhook_auth_password" class="block text-sm font-medium text-gray-700 mb-2">
              {{ $t('webhook.authPassword') }}
            </label>
            <input
              id="webhook_auth_password"
              v-model="webhookForm.auth_password"
              type="password"
              autocomplete="new-password"
              class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              :placeholder="$t('webhook.authSecretPlaceholder')"
            />
          </div>
        </div>

        <!-- API Key 自定义头 -->
        <div v-if="webhookForm.auth_type === 'api_key'" class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label for="webhook_auth_header_name" class="block text-sm font-medium text-gray-700 mb-2">
              {{ $t('webhook.authHeaderName') }}
            </label>
            <input
              id="webhook_auth_header_name"
              v-model="webhookForm.auth_header_name"
              type="text"
              class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="X-API-Key"
            />
          </div>
          <div>
            <label for="webhook_auth_header_value" class="block text-sm font-medium text-gray-700 mb-2">
              {{ $t('webhook.authHeaderValue') }}
            </label>
            <input
              id="webhook_auth_header_value"
              v-model="webhookForm.auth_header_value"
              type="password"
              autocomplete="new-password"
              class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              :placeholder="$t('webhook.authSecretPlaceholder')"
            />
          </div>
        </div>

        <!-- 订阅事件 -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">{{ $t('webhook.events') }}</label>
          <label class="flex items-center mb-1">
            <input
              v-model="webhookForm.events"
              value="task.completed"
              type="checkbox"
              class="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
            />
            <span class="ml-2 text-sm text-gray-700">{{ $t('webhook.eventCompleted') }}</span>
          </label>
          <label class="flex items-center">
            <input
              v-model="webhookForm.events"
              value="task.failed"
              type="checkbox"
              class="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
            />
            <span class="ml-2 text-sm text-gray-700">{{ $t('webhook.eventFailed') }}</span>
          </label>
        </div>

        <!-- 超时 / 最大重试次数 -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label for="webhook_timeout" class="block text-sm font-medium text-gray-700 mb-2">
              {{ $t('webhook.timeout') }}
            </label>
            <input
              id="webhook_timeout"
              v-model.number="webhookForm.timeout"
              type="number"
              min="1"
              class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <div>
            <label for="webhook_max_attempts" class="block text-sm font-medium text-gray-700 mb-2">
              {{ $t('webhook.maxAttempts') }}
            </label>
            <input
              id="webhook_max_attempts"
              v-model.number="webhookForm.max_attempts"
              type="number"
              min="1"
              class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <p class="mt-1 text-xs text-gray-500">{{ $t('webhook.maxAttemptsHelp') }}</p>
          </div>
        </div>

        <!-- 按钮组 -->
        <div class="flex justify-between pt-4 border-t border-gray-200">
          <button
            type="button"
            @click="handleTestWebhook"
            :disabled="webhookTesting || webhookSaving"
            class="px-4 py-2 border border-blue-600 text-blue-600 rounded-lg hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span v-if="webhookTesting">{{ $t('webhook.testing') }}</span>
            <span v-else>{{ $t('webhook.testConnection') }}</span>
          </button>
          <button
            type="submit"
            class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
            :disabled="webhookSaving || webhookTesting"
          >
            <span v-if="webhookSaving">{{ $t('webhook.saving') }}</span>
            <span v-else>{{ $t('webhook.save') }}</span>
          </button>
        </div>
      </form>

      <!-- 最近投递记录 -->
      <div class="mt-8 pt-4 border-t border-gray-200">
        <div class="flex items-center justify-between mb-3">
          <h3 class="text-sm font-semibold text-gray-900">{{ $t('webhook.deliveriesTitle') }}</h3>
          <button
            type="button"
            @click="loadWebhookDeliveries"
            class="px-3 py-1 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2"
          >
            {{ $t('webhook.refresh') }}
          </button>
        </div>
        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">{{ $t('webhook.colTime') }}</th>
                <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">{{ $t('webhook.colEvent') }}</th>
                <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">{{ $t('webhook.colTask') }}</th>
                <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">{{ $t('webhook.colUrl') }}</th>
                <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">{{ $t('webhook.colStatus') }}</th>
                <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">{{ $t('webhook.colAttempts') }}</th>
                <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">{{ $t('webhook.colError') }}</th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              <tr v-if="webhookDeliveries.length === 0">
                <td colspan="7" class="px-4 py-8 text-center text-sm text-gray-500">
                  {{ $t('webhook.deliveriesEmpty') }}
                </td>
              </tr>
              <tr v-for="d in webhookDeliveries" :key="d.delivery_id">
                <td class="px-4 py-2 text-sm text-gray-600 whitespace-nowrap">{{ d.created_at }}</td>
                <td class="px-4 py-2 text-sm text-gray-900 whitespace-nowrap">{{ d.event }}</td>
                <td class="px-4 py-2 text-sm text-gray-600">{{ d.task_id ? d.task_id.slice(0, 8) : '-' }}</td>
                <td class="px-4 py-2 text-sm text-gray-600 max-w-xs truncate">{{ d.url }}</td>
                <td class="px-4 py-2 text-sm">
                  <span
                    class="px-2 py-0.5 rounded-full text-xs font-medium"
                    :class="webhookStatusClass(d.status)"
                  >
                    {{ formatWebhookStatus(d.status) }}
                  </span>
                </td>
                <td class="px-4 py-2 text-sm text-gray-600">{{ d.attempts }}</td>
                <td class="px-4 py-2 text-sm text-gray-600 max-w-xs truncate">{{ d.last_error || '-' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- 审计日志 -->
    <div v-if="!loading" class="mt-6 bg-white rounded-lg shadow-md p-6">
      <h2 class="text-lg font-semibold text-gray-900 mb-1">{{ $t('auditLog.title') }}</h2>
      <p class="mb-6 text-sm text-gray-600">{{ $t('auditLog.description') }}</p>

      <!-- 筛选条 -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('auditLog.filterAction') }}</label>
          <select
            v-model="auditFilters.action"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="">{{ $t('auditLog.all') }}</option>
            <option v-for="action in auditActionOptions" :key="action" :value="action">
              {{ $t(`auditLog.actions.${action}`) }}
            </option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('auditLog.filterResult') }}</label>
          <select
            v-model="auditFilters.result"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="">{{ $t('auditLog.all') }}</option>
            <option value="success">{{ $t('auditLog.success') }}</option>
            <option value="failure">{{ $t('auditLog.failure') }}</option>
            <option value="denied">{{ $t('auditLog.denied') }}</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('auditLog.filterStart') }}</label>
          <input
            v-model="auditFilters.start"
            type="date"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('auditLog.filterEnd') }}</label>
          <input
            v-model="auditFilters.end"
            type="date"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
      </div>
      <div class="flex justify-end space-x-3 mb-4">
        <button
          type="button"
          @click="resetAuditFilters"
          class="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2"
        >
          {{ $t('auditLog.reset') }}
        </button>
        <button
          type="button"
          @click="loadAuditLogs(1)"
          class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
        >
          {{ $t('auditLog.search') }}
        </button>
      </div>

      <!-- 日志表格 -->
      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">{{ $t('auditLog.colTime') }}</th>
              <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">{{ $t('auditLog.colUser') }}</th>
              <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">{{ $t('auditLog.colAction') }}</th>
              <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">{{ $t('auditLog.colResource') }}</th>
              <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">{{ $t('auditLog.colResult') }}</th>
              <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">{{ $t('auditLog.colIp') }}</th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            <tr v-if="auditLogs.length === 0">
              <td colspan="6" class="px-4 py-8 text-center text-sm text-gray-500">{{ $t('auditLog.empty') }}</td>
            </tr>
            <tr v-for="log in auditLogs" :key="log.id">
              <td class="px-4 py-2 text-sm text-gray-600 whitespace-nowrap">{{ log.created_at }}</td>
              <td class="px-4 py-2 text-sm text-gray-900">{{ log.username || $t('auditLog.anonymous') }}</td>
              <td class="px-4 py-2 text-sm text-gray-900">{{ formatAuditAction(log.action) }}</td>
              <td class="px-4 py-2 text-sm text-gray-600">{{ formatAuditResource(log) }}</td>
              <td class="px-4 py-2 text-sm">
                <span
                  class="px-2 py-0.5 rounded-full text-xs font-medium"
                  :class="auditResultClass(log.result)"
                >
                  {{ formatAuditResult(log.result) }}
                </span>
              </td>
              <td class="px-4 py-2 text-sm text-gray-600">{{ log.ip || '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 分页 -->
      <div class="flex items-center justify-between mt-4">
        <span class="text-sm text-gray-600">{{ $t('auditLog.total', { total: auditTotal }) }}</span>
        <div class="flex space-x-2">
          <button
            type="button"
            @click="loadAuditLogs(auditPage - 1)"
            :disabled="auditPage <= 1"
            class="px-3 py-1 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ $t('auditLog.prevPage') }}
          </button>
          <button
            type="button"
            @click="loadAuditLogs(auditPage + 1)"
            :disabled="auditPage * auditPageSize >= auditTotal"
            class="px-3 py-1 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ $t('auditLog.nextPage') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  getSystemConfig,
  updateSystemConfig,
  uploadSystemLogo,
  getImageCaptionConfig,
  testImageCaptionConnection,
  getWebhookConfig,
  testWebhookConnection,
  getWebhookDeliveries,
  getAuditLogs,
  type SystemConfig,
  type SystemConfigUpdateRequest,
  type ImageCaptionConfig,
  type WebhookConfig,
  type WebhookDeliveryItem,
  type AuditLogItem,
  type AuditLogQuery,
} from '@/api'
import { toast } from '@/utils/toast'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const { t } = useI18n()

const loading = ref(true)
const saving = ref(false)
const uploading = ref(false)

// 原始配置（从服务器加载）
const originalConfig = ref<SystemConfig>({
  system_name: 'MinerU Tianshu',
  system_logo: '',
  show_github_star: true,
  allow_registration: true,
  registration_invite_code: '',
})

// 表单数据
const formData = ref<SystemConfig>({
  system_name: 'MinerU Tianshu',
  system_logo: '',
  show_github_star: true,
  allow_registration: true,
  registration_invite_code: '',
})

// Logo 上传相关
const logoFileInput = ref<HTMLInputElement | null>(null)
const logoPreviewUrl = ref<string>('')

// 图片描述（多模态大模型）配置
const imageCaptionSaving = ref(false)
const imageCaptionTesting = ref(false)

const imageCaptionOriginal = ref<ImageCaptionConfig>({
  enabled: false,
  api_base: '',
  api_key: '',
  model: '',
  prompt: '',
  max_images: 20,
  concurrency: 4,
  timeout: 60,
})

const imageCaptionForm = ref<ImageCaptionConfig>({ ...imageCaptionOriginal.value })

/**
 * 加载图片描述配置
 */
async function loadImageCaptionConfig() {
  try {
    const response = await getImageCaptionConfig()
    imageCaptionOriginal.value = { ...response.config }
    imageCaptionForm.value = { ...response.config }
  } catch (error: any) {
    console.error('Failed to load image caption config:', error)
    toast.error(t('imageCaption.loadError'))
  }
}

/**
 * 保存图片描述配置（只提交变更过的字段；api_key 保持掩码值时不提交）
 */
async function handleImageCaptionSubmit() {
  try {
    imageCaptionSaving.value = true

    const form = imageCaptionForm.value
    const original = imageCaptionOriginal.value
    const updates: SystemConfigUpdateRequest = {}
    if (form.enabled !== original.enabled) {
      updates.image_caption_enabled = form.enabled
    }
    if (form.api_base !== original.api_base) {
      updates.image_caption_api_base = form.api_base
    }
    if (form.api_key !== original.api_key) {
      updates.image_caption_api_key = form.api_key
    }
    if (form.model !== original.model) {
      updates.image_caption_model = form.model
    }
    if (form.prompt !== original.prompt) {
      updates.image_caption_prompt = form.prompt
    }
    if (form.max_images !== original.max_images) {
      updates.image_caption_max_images = form.max_images
    }
    if (form.concurrency !== original.concurrency) {
      updates.image_caption_concurrency = form.concurrency
    }
    if (form.timeout !== original.timeout) {
      updates.image_caption_timeout = form.timeout
    }

    if (Object.keys(updates).length === 0) {
      toast.success(t('imageCaption.noChanges'))
      return
    }

    await updateSystemConfig(updates)
    imageCaptionOriginal.value = { ...form }

    toast.success(t('imageCaption.saveSuccess'))
  } catch (error: any) {
    console.error('Failed to update image caption config:', error)
    toast.error(error.response?.data?.detail || t('imageCaption.saveError'))
  } finally {
    imageCaptionSaving.value = false
  }
}

/**
 * 测试图片描述模型连接（使用表单中未保存的值）
 */
async function handleTestImageCaption() {
  try {
    imageCaptionTesting.value = true

    const result = await testImageCaptionConnection({
      api_base: imageCaptionForm.value.api_base,
      api_key: imageCaptionForm.value.api_key,
      model: imageCaptionForm.value.model,
      timeout: imageCaptionForm.value.timeout,
    })

    if (result.success) {
      toast.success(result.message || t('imageCaption.testSuccess', { latency: result.latency_ms }))
    } else {
      toast.error(result.message || t('imageCaption.testFailed'))
    }
  } catch (error: any) {
    console.error('Failed to test image caption connection:', error)
    toast.error(error.response?.data?.detail || t('imageCaption.testError'))
  } finally {
    imageCaptionTesting.value = false
  }
}

/**
 * 加载系统配置
 */
async function loadConfig() {
  try {
    loading.value = true
    const response = await getSystemConfig()
    originalConfig.value = { ...response.config }
    formData.value = { ...response.config }
    logoPreviewUrl.value = response.config.system_logo
  } catch (error: any) {
    console.error('Failed to load system config:', error)
    toast.error(t('systemConfig.loadError'))
  } finally {
    loading.value = false
  }
}

/**
 * 触发文件选择
 */
function triggerFileSelect() {
  logoFileInput.value?.click()
}

/**
 * 处理文件选择
 */
async function handleFileSelect(event: Event) {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]

  if (!file) return

  // 验证文件类型
  const allowedTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/svg+xml', 'image/gif', 'image/webp']
  if (!allowedTypes.includes(file.type)) {
    toast.error(t('systemConfig.invalidFileType'))
    return
  }

  // 验证文件大小 (5MB)
  if (file.size > 5 * 1024 * 1024) {
    toast.error(t('systemConfig.fileTooLarge'))
    return
  }

  try {
    uploading.value = true

    // 上传文件到服务器
    const response = await uploadSystemLogo(file)

    // 更新表单数据和预览
    formData.value.system_logo = response.logo_url
    logoPreviewUrl.value = response.logo_url

    toast.success(t('systemConfig.uploadSuccess'))
  } catch (error: any) {
    console.error('Failed to upload logo:', error)
    toast.error(error.response?.data?.detail || t('systemConfig.uploadError'))
  } finally {
    uploading.value = false
    // 清空 input，允许重新选择相同文件
    if (target) {
      target.value = ''
    }
  }
}

/**
 * 清除 Logo
 */
function clearLogo() {
  formData.value.system_logo = ''
  logoPreviewUrl.value = ''
  if (logoFileInput.value) {
    logoFileInput.value.value = ''
  }
}

/**
 * 提交表单
 */
async function handleSubmit() {
  try {
    saving.value = true

    // 只提交有变化的字段
    const updates: Partial<SystemConfig> = {}
    if (formData.value.system_name !== originalConfig.value.system_name) {
      updates.system_name = formData.value.system_name
    }
    if (formData.value.system_logo !== originalConfig.value.system_logo) {
      updates.system_logo = formData.value.system_logo
    }
    if (formData.value.show_github_star !== originalConfig.value.show_github_star) {
      updates.show_github_star = formData.value.show_github_star
    }
    if (formData.value.allow_registration !== originalConfig.value.allow_registration) {
      updates.allow_registration = formData.value.allow_registration
    }
    // 邀请码为掩码值时表示未修改，不提交；清空则提交空字符串以移除邀请码
    if (
      formData.value.registration_invite_code !== originalConfig.value.registration_invite_code &&
      formData.value.registration_invite_code !== '********'
    ) {
      updates.registration_invite_code = formData.value.registration_invite_code ?? ''
    }

    if (Object.keys(updates).length === 0) {
      toast.success(t('systemConfig.noChanges'))
      return
    }

    const response = await updateSystemConfig(updates)
    originalConfig.value = { ...response.config }
    formData.value = { ...response.config }
    logoPreviewUrl.value = response.config.system_logo

    toast.success(t('systemConfig.saveSuccess'))

    // 刷新页面以应用新配置（特别是系统名称和 Logo）
    setTimeout(() => {
      window.location.reload()
    }, 1500)
  } catch (error: any) {
    console.error('Failed to update system config:', error)
    toast.error(error.response?.data?.detail || t('systemConfig.saveError'))
  } finally {
    saving.value = false
  }
}

/**
 * 重置表单
 */
function resetForm() {
  formData.value = { ...originalConfig.value }
  logoPreviewUrl.value = originalConfig.value.system_logo
}

/**
 * 处理图片加载错误
 */
function handleImageError(event: Event) {
  const target = event.target as HTMLImageElement
  target.style.display = 'none'
  toast.error(t('systemConfig.logoLoadError'))
}

// ==================== 审计日志 ====================

// 与后端埋点动作保持一致，用于筛选下拉
const auditActionOptions = [
  'auth.login',
  'auth.login_failed',
  'auth.logout',
  'auth.register',
  'auth.change_password',
  'api_key.create',
  'api_key.delete',
  'config.update',
  'task.delete',
  'task.clear_failed',
  'task.clear_cache',
  'admin.cleanup',
  'admin.reset_stale',
]

const auditLogs = ref<AuditLogItem[]>([])
const auditTotal = ref(0)
const auditPage = ref(1)
const auditPageSize = 50

const auditFilters = ref({
  action: '',
  result: '',
  start: '',
  end: '',
})

/**
 * 加载审计日志
 */
async function loadAuditLogs(page: number) {
  try {
    const query: AuditLogQuery = { page, page_size: auditPageSize }
    if (auditFilters.value.action) query.action = auditFilters.value.action
    if (auditFilters.value.result) query.result = auditFilters.value.result
    // 后端按 datetime('now') 的 UTC 字符串比较，日期补全天界
    if (auditFilters.value.start) query.start = `${auditFilters.value.start} 00:00:00`
    if (auditFilters.value.end) query.end = `${auditFilters.value.end} 23:59:59`

    const response = await getAuditLogs(query)
    auditLogs.value = response.data.items
    auditTotal.value = response.data.total
    auditPage.value = response.data.page
  } catch (error: any) {
    console.error('Failed to load audit logs:', error)
    toast.error(t('auditLog.loadError'))
  }
}

/**
 * 重置筛选条件并重新加载
 */
function resetAuditFilters() {
  auditFilters.value = { action: '', result: '', start: '', end: '' }
  loadAuditLogs(1)
}

/**
 * 动作标识翻译，未知动作原样展示
 */
function formatAuditAction(action: string): string {
  const key = `auditLog.actions.${action}`
  const translated = t(key)
  return translated === key ? action : translated
}

/**
 * 资源列展示：类型 + ID
 */
function formatAuditResource(log: AuditLogItem): string {
  if (!log.resource_type) return '-'
  return log.resource_id ? `${log.resource_type}: ${log.resource_id}` : log.resource_type
}

function formatAuditResult(result: string): string {
  if (result === 'success') return t('auditLog.success')
  if (result === 'failure') return t('auditLog.failure')
  if (result === 'denied') return t('auditLog.denied')
  return result
}

function auditResultClass(result: string): string {
  if (result === 'success') return 'bg-green-100 text-green-800'
  if (result === 'failure') return 'bg-red-100 text-red-800'
  return 'bg-yellow-100 text-yellow-800'
}

// ==================== Webhook 通知 ====================

const webhookSaving = ref(false)
const webhookTesting = ref(false)

const webhookOriginal = ref<WebhookConfig>({
  enabled: false,
  url: '',
  secret: '',
  events: ['task.completed', 'task.failed'],
  timeout: 10,
  max_attempts: 8,
  auth_type: 'none',
  auth_token: '',
  auth_username: '',
  auth_password: '',
  auth_header_name: 'X-API-Key',
  auth_header_value: '',
})

const webhookForm = ref<WebhookConfig>({ ...webhookOriginal.value })

const webhookDeliveries = ref<WebhookDeliveryItem[]>([])

/**
 * 加载 Webhook 配置
 */
async function loadWebhookConfig() {
  try {
    const response = await getWebhookConfig()
    webhookOriginal.value = { ...response.config }
    webhookForm.value = { ...response.config }
  } catch (error: any) {
    console.error('Failed to load webhook config:', error)
    toast.error(t('webhook.loadError'))
  }
}

/**
 * 保存 Webhook 配置（只提交变更过的字段；secret 保持掩码值时不提交）
 */
async function handleWebhookSubmit() {
  try {
    webhookSaving.value = true

    const form = webhookForm.value
    const original = webhookOriginal.value
    const updates: SystemConfigUpdateRequest = {}
    if (form.enabled !== original.enabled) {
      updates.webhook_enabled = form.enabled
    }
    if (form.url !== original.url) {
      updates.webhook_url = form.url
    }
    if (form.secret !== original.secret) {
      updates.webhook_secret = form.secret
    }
    if (form.events.join(',') !== original.events.join(',')) {
      updates.webhook_events = form.events.join(',')
    }
    if (form.timeout !== original.timeout) {
      updates.webhook_timeout = form.timeout
    }
    if (form.max_attempts !== original.max_attempts) {
      updates.webhook_max_attempts = form.max_attempts
    }
    if (form.auth_type !== original.auth_type) {
      updates.webhook_auth_type = form.auth_type
    }
    // 敏感字段保持掩码值时不提交（后端同样跳过掩码占位符）
    if (form.auth_token !== original.auth_token && form.auth_token !== '********') {
      updates.webhook_auth_token = form.auth_token
    }
    if (form.auth_username !== original.auth_username) {
      updates.webhook_auth_username = form.auth_username
    }
    if (form.auth_password !== original.auth_password && form.auth_password !== '********') {
      updates.webhook_auth_password = form.auth_password
    }
    if (form.auth_header_name !== original.auth_header_name) {
      updates.webhook_auth_header_name = form.auth_header_name
    }
    if (form.auth_header_value !== original.auth_header_value && form.auth_header_value !== '********') {
      updates.webhook_auth_header_value = form.auth_header_value
    }

    if (Object.keys(updates).length === 0) {
      toast.success(t('webhook.noChanges'))
      return
    }

    await updateSystemConfig(updates)
    webhookOriginal.value = { ...form }

    toast.success(t('webhook.saveSuccess'))
  } catch (error: any) {
    console.error('Failed to update webhook config:', error)
    toast.error(error.response?.data?.detail || t('webhook.saveError'))
  } finally {
    webhookSaving.value = false
  }
}

/**
 * 测试 Webhook 投递（使用已保存的配置，先保存表单再测）
 */
async function handleTestWebhook() {
  try {
    webhookTesting.value = true

    const result = await testWebhookConnection()

    if (result.success) {
      toast.success(t('webhook.testSuccess', { code: result.status_code }))
    } else {
      toast.error(result.error || `${t('webhook.testFailed')} (HTTP ${result.status_code ?? '-'})`)
    }
  } catch (error: any) {
    console.error('Failed to test webhook connection:', error)
    toast.error(error.response?.data?.detail || t('webhook.testError'))
  } finally {
    webhookTesting.value = false
  }
}

/**
 * 加载最近 20 条投递记录
 */
async function loadWebhookDeliveries() {
  try {
    const response = await getWebhookDeliveries({ page: 1, page_size: 20 })
    webhookDeliveries.value = response.data.items
  } catch (error: any) {
    console.error('Failed to load webhook deliveries:', error)
    toast.error(t('webhook.deliveriesLoadError'))
  }
}

function formatWebhookStatus(status: string): string {
  const map: Record<string, string> = {
    delivered: t('webhook.statusDelivered'),
    pending: t('webhook.statusPending'),
    failed: t('webhook.statusFailed'),
    dead: t('webhook.statusDead'),
  }
  return map[status] || status
}

function webhookStatusClass(status: string): string {
  if (status === 'delivered') return 'bg-green-100 text-green-800'
  if (status === 'dead' || status === 'failed') return 'bg-red-100 text-red-800'
  return 'bg-yellow-100 text-yellow-800'
}

onMounted(() => {
  loadConfig()
  loadImageCaptionConfig()
  loadWebhookConfig()
  loadWebhookDeliveries()
  loadAuditLogs(1)
})
</script>
