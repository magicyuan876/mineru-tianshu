# MinerU Tianshu 后端

企业级多 GPU 文档解析服务后端,基于 FastAPI + LitServe 构建。

## 🚀 快速开始

### 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 启动服务

**一键启动所有服务（推荐）:**

```bash
python start_all.py
```

**自定义配置启动:**

```bash
python start_all.py --workers-per-device 2 --devices 0,1
```

**分别启动各服务:**

```bash
# 1. 启动 API Server
python api_server.py

# 2. 启动 LitServe Workers
python litserve_worker.py --workers-per-device 2

# 3. 启动 Task Scheduler (可选)
python task_scheduler.py --enable-scheduler
```

## 📁 项目结构

```
backend/
├── api_server.py           # FastAPI API 服务器
├── task_db.py              # SQLite 数据库管理
├── litserve_worker.py      # LitServe Worker Pool
├── task_scheduler.py       # 任务调度器 (可选)
├── start_all.py            # 统一启动脚本
├── client_example.py       # Python 客户端示例
├── requirements.txt        # Python 依赖
└── README.md               # 后端文档
```

## 📡 API 接口

完整 API 文档: http://localhost:8000/docs

### 任务管理

#### 提交任务
```
POST /api/v1/tasks/submit

参数:
  - file: 文件 (必需)
  - backend: pipeline | vlm-transformers | vlm-vllm-engine (默认: pipeline)
  - lang: ch | en | korean | japan (默认: ch)
  - method: auto | txt | ocr (默认: auto)
  - formula_enable: boolean (默认: true)
  - table_enable: boolean (默认: true)
  - priority: 0-100 (默认: 0)

返回:
  {
    "success": true,
    "task_id": "uuid",
    "status": "pending",
    "message": "Task submitted successfully",
    "file_name": "document.pdf",
    "created_at": "2024-01-01T00:00:00"
  }
```

#### 查询任务状态
```
GET /api/v1/tasks/{task_id}?upload_images=false

返回:
  {
    "success": true,
    "task_id": "uuid",
    "status": "completed",
    "file_name": "document.pdf",
    "backend": "pipeline",
    "priority": 0,
    "error_message": null,
    "created_at": "2024-01-01T00:00:00",
    "started_at": "2024-01-01T00:00:10",
    "completed_at": "2024-01-01T00:01:00",
    "worker_id": "tianshu-worker-1",
    "retry_count": 0,
    "data": {
      "markdown_file": "document.md",
      "content": "# Document\n\n...",
      "images_uploaded": false,
      "has_images": true
    }
  }
```

#### 取消任务
```
DELETE /api/v1/tasks/{task_id}

返回:
  {
    "success": true,
    "message": "Task cancelled successfully"
  }
```

#### 获取任务列表
```
GET /api/v1/queue/tasks?status=pending&limit=100

返回:
  {
    "success": true,
    "count": 10,
    "tasks": [...]
  }
```

### 队列管理

#### 获取队列统计
```
GET /api/v1/queue/stats

返回:
  {
    "success": true,
    "stats": {
      "pending": 5,
      "processing": 2,
      "completed": 100,
      "failed": 3,
      "cancelled": 1
    },
    "total": 111,
    "timestamp": "2024-01-01T00:00:00"
  }
```

#### 重置超时任务
```
POST /api/v1/admin/reset-stale?timeout_minutes=60

返回:
  {
    "success": true,
    "reset_count": 2,
    "message": "Reset tasks processing for more than 60 minutes"
  }
```

#### 清理旧任务
```
POST /api/v1/admin/cleanup?days=7

返回:
  {
    "success": true,
    "deleted_count": 50,
    "message": "Cleaned up tasks older than 7 days"
  }
```

#### 健康检查
```
GET /api/v1/health

返回:
  {
    "status": "healthy",
    "timestamp": "2024-01-01T00:00:00",
    "database": "connected",
    "queue_stats": {...}
  }
```

## 🔧 配置说明

### 启动参数

```bash
python start_all.py [选项]

选项:
  --output-dir PATH                 输出目录 (默认: /tmp/mineru_tianshu_output)
  --api-port PORT                   API端口 (默认: 8000)
  --worker-port PORT                Worker端口 (默认: 9000)
  --accelerator TYPE                加速器类型: auto/cuda/cpu/mps (默认: auto)
  --workers-per-device N            每个GPU的worker数 (默认: 1)
  --devices DEVICES                 使用的GPU设备 (默认: auto)
  --poll-interval SECONDS           Worker拉取任务间隔 (默认: 0.5秒)
  --enable-scheduler                启用可选的任务调度器
  --monitor-interval SECONDS        调度器监控间隔 (默认: 300秒)
  --cleanup-old-files-days N        清理N天前的结果文件 (默认: 7天)
```

### 环境变量

```bash
# API Server 端口
export API_PORT=8000

# MinIO 配置 (可选)
export MINIO_ENDPOINT="your-endpoint.com"
export MINIO_ACCESS_KEY="your-access-key"
export MINIO_SECRET_KEY="your-secret-key"
export MINIO_BUCKET="your-bucket"

# MinerU 显存配置
export MINERU_VIRTUAL_VRAM_SIZE=6
```

### 数据库

项目使用 SQLite 数据库 (`mineru_tianshu.db`),自动创建,无需手动配置。

## 🎯 核心功能

### Worker 主动拉取模式
- Workers 持续循环拉取任务,无需调度器触发
- 默认 0.5 秒拉取间隔,响应速度极快
- 空闲时自动休眠,不占用 CPU 资源

### 并发安全
- 使用 `BEGIN IMMEDIATE` 和原子操作
- 防止任务重复处理
- 支持多 Worker 并发拉取

### 双解析器支持
- **MinerU**: 处理 PDF 和图片 (GPU 加速)
- **MarkItDown**: 处理 Office、HTML、文本等 (快速处理)

### 自动清理
- 自动清理旧结果文件 (默认 7 天)
- 保留数据库记录供查询
- 可配置清理周期或禁用

## 🐍 Python 客户端示例

```python
from client_example import TianshuClient
import asyncio

async def main():
    client = TianshuClient('http://localhost:8000')
    
    async with aiohttp.ClientSession() as session:
        # 提交任务
        result = await client.submit_task(
            session,
            file_path='document.pdf',
            backend='pipeline',
            lang='ch',
            formula_enable=True,
            table_enable=True
        )
        
        task_id = result['task_id']
        
        # 等待完成
        final_status = await client.wait_for_task(session, task_id)
        
        print(f"Task completed: {final_status}")

if __name__ == '__main__':
    asyncio.run(main())
```

## 🔍 故障排查

### Worker 无法启动

检查 GPU:
```bash
nvidia-smi
```

检查依赖:
```bash
pip list | grep -E "(mineru|litserve|torch)"
```

### 任务一直 pending

检查 Worker 是否运行:
```bash
# Windows
tasklist | findstr python

# Linux/Mac
ps aux | grep litserve_worker
```

检查 Worker 健康状态:
```bash
curl -X POST http://localhost:9000/predict \
  -H "Content-Type: application/json" \
  -d '{"action":"health"}'
```

### 显存不足

减少 worker 数量:
```bash
python start_all.py --workers-per-device 1
```

设置显存限制:
```bash
export MINERU_VIRTUAL_VRAM_SIZE=6
python start_all.py
```

## 📄 许可证

遵循 MinerU 主项目许可证

