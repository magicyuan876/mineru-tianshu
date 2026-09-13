<template>
  <header class="mb-6 lg:mb-8 flex flex-wrap items-end justify-between gap-4">
    <div class="min-w-0">
      <h1 class="text-2xl font-bold text-gray-900 tracking-tight">{{ title }}</h1>
      <p v-if="description" class="mt-1 text-sm text-gray-500">{{ description }}</p>
    </div>
    <div v-if="$slots.actions" class="flex items-center gap-3 flex-shrink-0">
      <slot name="actions" />
    </div>
  </header>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  description?: string
}>()
</script>
