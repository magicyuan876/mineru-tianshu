<template>
  <div class="card hover:shadow-lg transition-shadow">
    <div class="flex items-center justify-between">
      <div class="flex-1">
        <p class="text-sm font-medium text-gray-600">{{ title }}</p>
        <p class="mt-2 text-3xl font-semibold" :class="valueClass">{{ value }}</p>
        <p v-if="subtitle" class="mt-1 text-xs text-gray-500">{{ subtitle }}</p>
      </div>
      <div v-if="icon" :class="iconBgClass" class="p-3 rounded-full">
        <component :is="icon" :class="iconClass" class="w-6 h-6" />
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
</script>
