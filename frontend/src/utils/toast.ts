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

  // 创建 toast 容器
  const toast = document.createElement('div')

  // 设置颜色
  const colors = getToastColors(type)

  // 使用 setAttribute 和直接设置属性
  Object.assign(toast.style, {
    position: 'fixed',
    top: '1rem',
    right: '1rem',
    zIndex: '9999',
    minWidth: '250px',
    maxWidth: '500px',
    padding: '1rem 1.5rem',
    borderRadius: '0.5rem',
    boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
    fontSize: '14px',
    fontWeight: '500',
    lineHeight: '1.5',
    transition: 'all 0.3s ease',
    transform: 'translateX(0)',
    opacity: '1',
    backgroundColor: colors.bg,
    color: colors.text,
    fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
  })

  // 添加图标
  const icon = document.createElement('span')
  icon.innerHTML = getToastIcon(type)
  Object.assign(icon.style, {
    flexShrink: '0',
    width: '20px',
    height: '20px',
    color: colors.text,
  })

  // 添加文字 - 使用 innerText 而不是 textContent
  const messageEl = document.createElement('span')
  messageEl.innerText = message
  Object.assign(messageEl.style, {
    flex: '1',
    wordBreak: 'break-word',
    color: colors.text,
    fontSize: '14px',
    lineHeight: '1.5',
    fontWeight: '500',
    display: 'inline-block',
  })

  toast.appendChild(icon)
  toast.appendChild(messageEl)

  // 添加到页面
  document.body.appendChild(toast)

  // 添加调试信息
  console.log('Toast created:', {
    message,
    type,
    messageElement: messageEl,
    textContent: messageEl.innerText,
    computedStyle: window.getComputedStyle(messageEl).color
  })

  // 自动移除
  setTimeout(() => {
    toast.style.opacity = '0'
    toast.style.transform = 'translateX(100%)'
    setTimeout(() => {
      if (toast.parentNode) {
        document.body.removeChild(toast)
      }
    }, 300)
  }, duration)
}

function getToastColors(type: ToastType): { bg: string; text: string } {
  const colorMap = {
    success: { bg: '#10b981', text: '#ffffff' },
    error: { bg: '#ef4444', text: '#ffffff' },
    warning: { bg: '#f59e0b', text: '#ffffff' },
    info: { bg: '#3b82f6', text: '#ffffff' },
  }
  return colorMap[type]
}

function getToastIcon(type: ToastType): string {
  const icons = {
    success: '<svg viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/></svg>',
    error: '<svg viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/></svg>',
    warning: '<svg viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/></svg>',
    info: '<svg viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/></svg>',
  }
  return icons[type]
}

// 便捷方法
export const toast = {
  success: (message: string) => showToast({ message, type: 'success' }),
  error: (message: string) => showToast({ message, type: 'error' }),
  warning: (message: string) => showToast({ message, type: 'warning' }),
  info: (message: string) => showToast({ message, type: 'info' }),
}
