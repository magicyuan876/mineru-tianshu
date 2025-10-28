<template>
  <div class="json-node">
    <!-- 对象 -->
    <div v-if="isObject" class="node-object">
      <div class="node-line">
        <button
          v-if="hasChildren"
          @click="toggle"
          class="toggle-btn"
        >
          <ChevronRight :class="['w-3 h-3 transition-transform', isExpanded ? 'rotate-90' : '']" />
        </button>
        <span v-else class="toggle-placeholder"></span>
        <span v-if="nodeKey !== null" class="node-key">{{ nodeKey }}:</span>
        <span class="node-bracket">{{ '{' }}</span>
        <span v-if="!isExpanded" class="node-preview">
          {{ objectPreview }}
        </span>
        <span v-if="!isExpanded" class="node-bracket">{{ '}' }}</span>
        <span class="node-count">{{ objectCount }}</span>
      </div>
      <div v-if="isExpanded" class="node-children">
        <div v-for="(value, key) in data" :key="key" class="node-child">
          <JsonNode
            :data="value"
            :node-key="String(key)"
            :path="[...path, String(key)]"
            :expanded-paths="expandedPaths"
            @toggle="$emit('toggle', $event)"
          />
        </div>
        <div class="node-line">
          <span class="toggle-placeholder"></span>
          <span class="node-bracket">{{ '}' }}</span>
        </div>
      </div>
    </div>

    <!-- 数组 -->
    <div v-else-if="isArray" class="node-array">
      <div class="node-line">
        <button
          v-if="hasChildren"
          @click="toggle"
          class="toggle-btn"
        >
          <ChevronRight :class="['w-3 h-3 transition-transform', isExpanded ? 'rotate-90' : '']" />
        </button>
        <span v-else class="toggle-placeholder"></span>
        <span v-if="nodeKey !== null" class="node-key">{{ nodeKey }}:</span>
        <span class="node-bracket">{{ '[' }}</span>
        <span v-if="!isExpanded" class="node-preview">
          {{ arrayPreview }}
        </span>
        <span v-if="!isExpanded" class="node-bracket">{{ ']' }}</span>
        <span class="node-count">{{ arrayCount }}</span>
      </div>
      <div v-if="isExpanded" class="node-children">
        <div v-for="(value, index) in data" :key="index" class="node-child">
          <JsonNode
            :data="value"
            :node-key="String(index)"
            :path="[...path, String(index)]"
            :expanded-paths="expandedPaths"
            @toggle="$emit('toggle', $event)"
          />
        </div>
        <div class="node-line">
          <span class="toggle-placeholder"></span>
          <span class="node-bracket">{{ ']' }}</span>
        </div>
      </div>
    </div>

    <!-- 基础类型 -->
    <div v-else class="node-value">
      <div class="node-line">
        <span class="toggle-placeholder"></span>
        <span v-if="nodeKey !== null" class="node-key">{{ nodeKey }}:</span>
        <span :class="valueClass" class="selectable" @click="copyValue">{{ formattedValue }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ChevronRight } from 'lucide-vue-next'

const props = defineProps<{
  data: any
  nodeKey?: string | null
  path: string[]
  expandedPaths: Set<string>
}>()

const emit = defineEmits<{
  toggle: [path: string[]]
}>()

// 当前路径字符串
const pathStr = computed(() => props.path.join('.'))

// 是否展开
const isExpanded = computed(() => props.expandedPaths.has(pathStr.value))

// 类型判断
const isObject = computed(() =>
  typeof props.data === 'object' &&
  props.data !== null &&
  !Array.isArray(props.data)
)

const isArray = computed(() => Array.isArray(props.data))

const hasChildren = computed(() => {
  if (isObject.value) {
    return Object.keys(props.data).length > 0
  } else if (isArray.value) {
    return props.data.length > 0
  }
  return false
})

// 对象预览
const objectPreview = computed(() => {
  if (!isObject.value) return ''
  const keys = Object.keys(props.data)
  if (keys.length === 0) return ''
  if (keys.length <= 3) {
    return keys.map(k => `${k}: ${getValuePreview(props.data[k])}`).join(', ')
  }
  return keys.slice(0, 3).map(k => `${k}: ${getValuePreview(props.data[k])}`).join(', ') + ', ...'
})

const objectCount = computed(() => {
  if (!isObject.value) return ''
  const count = Object.keys(props.data).length
  return count > 0 ? `// ${count} keys` : ''
})

// 数组预览
const arrayPreview = computed(() => {
  if (!isArray.value) return ''
  const arr = props.data
  if (arr.length === 0) return ''
  if (arr.length <= 3) {
    return arr.map((item: any) => getValuePreview(item)).join(', ')
  }
  return arr.slice(0, 3).map((item: any) => getValuePreview(item)).join(', ') + ', ...'
})

const arrayCount = computed(() => {
  if (!isArray.value) return ''
  const count = props.data.length
  return count > 0 ? `// ${count} items` : ''
})

// 基础类型值
const formattedValue = computed(() => {
  if (props.data === null) return 'null'
  if (props.data === undefined) return 'undefined'
  if (typeof props.data === 'string') return `"${props.data}"`
  if (typeof props.data === 'boolean') return String(props.data)
  if (typeof props.data === 'number') return String(props.data)
  return String(props.data)
})

const valueClass = computed(() => {
  if (props.data === null) return 'value-null'
  if (props.data === undefined) return 'value-undefined'
  if (typeof props.data === 'string') return 'value-string'
  if (typeof props.data === 'boolean') return 'value-boolean'
  if (typeof props.data === 'number') return 'value-number'
  return 'value-default'
})

// 获取值的预览文本
function getValuePreview(value: any): string {
  if (value === null) return 'null'
  if (value === undefined) return 'undefined'
  if (typeof value === 'string') {
    return value.length > 20 ? `"${value.substring(0, 20)}..."` : `"${value}"`
  }
  if (typeof value === 'boolean') return String(value)
  if (typeof value === 'number') return String(value)
  if (Array.isArray(value)) return `Array(${value.length})`
  if (typeof value === 'object') return `Object(${Object.keys(value).length})`
  return String(value)
}

// 切换展开/收起
function toggle() {
  emit('toggle', props.path)
}

// 复制值到剪贴板
async function copyValue() {
  try {
    let text = props.data
    if (typeof props.data === 'string') {
      text = props.data // 复制不含引号的原始字符串
    } else {
      text = String(props.data)
    }
    await navigator.clipboard.writeText(text)
  } catch (err) {
    console.error('复制失败:', err)
  }
}
</script>

<style scoped>
.json-node {
  @apply leading-relaxed;
}

.node-line {
  @apply flex items-center gap-1;
}

.toggle-btn {
  @apply p-0.5 hover:bg-gray-200 rounded transition-colors flex-shrink-0;
}

.toggle-placeholder {
  @apply inline-block w-4;
}

.node-key {
  @apply text-purple-600 font-medium;
}

.node-bracket {
  @apply text-gray-600 font-bold;
}

.node-preview {
  @apply text-gray-500 text-xs ml-1;
}

.node-count {
  @apply text-gray-400 text-xs ml-2 italic;
}

.node-children {
  @apply ml-4 border-l-2 border-gray-200 pl-2;
}

.node-child {
  @apply my-0.5;
}

/* 值类型样式 */
.value-string {
  @apply text-green-600;
}

.value-number {
  @apply text-blue-600;
}

.value-boolean {
  @apply text-orange-600 font-medium;
}

.value-null,
.value-undefined {
  @apply text-gray-400 italic;
}

.value-default {
  @apply text-gray-700;
}

.selectable {
  @apply cursor-pointer select-text hover:bg-yellow-100 hover:px-1 hover:-mx-1 rounded transition-all;
}
</style>
