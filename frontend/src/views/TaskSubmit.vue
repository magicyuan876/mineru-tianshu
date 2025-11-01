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
          acceptHint="支持 PDF、图片、Word、Excel、PowerPoint、HTML、音频（MP3/WAV/M4A）、视频（MP4/AVI/MKV/MOV）、生物序列（FASTA/GenBank）等多种格式"
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
              解析引擎
              <span class="text-gray-500 font-normal">（影响解析质量和速度）</span>
            </label>
            <select
              v-model="config.backend"
              @change="onBackendChange"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="auto">🎯 自动选择（推荐，根据文件类型自动选择最佳引擎）</option>
              <optgroup label="文档解析">
                <option value="pipeline">MinerU Pipeline（完整解析）</option>
                <option value="paddleocr-vl">PaddleOCR-VL（多语言 OCR，109+ 语言）</option>
                <option value="vlm-transformers">VLM Transformers（视觉语言模型）</option>
                <option value="vlm-vllm-engine">VLM vLLM Engine（高性能 VLM）</option>
              </optgroup>
              <optgroup label="音频/视频处理">
                <option value="sensevoice">SenseVoice（语音识别，说话人识别）</option>
                <option value="video">Video（视频转文字，提取音频+语音识别）</option>
              </optgroup>
              <optgroup label="专业格式解析">
                <option value="fasta">🧬 FASTA（生物序列格式）</option>
                <option value="genbank">🧬 GenBank（基因序列注释格式）</option>
              </optgroup>
            </select>
            <p v-if="config.backend === 'auto'" class="mt-1 text-xs text-gray-500">
              🎯 自动选择: 系统会根据文件扩展名智能选择最合适的引擎进行处理
            </p>

            <p v-if="config.backend === 'paddleocr-vl'" class="mt-1 text-xs text-gray-500">
              🌏 PaddleOCR-VL: 自动多语言识别，支持文档方向校正、文本矫正、版面检测
            </p>
            <p v-if="config.backend === 'sensevoice'" class="mt-1 text-xs text-gray-500">
              🎙️ SenseVoice: 支持多语言语音识别、自动说话人识别、情感识别
            </p>
            <p v-if="config.backend === 'video'" class="mt-1 text-xs text-gray-500">
              🎬 Video: 从视频中提取音频并转写为文字，支持多种视频格式（MP4/AVI/MKV/MOV/WebM 等）
            </p>
            <p v-if="config.backend === 'fasta'" class="mt-1 text-xs text-gray-500">
              🧬 FASTA: 解析生物序列文件（.fasta/.fa/.fna），支持蛋白质和核酸序列，生成语义化描述
            </p>
            <p v-if="config.backend === 'genbank'" class="mt-1 text-xs text-gray-500">
              🧬 GenBank: 解析基因序列注释文件（.gb/.gbk），提取特征、注释和元数据
            </p>
          </div>

          <!-- 语言选择 -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              文档/音频/视频语言
            </label>
            <select
              v-model="config.lang"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="auto">自动检测（音频推荐）</option>
              <option value="ch">中文</option>
              <option value="en">英文</option>
              <option value="korean">韩文</option>
              <option value="japan">日文</option>
            </select>
            <p class="mt-1 text-xs text-gray-500">
              💡 音频文件请选择 SenseVoice 引擎，视频文件请选择 Video 引擎
            </p>
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

        <!-- 提示信息 -->
        <div v-if="['pipeline', 'paddleocr-vl'].includes(config.backend)" class="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <p class="text-sm text-blue-800">
            💡 提示：{{ config.backend === 'pipeline' ? 'MinerU' : 'PaddleOCR-VL' }} 会同时生成 Markdown 和 JSON 两种格式，您可以在查看结果时切换显示格式。
          </p>
        </div>

        <!-- Video 专属配置 -->
        <div v-if="config.backend === 'video'" class="mt-6 pt-6 border-t border-gray-200">
          <h3 class="text-base font-semibold text-gray-900 mb-4">🎬 视频处理选项</h3>

          <div class="space-y-4">
            <!-- 音频选项 -->
            <div>
              <label class="flex items-center">
                <input
                  v-model="config.keep_audio"
                  type="checkbox"
                  class="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
                />
                <span class="ml-2 text-sm text-gray-700">保留提取的音频文件</span>
              </label>
              <p class="text-xs text-gray-500 ml-6 mt-1">
                💡 默认情况下，处理完成后会自动删除临时音频文件以节省空间
              </p>
            </div>

            <!-- 关键帧OCR选项 -->
            <div class="pt-4 border-t border-gray-100">
              <label class="flex items-center">
                <input
                  v-model="config.enable_keyframe_ocr"
                  type="checkbox"
                  class="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
                />
                <span class="ml-2 text-sm text-gray-700 font-medium">
                  启用关键帧 OCR 识别
                  <span class="ml-1 px-1.5 py-0.5 text-xs bg-blue-100 text-blue-700 rounded">实验性</span>
                </span>
              </label>
              <p class="text-xs text-gray-500 ml-6 mt-1">
                📸 自动提取视频关键帧并进行 OCR 识别，适用于含有文字内容的视频（如课程、演示等）
              </p>

              <!-- 关键帧OCR子选项 -->
              <div v-if="config.enable_keyframe_ocr" class="ml-6 mt-3 space-y-3 pl-4 border-l-2 border-primary-200">
                <div>
                  <label class="block text-sm font-medium text-gray-700 mb-2">
                    OCR 引擎
                  </label>
                  <select
                    v-model="config.ocr_backend"
                    class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  >
                    <option value="paddleocr-vl">PaddleOCR-VL（推荐，支持多语言）</option>
                  </select>
                </div>

                <label class="flex items-center">
                  <input
                    v-model="config.keep_keyframes"
                    type="checkbox"
                    class="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
                  />
                  <span class="ml-2 text-sm text-gray-700">保留提取的关键帧图像</span>
                </label>
              </div>
            </div>
          </div>
        </div>

        <!-- PaddleOCR-VL 专属配置 -->
        <div v-if="config.backend === 'paddleocr-vl'" class="mt-6 pt-6 border-t border-gray-200">
          <div class="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
            <h3 class="text-sm font-semibold text-blue-900 mb-2">✨ 已启用增强功能</h3>
            <ul class="text-xs text-blue-800 space-y-1">
              <li>✅ 文档方向自动分类与校正</li>
              <li>✅ 文本图像矫正（修正扭曲变形）</li>
              <li>✅ 版面区域智能检测与排序</li>
              <li>✅ 自动多语言识别（109+ 语言，无需手动指定）</li>
            </ul>
          </div>

          <div class="text-sm text-gray-600">
            <p class="mb-2">💡 <strong>提示：</strong></p>
            <ul class="list-disc list-inside space-y-1 text-xs">
              <li>PaddleOCR-VL 会自动检测文档语言，无需手动选择</li>
              <li>支持中文、英文、日文、韩文、阿拉伯文等 109+ 种语言</li>
              <li>原生支持 PDF 多页文档处理</li>
              <li>仅支持 GPU 推理（要求 NVIDIA GPU）</li>
            </ul>
          </div>
        </div>

        <!-- 功能开关（仅 Pipeline） -->
        <div v-if="config.backend === 'pipeline'" class="mt-6 space-y-3">
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

        <!-- 水印去除配置（PDF/图片） -->
        <div v-if="['pipeline', 'paddleocr-vl'].includes(config.backend)" class="mt-6 pt-6 border-t border-gray-200">
          <h3 class="text-base font-semibold text-gray-900 mb-4">🎨 水印去除选项</h3>

          <div class="space-y-4">
            <!-- 水印去除开关 -->
            <div>
              <label class="flex items-center">
                <input
                  v-model="config.remove_watermark"
                  type="checkbox"
                  class="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
                />
                <span class="ml-2 text-sm text-gray-700 font-medium">
                  启用水印去除
                  <span class="ml-1 px-1.5 py-0.5 text-xs bg-purple-100 text-purple-700 rounded">智能检测</span>
                </span>
              </label>
              <p class="text-xs text-gray-500 ml-6 mt-1">
                🔍 使用 YOLO11x + LaMa 自动检测并去除图片和 PDF 中的水印
              </p>
            </div>

            <!-- 高级选项 -->
            <div v-if="config.remove_watermark" class="ml-6 mt-3 space-y-3 pl-4 border-l-2 border-purple-200">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">
                  检测置信度
                  <span class="text-gray-500 font-normal text-xs">（{{ config.watermark_conf_threshold }}）</span>
                </label>
                <input
                  v-model.number="config.watermark_conf_threshold"
                  type="range"
                  min="0.1"
                  max="0.9"
                  step="0.05"
                  class="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-purple-600"
                />
                <div class="flex justify-between text-xs text-gray-500 mt-1">
                  <span>0.1（更多）</span>
                  <span>0.35（推荐）</span>
                  <span>0.9（更少）</span>
                </div>
                <p class="text-xs text-gray-500 mt-1">
                  💡 值越小检测越敏感，可能有误检；值越大只检测高置信度水印
                </p>
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">
                  去除范围扩展
                  <span class="text-gray-500 font-normal text-xs">（{{ config.watermark_dilation }} 像素）</span>
                </label>
                <input
                  v-model.number="config.watermark_dilation"
                  type="range"
                  min="0"
                  max="30"
                  step="5"
                  class="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-purple-600"
                />
                <div class="flex justify-between text-xs text-gray-500 mt-1">
                  <span>0（精确）</span>
                  <span>10（推荐）</span>
                  <span>30（扩大）</span>
                </div>
                <p class="text-xs text-gray-500 mt-1">
                  💡 扩大去除区域，防止水印边缘残留
                </p>
              </div>
            </div>

            <!-- PDF 处理说明 -->
            <div v-if="config.remove_watermark" class="bg-purple-50 border border-purple-200 rounded-lg p-3 mt-3">
              <p class="text-xs text-purple-800">
                <strong>📄 PDF 智能处理：</strong>
              </p>
              <ul class="text-xs text-purple-700 mt-1 ml-4 list-disc space-y-0.5">
                <li>可编辑 PDF：直接删除水印对象</li>
                <li>扫描件 PDF：转图片 → 去水印 → 重组 PDF</li>
                <li>图片格式：直接使用 YOLO + LaMa 处理</li>
              </ul>
            </div>
          </div>
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
  backend: 'auto' as Backend,  // 默认自动选择引擎
  lang: 'auto' as Language,  // 默认自动检测语言
  method: 'auto' as ParseMethod,
  formula_enable: true,
  table_enable: true,
  priority: 0,
  // Video 专属配置
  keep_audio: false,
  enable_keyframe_ocr: false,
  ocr_backend: 'paddleocr-vl',
  keep_keyframes: false,
  // 水印去除配置
  remove_watermark: false,
  watermark_conf_threshold: 0.35,
  watermark_dilation: 10,
})

function onFilesChange(newFiles: File[]) {
  files.value = newFiles
}

function onBackendChange() {
  // 根据选择的引擎调整语言设置
  if (config.backend === 'pipeline') {
    // MinerU Pipeline 不支持 auto，默认使用中文
    config.lang = 'ch'
  } else if (['fasta', 'genbank'].includes(config.backend)) {
    // 专业格式引擎不需要语言选择
    config.lang = 'en'
  } else {
    // 其他引擎（auto/音频/视频/OCR）默认自动检测
    config.lang = 'auto'
  }
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
