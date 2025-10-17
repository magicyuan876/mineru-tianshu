<template>
  <span :class="badgeClass" class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium">
    <span :class="dotClass" class="w-1.5 h-1.5 rounded-full mr-1.5"></span>
    {{ statusText }}
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { TaskStatus } from '@/api/types'

const props = defineProps<{
  status: TaskStatus
}>()

const statusText = computed(() => {
  const statusMap: Record<TaskStatus, string> = {
    pending: '等待中',
    processing: '处理中',
    completed: '已完成',
    failed: '失败',
    cancelled: '已取消',
  }
  return statusMap[props.status] || props.status
})

const badgeClass = computed(() => {
  const classMap: Record<TaskStatus, string> = {
    pending: 'bg-gray-100 text-gray-800',
    processing: 'bg-yellow-100 text-yellow-800',
    completed: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800',
    cancelled: 'bg-gray-100 text-gray-600',
  }
  return classMap[props.status] || 'bg-gray-100 text-gray-800'
})

const dotClass = computed(() => {
  const classMap: Record<TaskStatus, string> = {
    pending: 'bg-gray-400',
    processing: 'bg-yellow-400 animate-pulse',
    completed: 'bg-green-500',
    failed: 'bg-red-500',
    cancelled: 'bg-gray-400',
  }
  return classMap[props.status] || 'bg-gray-400'
})
</script>

