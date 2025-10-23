<div align="center">

# MinerU Tianshu 天枢

**企业级多GPU文档解析服务**

结合 Vue 3 前端 + FastAPI 后端 + LitServe GPU负载均衡 + MCP协议支持

<p>
  <a href="https://github.com/magicyuan876/mineru-tianshu/stargazers">
    <img src="https://img.shields.io/github/stars/magicyuan876/mineru-tianshu?style=for-the-badge&logo=github&color=yellow" alt="Stars"/>
  </a>
  <a href="https://github.com/magicyuan876/mineru-tianshu/network/members">
    <img src="https://img.shields.io/github/forks/magicyuan876/mineru-tianshu?style=for-the-badge&logo=github&color=blue" alt="Forks"/>
  </a>
  <a href="https://github.com/magicyuan876/mineru-tianshu/blob/main/LICENSE">
    <img src="https://img.shields.io/badge/license-Apache%202.0-green?style=for-the-badge" alt="License"/>
  </a>
</p>

<p>
  <img src="https://img.shields.io/badge/Python-3.8+-blue?logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/Vue-3.x-green?logo=vue.js&logoColor=white" alt="Vue"/>
  <img src="https://img.shields.io/badge/FastAPI-0.115+-teal?logo=fastapi&logoColor=white" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/CUDA-Supported-76B900?logo=nvidia&logoColor=white" alt="CUDA"/>
  <img src="https://img.shields.io/badge/MCP-Supported-orange" alt="MCP"/>
</p>

[![Verified on MseeP](https://mseep.ai/badge.svg)](https://mseep.ai/app/819ff68b-5154-4717-9361-7db787d5a2f8)



[English](./README_EN.md) | 简体中文

<p>
  <a href="https://github.com/magicyuan876/mineru-tianshu">
    <img src="https://img.shields.io/badge/⭐_Star-项目-yellow?style=for-the-badge&logo=github" alt="Star"/>
  </a>
</p>

**如果这个项目对你有帮助，请点击右上角 ⭐ Star 支持一下，这是对开发者最大的鼓励！**

</div>

---

## 🌟 项目简介

MinerU Tianshu 是一个企业级的文档解析服务,提供:
- **现代化 Web 界面**: Vue 3 + TypeScript + TailwindCSS 构建的美观易用的管理界面
- **强大的解析能力**: 支持 MinerU、DeepSeek OCR 的 PDF/图片解析 + MarkItDown 的 Office 文档解析
- **高性能架构**: FastAPI + LitServe 实现的 GPU 负载均衡和并发处理
- **完善的任务管理**: 支持任务队列、优先级、状态追踪、自动重试等企业级功能

## ✨ 核心亮点

<table>
  <tr>
    <td align="center" width="25%">
      <img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Objects/Desktop%20Computer.png" width="60"/><br/>
      <strong>现代化界面</strong><br/>
      <sub>Vue 3 + TypeScript + TailwindCSS</sub>
    </td>
    <td align="center" width="25%">
      <img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Objects/Electric%20Plug.png" width="60"/><br/>
      <strong>GPU 加速</strong><br/>
      <sub>LitServe 负载均衡 + 多GPU隔离</sub>
    </td>
    <td align="center" width="25%">
      <img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Objects/Memo.png" width="60"/><br/>
      <strong>智能解析</strong><br/>
      <sub>PDF/Office/图片转Markdown</sub>
    </td>
    <td align="center" width="25%">
      <img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Objects/Link.png" width="60"/><br/>
      <strong>MCP 协议</strong><br/>
      <sub>AI 助手无缝集成</sub>
    </td>
  </tr>
</table>

## 📸 功能展示

<div align="center">

### 📊 仪表盘 - 实时监控

<img src="./docs/img/dashboard.png" alt="仪表盘" width="80%"/>

*实时监控队列统计和最近任务*

---

### 📤 任务提交 - 文件拖拽上传

<img src="./docs/img/submit.png" alt="任务提交" width="80%"/>

*支持批量处理和高级配置*

---

### ⚙️ 队列管理 - 系统监控

<img src="./docs/img/tasks.png" alt="队列管理" width="80%"/>

*重置超时任务、清理旧文件*

</div>

### 主要功能
- ✅ **仪表盘**: 实时监控队列统计和最近任务
- ✅ **任务提交**: 文件拖拽上传,支持批量处理和高级配置
- ✅ **任务详情**: 实时状态追踪,Markdown 预览,自动轮询更新
- ✅ **任务列表**: 筛选、搜索、分页、批量操作
- ✅ **队列管理**: 系统监控,重置超时任务,清理旧文件
- ✅ **MCP 协议支持**: 通过 Model Context Protocol 支持 AI 助手调用

### 支持的文件格式
- 📄 **PDF 和图片** - 使用 MinerU 或 DeepSeek OCR 解析（GPU 加速）
  - **MinerU**: 完整文档解析，支持表格、公式识别
  - **DeepSeek OCR**: 高精度 OCR 识别，适合需要极致精度的场景
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
│   ├── mcp_server.py      # MCP 协议服务器（可选）
│   ├── start_all.py       # 启动脚本
│   ├── requirements.txt
│   ├── README.md          # 后端文档
│   └── MCP_GUIDE.md       # MCP 详细指南
│
├── mcp_config.example.json # MCP 配置示例
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

# 如果需要启用 MCP 协议支持（用于 AI 助手调用）
python start_all.py --enable-mcp
```

后端服务将在以下端口启动:
- API Server: http://localhost:8000
- API 文档: http://localhost:8000/docs
- Worker Pool: http://localhost:9000
- MCP Server: http://localhost:8001 (如启用)

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
   - 选择处理后端 (pipeline/vlm-transformers/vlm-vllm-engine/deepseek-ocr)
     - **pipeline**: MinerU 标准流程，适合通用文档解析
     - **vlm-transformers**: MinerU VLM 模式（Transformers）
     - **vlm-vllm-engine**: MinerU VLM 模式（vLLM 引擎）
     - **deepseek-ocr**: DeepSeek OCR 引擎，适合高精度 OCR 需求
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
- **多解析引擎**: 
  - **MinerU**: 完整文档解析，支持表格、公式识别
  - **DeepSeek OCR**: 高精度 OCR 识别，支持多种分辨率和提示词类型
  - **MarkItDown**: Office 文档和网页解析
- **MCP 协议**: 支持 AI 助手通过标准协议调用文档解析服务

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

# 启用 MCP 协议支持
python backend/start_all.py --enable-mcp --mcp-port 8001
```

详见 [backend/README.md](backend/README.md)

### MCP 协议集成

MinerU Tianshu 支持 **Model Context Protocol (MCP)**，可以让 AI 助手（如 Claude Desktop）直接调用文档解析服务。

#### 什么是 MCP？

MCP 是 Anthropic 推出的开放协议，让 AI 助手可以直接调用外部工具和服务，无需手动 API 集成。

#### 快速配置

**1. 启动服务（启用 MCP）**

```bash
cd backend
python start_all.py --enable-mcp
```

服务启动后，MCP Server 将在端口 8001 运行。

> **📝 版本兼容性说明**：项目使用 mcp 1.18.0 和 litserve 0.2.16。为确保兼容性，在 `litserve_worker.py` 中已自动应用兼容性补丁，无需手动配置。

**2. 配置 Claude Desktop**

编辑配置文件（根据你的操作系统）：

- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

添加以下内容：

```json
{
  "mcpServers": {
    "mineru-tianshu": {
      "url": "http://localhost:8001/sse",
      "transport": "sse"
    }
  }
}
```

**远程服务器部署：** 将 `localhost` 替换为服务器 IP：

```json
{
  "mcpServers": {
    "mineru-tianshu": {
      "url": "http://your-server-ip:8001/sse",
      "transport": "sse"
    }
  }
}
```

**3. 重启 Claude Desktop**

配置完成后，重启 Claude Desktop 使配置生效。

**4. 开始使用**

在 Claude 对话中，直接使用自然语言：

```
帮我解析这个 PDF 文件：C:/Users/user/document.pdf
```

或：

```
请解析这个在线论文：https://arxiv.org/pdf/2301.12345.pdf
```

Claude 会自动：
1. 读取文件或下载 URL
2. 调用 MinerU Tianshu 解析服务
3. 等待处理完成
4. 返回 Markdown 格式的解析结果

#### 支持的功能

MCP Server 提供 4 个工具：

1. **parse_document** - 解析文档为 Markdown 格式
   - 输入方式：Base64 编码（< 100MB）或 URL
   - 支持格式：PDF、图片、Office 文档、网页和文本

2. **get_task_status** - 查询任务状态和结果

3. **list_tasks** - 列出最近的任务

4. **get_queue_stats** - 获取队列统计信息

#### 技术架构

```
Claude Desktop (客户端)
    ↓ MCP Protocol (SSE)
MCP Server (Port 8001)
    ↓ HTTP REST API
API Server (Port 8000)
    ↓ Task Queue
LitServe Worker Pool (Port 9000)
    ↓ GPU Processing
MinerU / MarkItDown
```

#### 常见问题

**Q: MCP Server 无法启动？**
- 检查端口 8001 是否被占用
- 使用 `--mcp-port` 指定其他端口

**Q: Claude Desktop 无法连接？**
1. 确认 MCP Server 正在运行：访问 `http://localhost:8001/health`
2. 检查配置文件 JSON 格式是否正确
3. 确认端点 URL 是 `/sse` 而不是 `/mcp/sse`
4. 重启 Claude Desktop

**Q: 文件传输失败？**
- 小文件自动使用 Base64 编码
- 大文件（> 100MB）会返回错误
- URL 文件需要公开可访问

**详细文档：** [backend/MCP_GUIDE.md](backend/MCP_GUIDE.md)

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
- DeepSeek OCR
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

## 🙏 鸣谢

本项目基于以下优秀的开源项目构建，在此表示衷心感谢：

- **[MinerU](https://github.com/opendatalab/MinerU)** - 强大的 PDF 和图片文档解析工具
  - 提供了高质量的 GPU 加速文档解析能力
  - 支持公式识别、表格提取等高级特性

- **[DeepSeek OCR](https://huggingface.co/deepseek-ai/DeepSeek-OCR)** - DeepSeek 开源的高精度 OCR 模型
  - 提供了业界领先的 OCR 识别精度
  - 支持多种分辨率和提示词类型
  - 优秀的多模态文档理解能力
  
- **[MarkItDown](https://github.com/microsoft/markitdown)** - Microsoft 开源的文档转换工具
  - 提供了 Office 文档、HTML 等多种格式的解析支持
  - 简单易用的 API 设计

- **[LitServe](https://github.com/Lightning-AI/LitServe)** - 高性能 AI 模型服务框架
  - 提供了优秀的 GPU 负载均衡能力
  - 简化了多 GPU 并发处理的实现

- **[Vue.js](https://vuejs.org/)** - 渐进式 JavaScript 框架
- **[FastAPI](https://fastapi.tiangolo.com/)** - 现代、快速的 Web 框架
- **[TailwindCSS](https://tailwindcss.com/)** - 实用优先的 CSS 框架

同时感谢所有为本项目贡献代码、提出建议的开发者们！

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

## 📝 更新日志

### 2025-10-23

#### ✨ 新增特性
- **集成 PaddleOCR-VL 解析引擎**
  - 新增 `paddleocr-vl` 后端选项，支持 109+ 语言自动识别
  - 文档方向分类、文本图像矫正、版面区域检测等增强功能
  - 原生 PDF 多页文档支持，无需手动转换
  - 模型自动下载和缓存，由 PaddleOCR 统一管理
  - 详细文档请查看 [backend/paddleocr_vl/README.md](backend/paddleocr_vl/README.md)

### 2025-10-22

#### ✨ 新增特性
- **集成 DeepSeek OCR 解析引擎**
  - 新增 `deepseek-ocr` 后端选项，提供高精度 OCR 识别能力
  - 支持多种分辨率配置（tiny/small/base/large/dynamic）
  - 支持多种提示词类型（document/image/free/figure）
  - 自动从 ModelScope/HuggingFace 下载模型（约 5-10GB）
  - 详细文档请查看 [backend/deepseek_ocr/README.md](backend/deepseek_ocr/README.md)

---

<div align="center">

**天枢 (Tianshu)** - 企业级多 GPU 文档解析服务 ⚡️

*北斗第一星，寓意核心调度能力*

<br/>

### 喜欢这个项目？

<a href="https://github.com/magicyuan876/mineru-tianshu/stargazers">
  <img src="https://img.shields.io/github/stars/magicyuan876/mineru-tianshu?style=social" alt="Stars"/>
</a>
<a href="https://github.com/magicyuan876/mineru-tianshu/network/members">
  <img src="https://img.shields.io/github/forks/magicyuan876/mineru-tianshu?style=social" alt="Forks"/>
</a>

**点击 ⭐ Star 支持项目发展，感谢！**

</div>
