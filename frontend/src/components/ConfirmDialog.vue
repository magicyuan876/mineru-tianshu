<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="modelValue" class="fixed inset-0 z-50 overflow-y-auto">
        <!-- 遮罩层 -->
        <div class="fixed inset-0 bg-black bg-opacity-50 transition-opacity" @click="onCancel"></div>
        
        <!-- 对话框 -->
        <div class="flex min-h-screen items-center justify-center p-4">
          <div class="relative bg-white rounded-lg shadow-xl max-w-md w-full p-6 transform transition-all">
            <!-- 标题 -->
            <h3 class="text-lg font-semibold text-gray-900 mb-4">{{ title }}</h3>
            
            <!-- 内容 -->
            <p class="text-sm text-gray-600 mb-6">{{ message }}</p>
            
            <!-- 按钮 -->
            <div class="flex justify-end gap-3">
              <button
                @click="onCancel"
                class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                {{ cancelText }}
              </button>
              <button
                @click="onConfirm"
                :class="confirmButtonClass"
                class="px-4 py-2 text-sm font-medium text-white rounded-lg"
              >
                {{ confirmText }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  modelValue: boolean
  title?: string
  message?: string
  confirmText?: string
  cancelText?: string
  type?: 'danger' | 'warning' | 'info'
}>(), {
  title: '确认',
  message: '您确定要执行此操作吗?',
  confirmText: '确定',
  cancelText: '取消',
  type: 'danger'
})

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'confirm': []
  'cancel': []
}>()

const confirmButtonClass = computed(() => {
  const classMap = {
    danger: 'bg-red-600 hover:bg-red-700',
    warning: 'bg-yellow-600 hover:bg-yellow-700',
    info: 'bg-blue-600 hover:bg-blue-700',
  }
  return classMap[props.type]
})

function onConfirm() {
  emit('confirm')
  emit('update:modelValue', false)
}

function onCancel() {
  emit('cancel')
  emit('update:modelValue', false)
}
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>

