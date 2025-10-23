<template>
  <div class="json-viewer">
    <!-- 工具栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <button
          @click="expandAll"
          class="toolbar-btn"
          title="展开所有"
        >
          <ChevronDown class="w-4 h-4" />
          <span>展开所有</span>
        </button>
        <button
          @click="collapseAll"
          class="toolbar-btn"
          title="收起所有"
        >
          <ChevronRight class="w-4 h-4" />
          <span>收起所有</span>
        </button>
        <button
          @click="expandLevel(2)"
          class="toolbar-btn"
          title="展开到第2层"
        >
          <Layers class="w-4 h-4" />
          <span>展开2层</span>
        </button>
        <div class="toolbar-divider"></div>
        <button
          @click="copyToClipboard"
          class="toolbar-btn"
          :class="{ 'text-green-600': copied }"
          title="复制JSON"
        >
          <Check v-if="copied" class="w-4 h-4" />
          <Copy v-else class="w-4 h-4" />
          <span>{{ copied ? '已复制' : '复制' }}</span>
        </button>
        <button
          @click="downloadJson"
          class="toolbar-btn"
          title="下载JSON文件"
        >
          <Download class="w-4 h-4" />
          <span>下载</span>
        </button>
        <div class="toolbar-divider"></div>
        <button
          @click="toggleRawView"
          class="toolbar-btn"
          :class="{ 'bg-primary-100 text-primary-700': showRaw }"
          title="切换原始视图"
        >
          <Code class="w-4 h-4" />
          <span>{{ showRaw ? '树形' : '原始' }}</span>
        </button>
      </div>
      <div class="toolbar-right">
        <span class="text-xs text-gray-500">
          {{ objectInfo }}
        </span>
      </div>
    </div>

    <!-- JSON内容 -->
    <div class="json-content">
      <!-- 树形视图 -->
      <div v-if="!showRaw" class="json-tree">
        <JsonNode
          :data="jsonData"
          :path="[]"
          :expanded-paths="expandedPaths"
          @toggle="togglePath"
        />
      </div>
      
      <!-- 原始视图 -->
      <div v-else class="json-raw">
        <pre class="text-sm text-gray-800 whitespace-pre-wrap font-mono">{{ JSON.stringify(jsonData, null, 2) }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ChevronDown, ChevronRight, Copy, Check, Download, Layers, Code } from 'lucide-vue-next'
import JsonNode from './JsonNode.vue'

const props = defineProps<{
  data: any
  fileName?: string
}>()

const expandedPaths = ref<Set<string>>(new Set())
const copied = ref(false)
const showRaw = ref(false)

// 解析JSON数据
const jsonData = computed(() => {
  if (typeof props.data === 'string') {
    try {
      return JSON.parse(props.data)
    } catch (e) {
      return props.data
    }
  }
  return props.data
})

// 对象信息
const objectInfo = computed(() => {
  const data = jsonData.value
  if (Array.isArray(data)) {
    return `数组 [${data.length} 项]`
  } else if (typeof data === 'object' && data !== null) {
    const keys = Object.keys(data).length
    return `对象 {${keys} 个键}`
  }
  return typeof data
})

// 获取所有路径
function getAllPaths(obj: any, currentPath: string[] = []): string[] {
  const paths: string[] = []
  
  if (Array.isArray(obj)) {
    paths.push(currentPath.join('.'))
    obj.forEach((item, index) => {
      const newPath = [...currentPath, String(index)]
      if (typeof item === 'object' && item !== null) {
        paths.push(...getAllPaths(item, newPath))
      }
    })
  } else if (typeof obj === 'object' && obj !== null) {
    paths.push(currentPath.join('.'))
    Object.keys(obj).forEach(key => {
      const newPath = [...currentPath, key]
      if (typeof obj[key] === 'object' && obj[key] !== null) {
        paths.push(...getAllPaths(obj[key], newPath))
      }
    })
  }
  
  return paths
}

// 展开所有
function expandAll() {
  const allPaths = getAllPaths(jsonData.value)
  expandedPaths.value = new Set(allPaths)
}

// 收起所有
function collapseAll() {
  expandedPaths.value = new Set()
}

// 展开到指定层级
function expandLevel(level: number) {
  const paths: string[] = []
  
  function collectPaths(obj: any, currentPath: string[] = [], currentLevel: number = 0) {
    if (currentLevel >= level) return
    
    if (Array.isArray(obj)) {
      paths.push(currentPath.join('.'))
      obj.forEach((item, index) => {
        if (typeof item === 'object' && item !== null) {
          collectPaths(item, [...currentPath, String(index)], currentLevel + 1)
        }
      })
    } else if (typeof obj === 'object' && obj !== null) {
      paths.push(currentPath.join('.'))
      Object.keys(obj).forEach(key => {
        if (typeof obj[key] === 'object' && obj[key] !== null) {
          collectPaths(obj[key], [...currentPath, key], currentLevel + 1)
        }
      })
    }
  }
  
  collectPaths(jsonData.value)
  expandedPaths.value = new Set(paths)
}

// 切换路径展开状态
function togglePath(path: string[]) {
  const pathStr = path.join('.')
  if (expandedPaths.value.has(pathStr)) {
    expandedPaths.value.delete(pathStr)
  } else {
    expandedPaths.value.add(pathStr)
  }
}

// 切换原始视图
function toggleRawView() {
  showRaw.value = !showRaw.value
}

// 复制到剪贴板
async function copyToClipboard() {
  try {
    const jsonString = JSON.stringify(jsonData.value, null, 2)
    await navigator.clipboard.writeText(jsonString)
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch (err) {
    console.error('复制失败:', err)
    alert('复制失败，请手动选择文本复制')
  }
}

// 下载JSON文件
function downloadJson() {
  const jsonString = JSON.stringify(jsonData.value, null, 2)
  const blob = new Blob([jsonString], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = props.fileName || 'data.json'
  a.click()
  URL.revokeObjectURL(url)
}

// 初始化时展开第2层
onMounted(() => {
  if (typeof jsonData.value === 'object' && jsonData.value !== null) {
    expandLevel(2)
  }
})
</script>

<style scoped>
.json-viewer {
  @apply bg-gray-50 rounded-lg border border-gray-200 overflow-hidden;
}

.toolbar {
  @apply flex items-center justify-between px-4 py-2 bg-white border-b border-gray-200;
}

.toolbar-left {
  @apply flex items-center gap-2;
}

.toolbar-right {
  @apply flex items-center gap-2;
}

.toolbar-btn {
  @apply flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-100 rounded transition-colors;
}

.toolbar-btn:active {
  @apply bg-gray-200;
}

.toolbar-divider {
  @apply w-px h-5 bg-gray-300;
}

.json-content {
  @apply p-4 overflow-x-auto;
  max-height: 600px;
  overflow-y: auto;
}

.json-tree {
  @apply font-mono text-sm;
}

.json-raw {
  @apply font-mono text-sm;
}
</style>

