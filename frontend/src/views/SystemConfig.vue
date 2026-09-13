<template>
  <div class="w-full">
    <PageHeader :title="$t('systemConfig.title')" :description="$t('systemConfig.description')" />

    <!-- 加载骨架屏 -->
    <div v-if="loading" class="flex flex-col lg:flex-row lg:items-start gap-6">
      <div class="hidden lg:block w-60 shrink-0">
        <div class="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-3 space-y-2 animate-pulse">
          <div v-for="i in 4" :key="i" class="h-10 bg-gray-100 rounded-lg"></div>
        </div>
      </div>
      <div class="flex-1 min-w-0 space-y-6">
        <div class="bg-white rounded-2xl border border-gray-200/80 shadow-sm px-6 sm:px-8 py-6 animate-pulse">
          <div class="h-5 w-40 bg-gray-200 rounded mb-2"></div>
          <div class="h-4 w-64 bg-gray-100 rounded mb-6"></div>
          <div v-for="i in 4" :key="i" class="flex items-center justify-between py-5 border-t border-gray-100">
            <div class="space-y-2">
              <div class="h-4 w-32 bg-gray-200 rounded"></div>
              <div class="h-3 w-52 bg-gray-100 rounded"></div>
            </div>
            <div class="h-10 w-72 bg-gray-100 rounded-xl"></div>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="flex flex-col lg:flex-row lg:items-start gap-6">
      <!-- 左侧导航（窄屏时为顶部横向滚动标签条） -->
      <aside class="w-full lg:w-60 lg:shrink-0 lg:sticky lg:top-6">
        <nav class="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-2">
          <p class="hidden lg:block px-3 pt-2 pb-1 text-xs font-semibold text-gray-400 uppercase tracking-wider">
            {{ $t('systemConfig.navTitle') }}
          </p>
          <div class="flex lg:flex-col gap-1 overflow-x-auto lg:overflow-visible scrollbar-hide">
            <button
              v-for="item in navItems"
              :key="item.key"
              type="button"
              @click="activeTab = item.key"
              class="relative flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm whitespace-nowrap transition-colors duration-200 focus:outline-none"
              :class="
                activeTab === item.key
                  ? 'bg-primary-50 text-primary-700 font-semibold'
                  : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
              "
            >
              <span
                v-if="activeTab === item.key"
                class="hidden lg:block absolute left-0 top-1/2 -translate-y-1/2 h-5 w-[3px] rounded-full bg-primary-600"
              />
              <component :is="item.icon" class="w-4 h-4 shrink-0" />
              <span>{{ $t(item.labelKey) }}</span>
            </button>
          </div>
        </nav>
      </aside>

      <!-- 右侧内容区 -->
      <div class="flex-1 min-w-0 w-full">
        <!-- 基础设置 -->
        <div v-show="activeTab === 'basic'" class="space-y-6">
          <section class="bg-white rounded-2xl border border-gray-200/80 shadow-sm">
            <header class="px-6 sm:px-8 py-5 border-b border-gray-100">
              <h2 class="text-lg font-semibold text-gray-900">{{ $t('systemConfig.nav.basic') }}</h2>
              <p class="mt-1 text-sm text-gray-500">{{ $t('systemConfig.nav.basicDesc') }}</p>
            </header>

            <form @submit.prevent="handleSubmit">
              <div class="px-6 sm:px-8 divide-y divide-gray-100">
                <!-- 系统名称 -->
                <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 sm:gap-8 py-5">
                  <div class="min-w-0">
                    <label for="system_name" class="block text-sm font-medium text-gray-900">
                      {{ $t('systemConfig.systemName') }}
                    </label>
                    <p class="mt-1 text-sm text-gray-500">{{ $t('systemConfig.systemNameHelp') }}</p>
                  </div>
                  <input
                    id="system_name"
                    v-model="formData.system_name"
                    type="text"
                    required
                    class="w-full sm:w-72 shrink-0 px-4 py-2"
                    :placeholder="$t('systemConfig.systemNamePlaceholder')"
                  />
                </div>

                <!-- 系统 Logo（全宽变体） -->
                <div class="py-5">
                  <label for="system_logo" class="block text-sm font-medium text-gray-900">
                    {{ $t('systemConfig.systemLogo') }}
                  </label>
                  <p class="mt-1 text-sm text-gray-500">{{ $t('systemConfig.systemLogoHelp') }}</p>

                  <div class="mt-4 space-y-3">
                    <!-- 隐藏的文件输入 -->
                    <input
                      ref="logoFileInput"
                      type="file"
                      accept="image/png,image/jpeg,image/jpg,image/svg+xml,image/gif,image/webp"
                      class="hidden"
                      @change="handleFileSelect"
                    />

                    <div class="flex flex-wrap items-center gap-3">
                      <button
                        type="button"
                        @click="triggerFileSelect"
                        :disabled="uploading"
                        class="btn btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <span v-if="uploading">{{ $t('systemConfig.uploading') }}</span>
                        <span v-else>{{ $t('systemConfig.uploadLogo') }}</span>
                      </button>

                      <button
                        v-if="formData.system_logo"
                        type="button"
                        @click="clearLogo"
                        :disabled="uploading"
                        class="btn btn-secondary disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {{ $t('systemConfig.clearLogo') }}
                      </button>
                    </div>

                    <div>
                      <label class="block text-xs text-gray-500 mb-1">
                        {{ $t('systemConfig.orEnterUrl') }}
                      </label>
                      <input
                        id="system_logo"
                        v-model="formData.system_logo"
                        type="url"
                        class="w-full sm:max-w-md px-4 py-2"
                        :placeholder="$t('systemConfig.systemLogoPlaceholder')"
                      />
                    </div>

                    <!-- Logo 预览 -->
                    <div v-if="logoPreviewUrl">
                      <p class="text-sm text-gray-700 mb-2">{{ $t('systemConfig.logoPreview') }}</p>
                      <img
                        :src="logoPreviewUrl"
                        alt="Logo Preview"
                        class="h-16 object-contain border border-gray-200 rounded-lg p-2"
                        @error="handleImageError"
                      />
                    </div>
                  </div>
                </div>

                <!-- GitHub Star 显示 -->
                <div class="flex items-center justify-between gap-8 py-5">
                  <div class="min-w-0">
                    <p class="text-sm font-medium text-gray-900">{{ $t('systemConfig.showGithubStar') }}</p>
                    <p class="mt-1 text-sm text-gray-500">{{ $t('systemConfig.showGithubStarHelp') }}</p>
                  </div>
                  <FormToggle v-model="formData.show_github_star" />
                </div>

                <!-- 允许用户注册 -->
                <div class="flex items-center justify-between gap-8 py-5">
                  <div class="min-w-0">
                    <p class="text-sm font-medium text-gray-900">{{ $t('systemConfig.allowRegistration') }}</p>
                    <p class="mt-1 text-sm text-gray-500">{{ $t('systemConfig.allowRegistrationHelp') }}</p>
                  </div>
                  <FormToggle v-model="formData.allow_registration" />
                </div>

                <!-- 注册邀请码 -->
                <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 sm:gap-8 py-5">
                  <div class="min-w-0">
                    <label for="registration_invite_code" class="block text-sm font-medium text-gray-900">
                      {{ $t('systemConfig.inviteCode') }}
                    </label>
                    <p class="mt-1 text-sm text-gray-500">{{ $t('systemConfig.inviteCodeHelp') }}</p>
                  </div>
                  <input
                    id="registration_invite_code"
                    v-model="formData.registration_invite_code"
                    type="text"
                    class="w-full sm:w-72 shrink-0 px-4 py-2"
                    :placeholder="$t('systemConfig.inviteCodePlaceholder')"
                  />
                </div>
              </div>
            </form>
          </section>

          <!-- 当前配置预览 -->
          <section class="bg-white rounded-2xl border border-gray-200/80 shadow-sm">
            <header class="px-6 sm:px-8 py-5 border-b border-gray-100">
              <h2 class="text-lg font-semibold text-gray-900">{{ $t('systemConfig.currentConfig') }}</h2>
            </header>
            <div class="px-6 sm:px-8 py-5">
              <div class="bg-gray-50 rounded-xl p-4 space-y-2">
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
          </section>

          <!-- 粘性保存栏 -->
          <Transition
            enter-active-class="transition-all duration-200 ease-out"
            enter-from-class="opacity-0 translate-y-3"
            leave-active-class="transition-all duration-150 ease-in"
            leave-to-class="opacity-0 translate-y-3"
          >
            <div
              v-if="basicDirty"
              class="sticky bottom-4 z-20 flex items-center justify-between gap-4 rounded-xl bg-white/90 backdrop-blur border border-gray-200 shadow-lg px-4 py-3"
            >
              <p class="text-sm text-gray-600 flex items-center gap-2 min-w-0">
                <span class="w-2 h-2 rounded-full bg-amber-500 shrink-0"></span>
                {{ $t('systemConfig.unsavedChanges') }}
              </p>
              <div class="flex items-center gap-3 shrink-0">
                <button type="button" @click="resetForm" :disabled="saving" class="btn btn-secondary !px-4 !py-1.5 text-sm">
                  {{ $t('systemConfig.reset') }}
                </button>
                <button
                  type="button"
                  @click="handleSubmit"
                  :disabled="saving"
                  class="btn btn-primary !px-4 !py-1.5 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <span v-if="saving">{{ $t('systemConfig.saving') }}</span>
                  <span v-else>{{ $t('systemConfig.saveChanges') }}</span>
                </button>
              </div>
            </div>
          </Transition>
        </div>

        <!-- 图片描述（多模态大模型）配置 -->
        <div v-show="activeTab === 'imageCaption'" class="space-y-6">
          <section class="bg-white rounded-2xl border border-gray-200/80 shadow-sm">
            <header class="px-6 sm:px-8 py-5 border-b border-gray-100 flex items-start justify-between gap-4">
              <div class="min-w-0">
                <h2 class="text-lg font-semibold text-gray-900">{{ $t('imageCaption.title') }}</h2>
                <p class="mt-1 text-sm text-gray-500">{{ $t('imageCaption.description') }}</p>
              </div>
              <span
                class="badge shrink-0"
                :class="imageCaptionOriginal.enabled ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'"
              >
                <span
                  class="w-1.5 h-1.5 rounded-full mr-1.5"
                  :class="imageCaptionOriginal.enabled ? 'bg-green-500' : 'bg-gray-400'"
                ></span>
                {{ imageCaptionOriginal.enabled ? $t('common.enabled') : $t('common.disabled') }}
              </span>
            </header>

            <form @submit.prevent="handleImageCaptionSubmit">
              <div class="px-6 sm:px-8 divide-y divide-gray-100">
                <!-- 启用开关 -->
                <div class="flex items-center justify-between gap-8 py-5">
                  <div class="min-w-0">
                    <p class="text-sm font-medium text-gray-900">{{ $t('imageCaption.enabled') }}</p>
                    <p class="mt-1 text-sm text-gray-500">{{ $t('imageCaption.enabledHelp') }}</p>
                  </div>
                  <FormToggle v-model="imageCaptionForm.enabled" />
                </div>

                <!-- API Base -->
                <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 sm:gap-8 py-5">
                  <div class="min-w-0">
                    <label for="image_caption_api_base" class="block text-sm font-medium text-gray-900">
                      {{ $t('imageCaption.apiBase') }}
                    </label>
                    <p class="mt-1 text-sm text-gray-500">{{ $t('imageCaption.apiBaseHelp') }}</p>
                  </div>
                  <input
                    id="image_caption_api_base"
                    v-model="imageCaptionForm.api_base"
                    type="text"
                    class="w-full sm:w-72 shrink-0 px-4 py-2"
                    :placeholder="$t('imageCaption.apiBasePlaceholder')"
                  />
                </div>

                <!-- API Key -->
                <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 sm:gap-8 py-5">
                  <div class="min-w-0">
                    <label for="image_caption_api_key" class="block text-sm font-medium text-gray-900">
                      {{ $t('imageCaption.apiKey') }}
                    </label>
                    <p class="mt-1 text-sm text-gray-500">{{ $t('imageCaption.apiKeyHelp') }}</p>
                  </div>
                  <input
                    id="image_caption_api_key"
                    v-model="imageCaptionForm.api_key"
                    type="password"
                    autocomplete="new-password"
                    class="w-full sm:w-72 shrink-0 px-4 py-2"
                    :placeholder="
                      imageCaptionOriginal.api_key === '********'
                        ? $t('imageCaption.apiKeyPlaceholder')
                        : $t('imageCaption.apiKeyNotSet')
                    "
                  />
                </div>

                <!-- 模型名 -->
                <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 sm:gap-8 py-5">
                  <div class="min-w-0">
                    <label for="image_caption_model" class="block text-sm font-medium text-gray-900">
                      {{ $t('imageCaption.model') }}
                    </label>
                    <p class="mt-1 text-sm text-gray-500">{{ $t('imageCaption.modelHelp') }}</p>
                  </div>
                  <input
                    id="image_caption_model"
                    v-model="imageCaptionForm.model"
                    type="text"
                    class="w-full sm:w-72 shrink-0 px-4 py-2"
                    :placeholder="$t('imageCaption.modelPlaceholder')"
                  />
                </div>

                <!-- Prompt（全宽变体） -->
                <div class="py-5">
                  <label for="image_caption_prompt" class="block text-sm font-medium text-gray-900">
                    {{ $t('imageCaption.prompt') }}
                  </label>
                  <p class="mt-1 text-sm text-gray-500">{{ $t('imageCaption.promptHelp') }}</p>
                  <textarea
                    id="image_caption_prompt"
                    v-model="imageCaptionForm.prompt"
                    rows="3"
                    class="mt-3 w-full max-w-3xl px-4 py-2"
                    :placeholder="$t('imageCaption.promptPlaceholder')"
                  ></textarea>
                </div>

                <!-- 最大图片数 -->
                <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 sm:gap-8 py-5">
                  <div class="min-w-0">
                    <label for="image_caption_max_images" class="block text-sm font-medium text-gray-900">
                      {{ $t('imageCaption.maxImages') }}
                    </label>
                    <p class="mt-1 text-sm text-gray-500">{{ $t('imageCaption.maxImagesHelp') }}</p>
                  </div>
                  <input
                    id="image_caption_max_images"
                    v-model.number="imageCaptionForm.max_images"
                    type="number"
                    min="1"
                    class="w-full sm:w-28 shrink-0 px-4 py-2"
                  />
                </div>

                <!-- 并发数 -->
                <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 sm:gap-8 py-5">
                  <div class="min-w-0">
                    <label for="image_caption_concurrency" class="block text-sm font-medium text-gray-900">
                      {{ $t('imageCaption.concurrency') }}
                    </label>
                    <p class="mt-1 text-sm text-gray-500">{{ $t('imageCaption.concurrencyHelp') }}</p>
                  </div>
                  <input
                    id="image_caption_concurrency"
                    v-model.number="imageCaptionForm.concurrency"
                    type="number"
                    min="1"
                    class="w-full sm:w-28 shrink-0 px-4 py-2"
                  />
                </div>

                <!-- 超时秒数 -->
                <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 sm:gap-8 py-5">
                  <div class="min-w-0">
                    <label for="image_caption_timeout" class="block text-sm font-medium text-gray-900">
                      {{ $t('imageCaption.timeout') }}
                    </label>
                    <p class="mt-1 text-sm text-gray-500">{{ $t('imageCaption.timeoutHelp') }}</p>
                  </div>
                  <input
                    id="image_caption_timeout"
                    v-model.number="imageCaptionForm.timeout"
                    type="number"
                    min="1"
                    class="w-full sm:w-28 shrink-0 px-4 py-2"
                  />
                </div>

                <!-- 测试连接 -->
                <div class="flex items-center justify-between gap-8 py-5">
                  <div class="min-w-0">
                    <p class="text-sm font-medium text-gray-900">{{ $t('imageCaption.testConnection') }}</p>
                    <p class="mt-1 text-sm text-gray-500">{{ $t('imageCaption.testHelp') }}</p>
                  </div>
                  <button
                    type="button"
                    @click="handleTestImageCaption"
                    :disabled="imageCaptionTesting || imageCaptionSaving"
                    class="btn btn-secondary !px-4 !py-1.5 text-sm shrink-0 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <span v-if="imageCaptionTesting">{{ $t('imageCaption.testing') }}</span>
                    <span v-else>{{ $t('imageCaption.testConnection') }}</span>
                  </button>
                </div>
              </div>
            </form>
          </section>

          <!-- 粘性保存栏 -->
          <Transition
            enter-active-class="transition-all duration-200 ease-out"
            enter-from-class="opacity-0 translate-y-3"
            leave-active-class="transition-all duration-150 ease-in"
            leave-to-class="opacity-0 translate-y-3"
          >
            <div
              v-if="imageCaptionDirty"
              class="sticky bottom-4 z-20 flex items-center justify-between gap-4 rounded-xl bg-white/90 backdrop-blur border border-gray-200 shadow-lg px-4 py-3"
            >
              <p class="text-sm text-gray-600 flex items-center gap-2 min-w-0">
                <span class="w-2 h-2 rounded-full bg-amber-500 shrink-0"></span>
                {{ $t('systemConfig.unsavedChanges') }}
              </p>
              <div class="flex items-center gap-3 shrink-0">
                <button
                  type="button"
                  @click="resetImageCaptionForm"
                  :disabled="imageCaptionSaving"
                  class="btn btn-secondary !px-4 !py-1.5 text-sm"
                >
                  {{ $t('systemConfig.reset') }}
                </button>
                <button
                  type="button"
                  @click="handleImageCaptionSubmit"
                  :disabled="imageCaptionSaving || imageCaptionTesting"
                  class="btn btn-primary !px-4 !py-1.5 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <span v-if="imageCaptionSaving">{{ $t('imageCaption.saving') }}</span>
                  <span v-else>{{ $t('systemConfig.saveChanges') }}</span>
                </button>
              </div>
            </div>
          </Transition>
        </div>

        <!-- Webhook 通知配置 -->
        <div v-show="activeTab === 'webhook'" class="space-y-6">
          <section class="bg-white rounded-2xl border border-gray-200/80 shadow-sm">
            <header class="px-6 sm:px-8 py-5 border-b border-gray-100">
              <h2 class="text-lg font-semibold text-gray-900">{{ $t('webhook.title') }}</h2>
              <p class="mt-1 text-sm text-gray-500">{{ $t('webhook.description') }}</p>
            </header>

            <form @submit.prevent="handleWebhookSubmit">
              <div class="px-6 sm:px-8 divide-y divide-gray-100">
                <!-- 超时 -->
                <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 sm:gap-8 py-5">
                  <div class="min-w-0">
                    <label for="webhook_timeout" class="block text-sm font-medium text-gray-900">
                      {{ $t('webhook.timeout') }}
                    </label>
                    <p class="mt-1 text-sm text-gray-500">{{ $t('webhook.timeoutHelp') }}</p>
                  </div>
                  <input
                    id="webhook_timeout"
                    v-model.number="webhookForm.timeout"
                    type="number"
                    min="1"
                    class="w-full sm:w-28 shrink-0 px-4 py-2"
                  />
                </div>

                <!-- 最大重试次数 -->
                <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 sm:gap-8 py-5">
                  <div class="min-w-0">
                    <label for="webhook_max_attempts" class="block text-sm font-medium text-gray-900">
                      {{ $t('webhook.maxAttempts') }}
                    </label>
                    <p class="mt-1 text-sm text-gray-500">{{ $t('webhook.maxAttemptsHelp') }}</p>
                  </div>
                  <input
                    id="webhook_max_attempts"
                    v-model.number="webhookForm.max_attempts"
                    type="number"
                    min="1"
                    class="w-full sm:w-28 shrink-0 px-4 py-2"
                  />
                </div>
              </div>
            </form>
          </section>

          <!-- 粘性保存栏 -->
          <Transition
            enter-active-class="transition-all duration-200 ease-out"
            enter-from-class="opacity-0 translate-y-3"
            leave-active-class="transition-all duration-150 ease-in"
            leave-to-class="opacity-0 translate-y-3"
          >
            <div
              v-if="webhookDirty"
              class="sticky bottom-4 z-20 flex items-center justify-between gap-4 rounded-xl bg-white/90 backdrop-blur border border-gray-200 shadow-lg px-4 py-3"
            >
              <p class="text-sm text-gray-600 flex items-center gap-2 min-w-0">
                <span class="w-2 h-2 rounded-full bg-amber-500 shrink-0"></span>
                {{ $t('systemConfig.unsavedChanges') }}
              </p>
              <div class="flex items-center gap-3 shrink-0">
                <button
                  type="button"
                  @click="resetWebhookForm"
                  :disabled="webhookSaving"
                  class="btn btn-secondary !px-4 !py-1.5 text-sm"
                >
                  {{ $t('systemConfig.reset') }}
                </button>
                <button
                  type="button"
                  @click="handleWebhookSubmit"
                  :disabled="webhookSaving"
                  class="btn btn-primary !px-4 !py-1.5 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <span v-if="webhookSaving">{{ $t('webhook.saving') }}</span>
                  <span v-else>{{ $t('systemConfig.saveChanges') }}</span>
                </button>
              </div>
            </div>
          </Transition>

          <!-- 对接方回调概览（管理员） -->
          <section class="bg-white rounded-2xl border border-gray-200/80 shadow-sm">
            <header class="px-6 sm:px-8 py-5 border-b border-gray-100 flex items-center justify-between gap-4">
              <div>
                <h3 class="text-sm font-semibold text-gray-900">{{ $t('webhook.endpointsTitle') }}</h3>
                <p class="mt-1 text-xs text-gray-400">{{ $t('webhook.endpointsDesc') }}</p>
              </div>
              <button
                type="button"
                @click="loadAdminApiKeys"
                class="btn btn-secondary !px-3 !py-1.5 text-sm"
              >
                {{ $t('webhook.refresh') }}
              </button>
            </header>
            <div class="overflow-x-auto">
              <table>
                <thead>
                  <tr>
                    <th>{{ $t('webhook.colKeyName') }}</th>
                    <th>{{ $t('webhook.colKeyPrefix') }}</th>
                    <th>{{ $t('webhook.colKeyOwner') }}</th>
                    <th>{{ $t('webhook.colWebhook') }}</th>
                    <th>{{ $t('webhook.colUrl') }}</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody class="bg-white">
                  <tr v-if="adminApiKeys.length === 0">
                    <td colspan="6" class="!border-b-0">
                      <p class="py-8 text-center text-sm text-gray-500">{{ $t('webhook.endpointsEmpty') }}</p>
                    </td>
                  </tr>
                  <tr v-for="k in adminApiKeys" :key="k.key_id">
                    <td class="text-sm text-gray-900">{{ k.name }}</td>
                    <td class="text-sm text-gray-600">
                      <code class="bg-gray-100 px-1.5 py-0.5 rounded font-mono text-xs">{{ k.prefix }}...</code>
                    </td>
                    <td class="text-sm text-gray-600">{{ k.username }}</td>
                    <td class="text-sm">
                      <span
                        class="badge"
                        :class="k.webhook_enabled ? 'bg-indigo-100 text-indigo-700' : 'bg-gray-100 text-gray-500'"
                      >
                        {{ k.webhook_enabled ? $t('webhook.endpointOn') : $t('webhook.endpointOff') }}
                      </span>
                    </td>
                    <td class="text-sm text-gray-600 max-w-xs truncate" :title="k.webhook_url || ''">
                      {{ k.webhook_url || '-' }}
                    </td>
                    <td class="text-sm">
                      <button
                        type="button"
                        @click="keyWebhookTarget = k"
                        class="text-primary-600 hover:text-primary-700 font-medium"
                      >
                        {{ $t('webhook.editEndpoint') }}
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          <!-- 最近投递记录 -->
          <section class="bg-white rounded-2xl border border-gray-200/80 shadow-sm">
            <header class="px-6 sm:px-8 py-5 border-b border-gray-100 flex items-center justify-between gap-4">
              <h3 class="text-sm font-semibold text-gray-900">{{ $t('webhook.deliveriesTitle') }}</h3>
              <button
                type="button"
                @click="loadWebhookDeliveries"
                class="btn btn-secondary !px-3 !py-1.5 text-sm"
              >
                {{ $t('webhook.refresh') }}
              </button>
            </header>
            <div class="overflow-x-auto">
              <table>
                <thead>
                  <tr>
                    <th>{{ $t('webhook.colTime') }}</th>
                    <th>{{ $t('webhook.colEvent') }}</th>
                    <th>{{ $t('webhook.colSource') }}</th>
                    <th>{{ $t('webhook.colTask') }}</th>
                    <th>{{ $t('webhook.colUrl') }}</th>
                    <th>{{ $t('webhook.colStatus') }}</th>
                    <th>{{ $t('webhook.colAttempts') }}</th>
                    <th>{{ $t('webhook.colError') }}</th>
                  </tr>
                </thead>
                <tbody class="bg-white">
                  <tr v-if="webhookDeliveries.length === 0">
                    <td colspan="8" class="!border-b-0">
                      <div class="flex flex-col items-center py-10">
                        <Send class="w-10 h-10 text-gray-300 mb-3" />
                        <p class="text-sm text-gray-500">{{ $t('webhook.deliveriesEmpty') }}</p>
                      </div>
                    </td>
                  </tr>
                  <tr v-for="d in webhookDeliveries" :key="d.delivery_id">
                    <td class="text-sm text-gray-600 whitespace-nowrap">{{ d.created_at }}</td>
                    <td class="text-sm text-gray-900 whitespace-nowrap">{{ d.event }}</td>
                    <td class="text-sm whitespace-nowrap">
                      <span class="badge" :class="webhookSourceClass(d.source)">
                        {{ formatWebhookSource(d.source) }}
                      </span>
                    </td>
                    <td class="text-sm text-gray-600">{{ d.task_id ? d.task_id.slice(0, 8) : '-' }}</td>
                    <td class="text-sm text-gray-600 max-w-xs truncate" :title="d.url">{{ d.url }}</td>
                    <td class="text-sm">
                      <span class="badge" :class="webhookStatusClass(d.status)">
                        {{ formatWebhookStatus(d.status) }}
                      </span>
                    </td>
                    <td class="text-sm text-gray-600">{{ d.attempts }}</td>
                    <td class="text-sm text-gray-600 max-w-xs truncate" :title="d.last_error || ''">{{ d.last_error || '-' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          <!-- Key 级回调配置编辑（管理员视角，复用自助弹窗） -->
          <KeyWebhookDialog
            v-if="keyWebhookTarget"
            :key-id="keyWebhookTarget.key_id"
            :key-name="keyWebhookTarget.name"
            @close="keyWebhookTarget = null"
            @saved="loadAdminApiKeys"
          />
        </div>

        <!-- 审计日志 -->
        <div v-show="activeTab === 'auditLog'" class="space-y-6">
          <section class="bg-white rounded-2xl border border-gray-200/80 shadow-sm">
            <header class="px-6 sm:px-8 py-5 border-b border-gray-100">
              <h2 class="text-lg font-semibold text-gray-900">{{ $t('auditLog.title') }}</h2>
              <p class="mt-1 text-sm text-gray-500">{{ $t('auditLog.description') }}</p>
            </header>

            <div class="px-6 sm:px-8 py-5">
              <!-- 筛选条 -->
              <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
                <div>
                  <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('auditLog.filterAction') }}</label>
                  <select v-model="auditFilters.action" class="w-full px-3 py-2">
                    <option value="">{{ $t('auditLog.all') }}</option>
                    <option v-for="action in auditActionOptions" :key="action" :value="action">
                      {{ formatAuditAction(action) }}
                    </option>
                  </select>
                </div>
                <div>
                  <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('auditLog.filterResult') }}</label>
                  <select v-model="auditFilters.result" class="w-full px-3 py-2">
                    <option value="">{{ $t('auditLog.all') }}</option>
                    <option value="success">{{ $t('auditLog.success') }}</option>
                    <option value="failure">{{ $t('auditLog.failure') }}</option>
                    <option value="denied">{{ $t('auditLog.denied') }}</option>
                  </select>
                </div>
                <div>
                  <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('auditLog.filterStart') }}</label>
                  <input v-model="auditFilters.start" type="date" class="w-full px-3 py-2" />
                </div>
                <div>
                  <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('auditLog.filterEnd') }}</label>
                  <input v-model="auditFilters.end" type="date" class="w-full px-3 py-2" />
                </div>
              </div>
              <div class="flex justify-end gap-3 mb-4">
                <button type="button" @click="resetAuditFilters" class="btn btn-secondary !px-4 !py-1.5 text-sm">
                  {{ $t('auditLog.reset') }}
                </button>
                <button type="button" @click="loadAuditLogs(1)" class="btn btn-primary !px-4 !py-1.5 text-sm">
                  {{ $t('auditLog.search') }}
                </button>
              </div>

              <!-- 日志表格 -->
              <div class="overflow-x-auto">
                <table>
                  <thead>
                    <tr>
                      <th>{{ $t('auditLog.colTime') }}</th>
                      <th>{{ $t('auditLog.colUser') }}</th>
                      <th>{{ $t('auditLog.colAction') }}</th>
                      <th>{{ $t('auditLog.colDetail') }}</th>
                      <th>{{ $t('auditLog.colResource') }}</th>
                      <th>{{ $t('auditLog.colResult') }}</th>
                      <th>{{ $t('auditLog.colIp') }}</th>
                    </tr>
                  </thead>
                  <tbody class="bg-white">
                    <tr v-if="auditLogs.length === 0">
                      <td colspan="7" class="!border-b-0">
                        <div class="flex flex-col items-center py-10">
                          <FileSearch class="w-10 h-10 text-gray-300 mb-3" />
                          <p class="text-sm text-gray-500">{{ $t('auditLog.empty') }}</p>
                        </div>
                      </td>
                    </tr>
                    <tr v-for="log in auditLogs" :key="log.id">
                      <td class="text-sm text-gray-600 whitespace-nowrap">{{ log.created_at }}</td>
                      <td class="text-sm text-gray-900">{{ log.username || $t('auditLog.anonymous') }}</td>
                      <td class="text-sm whitespace-nowrap">
                        <span class="badge" :class="auditActionClass(log.action)">
                          {{ formatAuditAction(log.action) }}
                        </span>
                      </td>
                      <td class="text-sm text-gray-600">{{ formatAuditDetail(log) }}</td>
                      <td class="text-sm text-gray-600" :title="log.resource_id || undefined">
                        {{ formatAuditResource(log) }}
                      </td>
                      <td class="text-sm">
                        <span class="badge" :class="auditResultClass(log.result)">
                          {{ formatAuditResult(log.result) }}
                        </span>
                      </td>
                      <td class="text-sm text-gray-600">{{ log.ip || '-' }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <!-- 分页 -->
              <div class="flex items-center justify-between mt-4">
                <span class="text-sm text-gray-600">{{ $t('auditLog.total', { total: auditTotal }) }}</span>
                <div class="flex items-center gap-3">
                  <span class="text-sm text-gray-500">
                    {{ $t('auditLog.pageInfo', { page: auditPage, pages: auditPages }) }}
                  </span>
                  <button
                    type="button"
                    @click="loadAuditLogs(auditPage - 1)"
                    :disabled="auditPage <= 1"
                    class="btn btn-secondary !px-3 !py-1.5 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {{ $t('auditLog.prevPage') }}
                  </button>
                  <button
                    type="button"
                    @click="loadAuditLogs(auditPage + 1)"
                    :disabled="auditPage >= auditPages"
                    class="btn btn-secondary !px-3 !py-1.5 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {{ $t('auditLog.nextPage') }}
                  </button>
                </div>
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { Settings, Sparkles, Webhook, ScrollText, Send, FileSearch } from 'lucide-vue-next'
import {
  getSystemConfig,
  updateSystemConfig,
  uploadSystemLogo,
  getImageCaptionConfig,
  testImageCaptionConnection,
  getWebhookConfig,
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
import FormToggle from '@/components/FormToggle.vue'
import PageHeader from '@/components/PageHeader.vue'
import KeyWebhookDialog from '@/components/KeyWebhookDialog.vue'
import { getAllAPIKeys } from '@/api/authApi'
import type { AdminAPIKeyInfo } from '@/api/types'

const { t, tm } = useI18n()

const loading = ref(true)
const saving = ref(false)
const uploading = ref(false)

// 设置中心板块导航（ref 切换，无路由跳转）
type TabKey = 'basic' | 'imageCaption' | 'webhook' | 'auditLog'
const activeTab = ref<TabKey>('basic')

const navItems = [
  { key: 'basic', icon: Settings, labelKey: 'systemConfig.nav.basic', descKey: 'systemConfig.nav.basicDesc' },
  { key: 'imageCaption', icon: Sparkles, labelKey: 'systemConfig.nav.imageCaption', descKey: 'systemConfig.nav.imageCaptionDesc' },
  { key: 'webhook', icon: Webhook, labelKey: 'systemConfig.nav.webhook', descKey: 'systemConfig.nav.webhookDesc' },
  { key: 'auditLog', icon: ScrollText, labelKey: 'systemConfig.nav.auditLog', descKey: 'systemConfig.nav.auditLogDesc' },
] as const

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

// 脏状态检测：与各自已保存快照做深度比较（快照在加载/保存成功后由业务函数更新）
const basicDirty = computed(() => JSON.stringify(formData.value) !== JSON.stringify(originalConfig.value))
const imageCaptionDirty = computed(
  () => JSON.stringify(imageCaptionForm.value) !== JSON.stringify(imageCaptionOriginal.value),
)
const webhookDirty = computed(() => JSON.stringify(webhookForm.value) !== JSON.stringify(webhookOriginal.value))

/**
 * 重置图片描述表单为已保存快照
 */
function resetImageCaptionForm() {
  imageCaptionForm.value = { ...imageCaptionOriginal.value }
}

/**
 * 重置 Webhook 表单为已保存快照
 */
function resetWebhookForm() {
  webhookForm.value = { ...webhookOriginal.value }
}

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
  'api_key.webhook_update',
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

const auditPages = computed(() => Math.max(1, Math.ceil(auditTotal.value / auditPageSize)))

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
 * 动作标识翻译，未知动作原样展示。
 * 动作为 a.b 形式（带点号），不能走 $t 点路径解析，需取整段消息对象后按键索引
 */
function formatAuditAction(action: string): string {
  const messages = tm('auditLog.actions') as Record<string, string>
  return messages[action] || action
}

/**
 * 动作徽章配色：按动作前缀分类，便于快速扫读
 */
function auditActionClass(action: string): string {
  const category = action.split('.')[0]
  const classes: Record<string, string> = {
    auth: 'bg-blue-100 text-blue-700',
    api_key: 'bg-purple-100 text-purple-700',
    config: 'bg-amber-100 text-amber-700',
    task: 'bg-indigo-100 text-indigo-700',
    admin: 'bg-rose-100 text-rose-700',
  }
  return classes[category] || 'bg-gray-100 text-gray-600'
}

/**
 * 解析 detail JSON，失败时返回空对象
 */
function parseAuditDetail(detail: string | null): Record<string, any> {
  if (!detail) return {}
  try {
    const parsed = JSON.parse(detail)
    return parsed && typeof parsed === 'object' ? parsed : {}
  } catch {
    return {}
  }
}

/**
 * 详情列人性化渲染：按动作套用语句模板，无法渲染时回退原始 JSON
 */
function formatAuditDetail(log: AuditLogItem): string {
  const detail = parseAuditDetail(log.detail)
  if (Object.keys(detail).length === 0) return '-'

  const params: Record<string, string> = {}
  if (detail.file_name) params.fileName = String(detail.file_name)
  if (detail.username) params.username = String(detail.username)
  if (detail.name) params.name = String(detail.name)
  if (Array.isArray(detail.scopes)) params.scopes = detail.scopes.join(', ')
  if (Array.isArray(detail.keys)) params.keys = detail.keys.join(', ')
  if (detail.deleted_count !== undefined) params.count = String(detail.deleted_count)
  if (detail.reset_count !== undefined) params.count = String(detail.reset_count)
  if (detail.days !== undefined) params.days = String(detail.days)
  if (detail.timeout_minutes !== undefined) params.minutes = String(detail.timeout_minutes)
  if (detail.reason === 'account_disabled') params.reason = t('auditLog.reasonAccountDisabled')
  if (detail.enabled !== undefined)
    params.enabled = detail.enabled ? t('auditLog.stateEnabled') : t('auditLog.stateDisabled')
  if (detail.url !== undefined) params.url = String(detail.url || '-')

  const templates = tm('auditLog.details') as Record<string, string>
  const template = templates[log.action]
  if (template) {
    // 手工替换 {placeholder}，绕过 $t 的点路径解析限制
    return template.replace(/\{(\w+)\}/g, (match, name) => params[name] ?? (name === 'reason' ? '' : match))
  }

  // 未知动作：退化为 key: value 片段
  return Object.entries(detail)
    .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`)
    .join('；')
}

/**
 * 资源列展示：翻译资源类型，超长 ID 截断并保留完整值提示
 */
function formatAuditResource(log: AuditLogItem): string {
  if (!log.resource_type) return '-'
  const typeKey = `auditLog.resources.${log.resource_type}`
  const translated = t(typeKey)
  const typeLabel = translated === typeKey ? log.resource_type : translated
  if (!log.resource_id) return typeLabel
  const id = log.resource_id
  return id.length > 12 ? `${typeLabel} ${id.slice(0, 8)}…` : `${typeLabel} ${id}`
}

function formatAuditResult(result: string): string {
  if (result === 'success') return t('auditLog.success')
  if (result === 'failure') return t('auditLog.failure')
  if (result === 'denied') return t('auditLog.denied')
  return result
}

function auditResultClass(result: string): string {
  if (result === 'success') return 'bg-green-100 text-green-700'
  if (result === 'failure') return 'bg-red-100 text-red-700'
  if (result === 'denied') return 'bg-orange-100 text-orange-700'
  return 'bg-gray-100 text-gray-600'
}

// ==================== Webhook 通知 ====================

const webhookSaving = ref(false)

const webhookOriginal = ref<WebhookConfig>({
  timeout: 10,
  max_attempts: 8,
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
 * 保存 Webhook 投递策略（只提交变更过的字段）
 */
async function handleWebhookSubmit() {
  try {
    webhookSaving.value = true

    const form = webhookForm.value
    const original = webhookOriginal.value
    const updates: SystemConfigUpdateRequest = {}
    if (form.timeout !== original.timeout) {
      updates.webhook_timeout = form.timeout
    }
    if (form.max_attempts !== original.max_attempts) {
      updates.webhook_max_attempts = form.max_attempts
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
  if (status === 'delivered') return 'bg-green-100 text-green-700'
  if (status === 'failed') return 'bg-red-100 text-red-700'
  if (status === 'dead') return 'bg-gray-100 text-gray-600'
  return 'bg-yellow-100 text-yellow-700'
}

// ==================== 对接方回调概览（管理员） ====================

const adminApiKeys = ref<AdminAPIKeyInfo[]>([])
const keyWebhookTarget = ref<AdminAPIKeyInfo | null>(null)

async function loadAdminApiKeys() {
  try {
    const response = await getAllAPIKeys()
    adminApiKeys.value = response.api_keys || []
  } catch (error: any) {
    console.error('Failed to load api keys:', error)
    toast.error(t('webhook.endpointsLoadError'))
  }
}

function formatWebhookSource(source: string): string {
  const map: Record<string, string> = {
    task: t('webhook.sourceTask'),
    api_key: t('webhook.sourceApiKey'),
    global: t('webhook.sourceGlobal'),
  }
  return map[source] || source
}

function webhookSourceClass(source: string): string {
  if (source === 'api_key') return 'bg-indigo-100 text-indigo-700'
  if (source === 'task') return 'bg-sky-100 text-sky-700'
  return 'bg-gray-100 text-gray-600'
}

onMounted(() => {
  loadConfig()
  loadImageCaptionConfig()
  loadWebhookConfig()
  loadWebhookDeliveries()
  loadAdminApiKeys()
  loadAuditLogs(1)
})
</script>
