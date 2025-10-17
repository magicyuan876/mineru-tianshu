# MinerU Tianshu (天枢)

> 天枢 - 企业级多GPU文档解析服务  
> 结合 Vue 3 前端 + FastAPI 后端 + LitServe GPU负载均衡的全栈解决方案

## 🌟 项目简介

MinerU Tianshu 是一个企业级的文档解析服务,提供:
- **现代化 Web 界面**: Vue 3 + TypeScript + TailwindCSS 构建的美观易用的管理界面
- **强大的解析能力**: 基于 MinerU 的 PDF/图片解析 + MarkItDown 的 Office 文档解析
- **高性能架构**: FastAPI + LitServe 实现的 GPU 负载均衡和并发处理
- **完善的任务管理**: 支持任务队列、优先级、状态追踪、自动重试等企业级功能

## 📸 功能展示

### 主要功能
- ✅ **仪表盘**: 实时监控队列统计和最近任务
- ✅ **任务提交**: 文件拖拽上传,支持批量处理和高级配置
- ✅ **任务详情**: 实时状态追踪,Markdown 预览,自动轮询更新
- ✅ **任务列表**: 筛选、搜索、分页、批量操作
- ✅ **队列管理**: 系统监控,重置超时任务,清理旧文件

### 支持的文件格式
- 📄 **PDF 和图片** - 使用 MinerU 解析（GPU 加速）
- 📊 **Office 文档** - Word、Excel、PowerPoint（使用 MarkItDown）
- 🌐 **网页和文本** - HTML、Markdown、TXT、CSV 等

## 🏗️ 项目结构

```
mineru-server/
├── frontend/               # Vue 3 前端项目
│   ├── src/
│   │   ├── api/           # API 接口层
│   │   ├── components/    # 通用组件
│   │   ├── layouts/       # 布局组件
│   │   ├── views/         # 页面组件
│   │   ├── stores/        # Pinia 状态管理
│   │   ├── router/        # Vue Router
│   │   └── utils/         # 工具函数
│   ├── package.json
│   ├── vite.config.ts
│   └── README.md          # 前端文档
│
├── backend/                # Python 后端项目
│   ├── api_server.py      # FastAPI 服务器
│   ├── task_db.py         # 数据库管理
│   ├── litserve_worker.py # Worker Pool
│   ├── task_scheduler.py  # 任务调度器
│   ├── start_all.py       # 启动脚本
│   ├── requirements.txt
│   └── README.md          # 后端文档
│
└── README.md              # 本文件
```

## 🚀 快速开始

### 前置要求

- **Node.js** 18+ (前端)
- **Python** 3.8+ (后端)
- **CUDA** (可选,用于 GPU 加速)

### 1. 启动后端服务

```bash
# 进入后端目录
cd backend

# 安装依赖
pip install -r requirements.txt

# 一键启动所有服务
python start_all.py
```

后端服务将在以下端口启动:
- API Server: http://localhost:8000
- API 文档: http://localhost:8000/docs
- Worker Pool: http://localhost:9000

### 2. 启动前端服务

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端服务将在 http://localhost:3000 启动

### 3. 访问应用

打开浏览器访问 http://localhost:3000

## 📖 使用指南

### 提交任务

1. 点击顶部导航栏的 "提交任务"
2. 拖拽或点击上传文件（支持批量上传）
3. 配置解析选项：
   - 选择处理后端 (pipeline/vlm-transformers/vlm-vllm-engine)
   - 设置文档语言
   - 启用公式/表格识别
   - 设置任务优先级
4. 点击 "提交任务"

### 查看任务状态

1. 在仪表盘或任务列表中找到你的任务
2. 点击 "查看" 进入任务详情页
3. 页面会自动轮询更新任务状态
4. 任务完成后可以：
   - 预览 Markdown 结果
   - 下载 Markdown 文件
   - 查看处理时长和错误信息（如果失败）

### 管理队列

1. 点击顶部导航栏的 "队列管理"
2. 查看实时队列统计
3. 执行管理操作：
   - 重置超时任务
   - 清理旧任务文件
   - 系统健康检查

## 🎯 核心特性

### 前端特性
- **现代化 UI**: 基于 TailwindCSS 的美观界面
- **响应式设计**: 完美适配桌面端和移动端
- **实时更新**: 自动刷新队列统计和任务状态
- **批量操作**: 支持批量文件上传和任务管理
- **Markdown 预览**: 实时渲染解析结果,支持代码高亮

### 后端特性
- **Worker 主动拉取**: 0.5秒响应速度,无需调度器触发
- **并发安全**: 原子操作防止任务重复,支持多Worker并发
- **GPU 负载均衡**: LitServe 自动调度,避免显存冲突
- **多GPU隔离**: 每个进程只使用分配的GPU
- **自动清理**: 定期清理旧结果文件,保留数据库记录
- **双解析器**: PDF/图片用 MinerU, Office等用 MarkItDown

## ⚙️ 配置说明

### 后端配置

```bash
# 自定义启动配置
python backend/start_all.py \
  --output-dir /data/output \
  --api-port 8000 \
  --worker-port 9000 \
  --accelerator cuda \
  --devices 0,1 \
  --workers-per-device 2
```

详见 [backend/README.md](backend/README.md)

### 前端配置

开发环境修改 `frontend/.env.development`:
```
VITE_API_BASE_URL=http://localhost:8000
```

生产环境修改 `frontend/.env.production`:
```
VITE_API_BASE_URL=/api
```

详见 [frontend/README.md](frontend/README.md)

## 🚢 生产部署

### 前端构建

```bash
cd frontend
npm run build
```

构建产物在 `frontend/dist/` 目录。

### Nginx 配置示例

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    root /path/to/frontend/dist;
    index index.html;

    # 前端路由
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API 代理到后端
    location /api/ {
        proxy_pass http://localhost:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### 后端部署

使用 systemd 或 supervisor 管理后端服务:

```bash
# 启动后端
cd backend
python start_all.py --api-port 8000 --worker-port 9000
```

## 📚 技术栈

### 前端
- Vue 3 (Composition API)
- TypeScript
- Vite
- TailwindCSS
- Vue Router
- Pinia
- Axios
- Marked (Markdown 渲染)
- Highlight.js (代码高亮)
- Lucide Vue (图标)

### 后端
- FastAPI
- LitServe
- MinerU
- MarkItDown
- SQLite
- Loguru
- MinIO (可选)

## 🔧 故障排查

### 前端无法连接后端

检查后端是否正常运行:
```bash
curl http://localhost:8000/api/v1/health
```

检查前端代理配置:
```typescript
// frontend/vite.config.ts
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    }
  }
}
```

### Worker 无法启动

检查 GPU 可用性:
```bash
nvidia-smi
```

检查 Python 依赖:
```bash
pip list | grep -E "(mineru|litserve|torch)"
```

更多故障排查,请参考:
- [前端故障排查](frontend/README.md)
- [后端故障排查](backend/README.md)

## 📄 API 文档

启动后端后,访问 http://localhost:8000/docs 查看完整的 API 文档。

主要 API 端点:
- `POST /api/v1/tasks/submit` - 提交任务
- `GET /api/v1/tasks/{task_id}` - 查询任务状态
- `DELETE /api/v1/tasks/{task_id}` - 取消任务
- `GET /api/v1/queue/stats` - 获取队列统计
- `GET /api/v1/queue/tasks` - 获取任务列表

## 🤝 贡献

欢迎提交 Issue 和 Pull Request!

## 📜 许可证

本项目采用 [Apache License 2.0](LICENSE) 开源协议。

```
Copyright 2024 MinerU Tianshu Contributors

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```

---

**天枢 (Tianshu)** - 企业级多 GPU 文档解析服务 ⚡️

*北斗第一星，寓意核心调度能力*
