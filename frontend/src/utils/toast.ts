/**
 * 简单的 Toast 通知工具
 */

export type ToastType = 'success' | 'error' | 'warning' | 'info'

interface ToastOptions {
  message: string
  type?: ToastType
  duration?: number
}

export function showToast(options: ToastOptions) {
  const { message, type = 'info', duration = 3000 } = options
  
  // 创建 toast 元素
  const toast = document.createElement('div')
  toast.className = `fixed top-4 right-4 z-50 px-6 py-3 rounded-lg shadow-lg text-white transform transition-all duration-300 translate-x-0 ${getToastClass(type)}`
  toast.textContent = message
  
  // 添加到页面
  document.body.appendChild(toast)
  
  // 自动移除
  setTimeout(() => {
    toast.classList.add('opacity-0', 'translate-x-full')
    setTimeout(() => {
      document.body.removeChild(toast)
    }, 300)
  }, duration)
}

function getToastClass(type: ToastType): string {
  const classes = {
    success: 'bg-green-600',
    error: 'bg-red-600',
    warning: 'bg-yellow-600',
    info: 'bg-blue-600',
  }
  return classes[type]
}

// 便捷方法
export const toast = {
  success: (message: string) => showToast({ message, type: 'success' }),
  error: (message: string) => showToast({ message, type: 'error' }),
  warning: (message: string) => showToast({ message, type: 'warning' }),
  info: (message: string) => showToast({ message, type: 'info' }),
}

