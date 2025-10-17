<template>
  <div>
    <!-- 页面标题 -->
    <div class="mb-6">
      <h1 class="text-2xl font-bold text-gray-900">提交任务</h1>
      <p class="mt-1 text-sm text-gray-600">上传文档并配置解析选项</p>
    </div>

    <div class="max-w-4xl mx-auto">
      <!-- 文件上传 -->
      <div class="card mb-6">
        <h2 class="text-lg font-semibold text-gray-900 mb-4">选择文件</h2>
        <FileUploader
          ref="fileUploader"
          :multiple="true"
          :maxSize="100 * 1024 * 1024"
          acceptHint="支持 PDF、图片、Word、Excel、PowerPoint、HTML 等多种格式"
          @update:files="onFilesChange"
        />
      </div>

      <!-- 配置选项 -->
      <div class="card mb-6">
        <h2 class="text-lg font-semibold text-gray-900 mb-4">解析配置</h2>
        
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <!-- Backend 选择 -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              处理后端
              <span class="text-gray-500 font-normal">（影响解析质量和速度）</span>
            </label>
            <select
              v-model="config.backend"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="pipeline">Pipeline（推荐，平衡性能）</option>
              <option value="vlm-transformers">VLM Transformers（高质量）</option>
              <option value="vlm-vllm-engine">VLM vLLM Engine（高性能）</option>
            </select>
          </div>

          <!-- 语言选择 -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              文档语言
            </label>
            <select
              v-model="config.lang"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="ch">中文</option>
              <option value="en">英文</option>
              <option value="korean">韩文</option>
              <option value="japan">日文</option>
            </select>
          </div>

          <!-- 解析方法 -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              解析方法
            </label>
            <select
              v-model="config.method"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="auto">自动选择（推荐）</option>
              <option value="txt">文本提取</option>
              <option value="ocr">OCR 识别</option>
            </select>
          </div>

          <!-- 优先级 -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              任务优先级
              <span class="text-gray-500 font-normal">（0-100，数字越大越优先）</span>
            </label>
            <input
              v-model.number="config.priority"
              type="number"
              min="0"
              max="100"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>
        </div>

        <!-- 功能开关 -->
        <div class="mt-6 space-y-3">
          <label class="flex items-center">
            <input
              v-model="config.formula_enable"
              type="checkbox"
              class="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
            />
            <span class="ml-2 text-sm text-gray-700">启用公式识别</span>
          </label>

          <label class="flex items-center">
            <input
              v-model="config.table_enable"
              type="checkbox"
              class="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
            />
            <span class="ml-2 text-sm text-gray-700">启用表格识别</span>
          </label>
        </div>
      </div>

      <!-- 错误提示 -->
      <div v-if="errorMessage" class="card bg-red-50 border-red-200 mb-6">
        <div class="flex items-start">
          <AlertCircle class="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
          <div class="ml-3 flex-1">
            <h3 class="text-sm font-medium text-red-800">提交失败</h3>
            <p class="mt-1 text-sm text-red-700">{{ errorMessage }}</p>
          </div>
          <button
            @click="errorMessage = ''"
            class="ml-auto -mr-1 -mt-1 p-1 text-red-600 hover:text-red-800"
          >
            <X class="w-5 h-5" />
          </button>
        </div>
      </div>

      <!-- 提交按钮 -->
      <div class="flex justify-end gap-3">
        <router-link to="/" class="btn btn-secondary">
          取消
        </router-link>
        <button
          @click="submitTasks"
          :disabled="files.length === 0 || submitting"
          class="btn btn-primary disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
        >
          <Loader v-if="submitting" class="w-4 h-4 mr-2 animate-spin" />
          <Upload v-else class="w-4 h-4 mr-2" />
          {{ submitting ? '提交中...' : `提交任务 (${files.length})` }}
        </button>
      </div>

      <!-- 提交进度 -->
      <div v-if="submitting || submitProgress.length > 0" class="card mt-6">
        <h3 class="text-lg font-semibold text-gray-900 mb-4">提交进度</h3>
        <div class="space-y-2">
          <div
            v-for="(progress, index) in submitProgress"
            :key="index"
            class="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
          >
            <div class="flex items-center flex-1">
              <FileText class="w-5 h-5 text-gray-400 flex-shrink-0" />
              <span class="ml-3 text-sm text-gray-900">{{ progress.fileName }}</span>
            </div>
            <div class="flex items-center">
              <CheckCircle v-if="progress.success" class="w-5 h-5 text-green-600" />
              <XCircle v-else-if="progress.error" class="w-5 h-5 text-red-600" />
              <Loader v-else class="w-5 h-5 text-primary-600 animate-spin" />
              <span v-if="progress.taskId" class="ml-2 text-xs text-gray-500">
                {{ progress.taskId }}
              </span>
            </div>
          </div>
        </div>

        <!-- 完成后的操作 -->
        <div v-if="!submitting && submitProgress.length > 0" class="mt-4 flex justify-end gap-3">
          <button
            @click="resetForm"
            class="btn btn-secondary"
          >
            继续提交
          </button>
          <router-link to="/tasks" class="btn btn-primary">
            查看任务列表
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useTaskStore } from '@/stores'
import FileUploader from '@/components/FileUploader.vue'
import {
  Upload,
  Loader,
  AlertCircle,
  X,
  FileText,
  CheckCircle,
  XCircle,
} from 'lucide-vue-next'
import type { Backend, Language, ParseMethod } from '@/api/types'

const router = useRouter()
const taskStore = useTaskStore()

const fileUploader = ref<InstanceType<typeof FileUploader>>()
const files = ref<File[]>([])
const submitting = ref(false)
const errorMessage = ref('')

interface SubmitProgress {
  fileName: string
  success: boolean
  error: boolean
  taskId?: string
}

const submitProgress = ref<SubmitProgress[]>([])

const config = reactive({
  backend: 'pipeline' as Backend,
  lang: 'ch' as Language,
  method: 'auto' as ParseMethod,
  formula_enable: true,
  table_enable: true,
  priority: 0,
})

function onFilesChange(newFiles: File[]) {
  files.value = newFiles
}

async function submitTasks() {
  if (files.value.length === 0) {
    errorMessage.value = '请先选择文件'
    return
  }

  submitting.value = true
  errorMessage.value = ''
  submitProgress.value = files.value.map(f => ({
    fileName: f.name,
    success: false,
    error: false,
  }))

  // 批量提交任务
  for (let i = 0; i < files.value.length; i++) {
    const file = files.value[i]
    try {
      const response = await taskStore.submitTask({
        file,
        ...config,
      })
      submitProgress.value[i].success = true
      submitProgress.value[i].taskId = response.task_id
    } catch (err: any) {
      submitProgress.value[i].error = true
      console.error(`Failed to submit ${file.name}:`, err)
    }
  }

  submitting.value = false

  // 检查是否全部成功
  const allSuccess = submitProgress.value.every(p => p.success)
  if (allSuccess && files.value.length === 1) {
    // 单个文件且成功，跳转到详情页
    const taskId = submitProgress.value[0].taskId!
    router.push(`/tasks/${taskId}`)
  }
}

function resetForm() {
  files.value = []
  submitProgress.value = []
  errorMessage.value = ''
  fileUploader.value?.clearFiles()
}
</script>

