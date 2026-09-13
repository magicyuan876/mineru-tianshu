<template>
  <div class="group relative overflow-hidden bg-white rounded-xl lg:rounded-2xl shadow-lg hover:shadow-2xl transition-all duration-300 p-4 lg:p-6 border border-gray-100/50 hover:scale-105">
    <!-- 背景装饰 -->
    <div :class="bgGradientClass" class="absolute inset-0 opacity-5 group-hover:opacity-10 transition-opacity duration-300"></div>

    <div class="relative flex items-center justify-between">
      <div class="flex-1 min-w-0">
        <p class="text-xs lg:text-sm font-semibold text-gray-600 uppercase tracking-wide truncate" :title="title">{{ title }}</p>
        <p class="mt-2 lg:mt-3 text-2xl lg:text-3xl xl:text-4xl font-bold" :class="valueClass">{{ value }}</p>
        <p v-if="subtitle" class="mt-1 lg:mt-2 text-xs lg:text-sm text-gray-500 font-medium truncate" :title="subtitle">{{ subtitle }}</p>
      </div>
      <div v-if="icon" :class="iconBgClass" class="p-2 lg:p-3 xl:p-4 rounded-xl lg:rounded-2xl shadow-lg group-hover:scale-110 transition-transform duration-300 flex-shrink-0 ml-2">
        <component :is="icon" :class="iconClass" class="w-5 h-5 lg:w-6 lg:h-6 xl:w-8 xl:h-8" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, type Component } from 'vue'

const props = withDefaults(defineProps<{
  title: string
  value: string | number
  subtitle?: string
  icon?: Component
  color?: 'gray' | 'yellow' | 'green' | 'red' | 'blue'
}>(), {
  color: 'blue'
})

const valueClass = computed(() => {
  const classMap = {
    gray: 'text-gray-900',
    yellow: 'text-yellow-600',
    green: 'text-green-600',
    red: 'text-red-600',
    blue: 'text-blue-600',
  }
  return classMap[props.color]
})

const iconBgClass = computed(() => {
  const classMap = {
    gray: 'bg-gray-100',
    yellow: 'bg-yellow-100',
    green: 'bg-green-100',
    red: 'bg-red-100',
    blue: 'bg-blue-100',
  }
  return classMap[props.color]
})

const iconClass = computed(() => {
  const classMap = {
    gray: 'text-gray-600',
    yellow: 'text-yellow-600',
    green: 'text-green-600',
    red: 'text-red-600',
    blue: 'text-blue-600',
  }
  return classMap[props.color]
})

const bgGradientClass = computed(() => {
  const classMap = {
    gray: 'bg-gradient-to-br from-gray-400 to-gray-600',
    yellow: 'bg-gradient-to-br from-yellow-400 to-yellow-600',
    green: 'bg-gradient-to-br from-green-400 to-green-600',
    red: 'bg-gradient-to-br from-red-400 to-red-600',
    blue: 'bg-gradient-to-br from-blue-400 to-blue-600',
  }
  return classMap[props.color]
})
</script>
