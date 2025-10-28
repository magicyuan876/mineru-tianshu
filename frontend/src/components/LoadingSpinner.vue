<template>
  <div :class="containerClass" class="flex items-center justify-center">
    <div :class="spinnerClass" class="animate-spin rounded-full border-t-2 border-b-2"></div>
    <p v-if="text" :class="textClass" class="ml-3">{{ text }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  size?: 'sm' | 'md' | 'lg'
  text?: string
  fullscreen?: boolean
}>(), {
  size: 'md',
  fullscreen: false
})

const containerClass = computed(() => {
  if (props.fullscreen) {
    return 'fixed inset-0 bg-white bg-opacity-75 z-50'
  }
  return ''
})

const spinnerClass = computed(() => {
  const sizeMap = {
    sm: 'h-4 w-4 border-primary-500',
    md: 'h-8 w-8 border-primary-600',
    lg: 'h-12 w-12 border-primary-600',
  }
  return sizeMap[props.size]
})

const textClass = computed(() => {
  const sizeMap = {
    sm: 'text-sm text-gray-600',
    md: 'text-base text-gray-700',
    lg: 'text-lg text-gray-800',
  }
  return sizeMap[props.size]
})
</script>
