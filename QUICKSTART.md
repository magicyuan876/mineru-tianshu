# MinerU Tianshu 快速启动指南

## 🚀 快速开始（5分钟搞定）

### 步骤 1: 启动后端

```bash
# 进入后端目录
cd backend

# 安装依赖（首次运行）
pip install -r requirements.txt

# 一键启动
python start_all.py
```

等待看到以下提示:
```
✅ All Services Started Successfully!
📚 Quick Start:
   • API Documentation: http://localhost:8000/docs
```

### 步骤 2: 启动前端

**打开新的终端窗口:**

```bash
# 进入前端目录
cd frontend

# 安装依赖（首次运行）
npm install

# 启动开发服务器
npm run dev
```

等待看到:
```
  ➜  Local:   http://localhost:3000/
```

### 步骤 3: 访问应用

打开浏览器访问: **http://localhost:3000**

## ✨ 第一次使用

1. **提交任务**
   - 点击顶部导航 "提交任务"
   - 拖拽或点击上传文件
   - 点击 "提交任务"

2. **查看结果**
   - 点击 "仪表盘" 查看任务状态
   - 点击任务的 "查看" 按钮进入详情
   - 任务完成后可以预览和下载 Markdown

## 🎯 常用配置

### GPU 模式（推荐）

```bash
cd backend
python start_all.py --accelerator cuda --workers-per-device 2
```

### CPU 模式（无 GPU 或测试）

```bash
cd backend
python start_all.py --accelerator cpu
```

### 指定 GPU 设备

```bash
cd backend
python start_all.py --devices 0,1
```

## 🔧 故障排查

### 后端启动失败

**检查 Python 版本:**
```bash
python --version  # 需要 3.8+
```

**检查依赖安装:**
```bash
cd backend
pip install -r requirements.txt
```

### 前端启动失败

**检查 Node.js 版本:**
```bash
node --version  # 需要 18+
```

**清理并重新安装:**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### 前端无法连接后端

**确认后端已启动:**
```bash
curl http://localhost:8000/api/v1/health
```

应该返回:
```json
{"status":"healthy","timestamp":"..."}
```

### Worker 未运行

**查看后端日志:**
查找类似以下的日志:
```
✅ LitServe Workers started (PID: xxxxx)
```

如果没有,尝试单独启动 worker:
```bash
cd backend
python litserve_worker.py
```

## 📱 支持的文件格式

- ✅ PDF
- ✅ 图片 (PNG, JPG, JPEG, BMP, TIFF, WEBP)
- ✅ Word (DOCX, DOC)
- ✅ Excel (XLSX, XLS)
- ✅ PowerPoint (PPTX, PPT)
- ✅ HTML
- ✅ Markdown
- ✅ 文本文件

## 🔗 有用的链接

- **前端**: http://localhost:3000
- **后端 API 文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/api/v1/health
- **队列统计**: http://localhost:8000/api/v1/queue/stats

## 💡 小贴士

1. **首次使用建议上传小文件测试** (几 MB 的 PDF)
2. **GPU 模式下解析速度更快**
3. **批量上传时建议设置不同的优先级**
4. **任务失败时查看详情页的错误信息**
5. **队列管理页面可以监控系统运行状态**

## 📚 进阶使用

查看完整文档:
- [根 README.md](README.md) - 项目总览
- [frontend/README.md](frontend/README.md) - 前端文档
- [backend/README.md](backend/README.md) - 后端文档

## 🎉 开始使用吧!

现在你可以开始使用 MinerU Tianshu 解析文档了!

