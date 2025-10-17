# MinerU Tianshu 前端

Vue 3 + TypeScript + Vite + TailwindCSS 构建的现代化文档解析管理界面。

## 🚀 快速开始

### 安装依赖

```bash
npm install
```

### 开发模式

```bash
npm run dev
```

访问 http://localhost:3000

### 生产构建

```bash
npm run build
```

构建产物在 `dist/` 目录。

### 预览构建结果

```bash
npm run preview
```

## 📁 项目结构

```
frontend/
├── src/
│   ├── api/                 # API 接口层
│   │   ├── client.ts       # Axios 客户端配置
│   │   ├── taskApi.ts      # 任务相关接口
│   │   ├── queueApi.ts     # 队列管理接口
│   │   └── types.ts        # TypeScript 类型定义
│   ├── components/          # 通用组件
│   │   ├── FileUploader.vue      # 文件上传组件
│   │   ├── StatusBadge.vue       # 状态徽章
│   │   ├── StatCard.vue          # 统计卡片
│   │   ├── MarkdownViewer.vue    # Markdown 查看器
│   │   ├── LoadingSpinner.vue    # 加载动画
│   │   └── ConfirmDialog.vue     # 确认对话框
│   ├── layouts/             # 布局组件
│   │   └── AppLayout.vue   # 主布局
│   ├── views/               # 页面组件
│   │   ├── Dashboard.vue         # 仪表盘
│   │   ├── TaskSubmit.vue        # 提交任务
│   │   ├── TaskDetail.vue        # 任务详情
│   │   ├── TaskList.vue          # 任务列表
│   │   └── QueueManagement.vue   # 队列管理
│   ├── stores/              # Pinia 状态管理
│   │   ├── taskStore.ts    # 任务状态
│   │   └── queueStore.ts   # 队列状态
│   ├── router/              # Vue Router 配置
│   │   └── index.ts
│   ├── utils/               # 工具函数
│   │   ├── format.ts       # 格式化工具
│   │   └── toast.ts        # Toast 通知
│   ├── App.vue              # 根组件
│   ├── main.ts              # 入口文件
│   └── style.css            # 全局样式
├── public/                  # 静态资源
├── index.html               # HTML 模板
├── vite.config.ts           # Vite 配置
├── tailwind.config.js       # TailwindCSS 配置
├── tsconfig.json            # TypeScript 配置
└── package.json             # 项目依赖

```

## 🎨 技术栈

- **框架**: Vue 3 (Composition API)
- **语言**: TypeScript
- **构建工具**: Vite
- **样式**: TailwindCSS + @tailwindcss/typography
- **路由**: Vue Router
- **状态管理**: Pinia
- **HTTP 客户端**: Axios
- **Markdown 渲染**: Marked
- **代码高亮**: Highlight.js
- **图标**: Lucide Vue
- **时间处理**: Day.js

## 🌟 主要功能

### 仪表盘 (Dashboard)
- 实时队列统计
- 最近任务列表
- 快捷操作入口

### 任务提交 (TaskSubmit)
- 文件拖拽上传
- 批量文件上传
- 高级配置选项
  - Backend 选择 (pipeline/vlm-transformers/vlm-vllm-engine)
  - 语言选择 (中文/英文/韩文/日文)
  - 解析方法 (auto/txt/ocr)
  - 公式识别开关
  - 表格识别开关
  - 优先级设置
- 上传进度显示

### 任务详情 (TaskDetail)
- 任务基本信息展示
- 状态时间轴
- Markdown 结果预览
- 自动轮询更新 (未完成任务)
- 下载 Markdown 文件
- 取消任务

### 任务列表 (TaskList)
- 状态筛选 (pending/processing/completed/failed/cancelled)
- Backend 类型筛选
- 文件名搜索
- 分页展示
- 批量操作 (批量取消)
- 实时刷新

### 队列管理 (QueueManagement)
- 队列统计展示
- 历史统计 (已完成/失败)
- 管理操作
  - 重置超时任务
  - 清理旧任务文件
  - 系统健康检查
- 操作日志

## 🔧 配置说明

### 环境变量

开发环境 (`.env.development`):
```
VITE_API_BASE_URL=http://localhost:8000
```

生产环境 (`.env.production`):
```
VITE_API_BASE_URL=/api
```

### 代理配置

开发环境下,Vite 会自动代理 `/api` 请求到后端服务 (localhost:8000)。

生产环境需要 Nginx 等反向代理配置,将 `/api` 请求转发到后端。

## 📝 开发规范

### 组件命名
- 使用 PascalCase 命名组件文件
- 组件名使用多个单词 (避免与 HTML 标签冲突)

### 样式规范
- 优先使用 TailwindCSS 工具类
- 自定义样式使用 `<style scoped>`
- 避免全局样式污染

### TypeScript
- 所有 API 接口使用明确的类型定义
- Props 使用 TypeScript 类型注解
- 避免使用 `any` 类型

### 状态管理
- 组件内部状态使用 `ref`/`reactive`
- 跨组件共享状态使用 Pinia Store
- Store 按功能模块拆分

## 🚢 部署

### 构建

```bash
npm run build
```

### Nginx 配置示例

```nginx
server {
    listen 80;
    server_name your-domain.com;

    root /path/to/frontend/dist;
    index index.html;

    # 前端路由
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API 代理
    location /api/ {
        proxy_pass http://localhost:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 📄 许可证

遵循 MinerU 主项目许可证

