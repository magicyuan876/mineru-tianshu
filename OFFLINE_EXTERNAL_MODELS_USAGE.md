# 天枢离线外置模型部署使用说明

本文档用于实际部署操作。详细设计、模型清单和验收背景见
`OFFLINE_EXTERNAL_MODELS_DEPLOYMENT.md`。

核心原则：

- 镜像不包含模型。
- 所有模型提前下载到外置目录。
- 离线服务器只加载镜像、解压模型、挂载模型目录并启动服务。
- 运行时禁止自动联网下载模型，缺少必需模型应直接失败。

## 1. 交付物

执行构建后，`docker-images/` 目录应至少包含：

```text
docker-images/
├── tianshu-backend-amd64.tar.gz
├── tianshu-frontend-amd64.tar.gz
├── rustfs-amd64.tar.gz
├── redis-amd64.tar.gz
├── models-offline.tar.gz
├── docker-compose.yml
├── docker-compose.offline.yml
├── .env.example
└── deploy-offline.sh
```

说明：

- `tianshu-backend-*.tar.gz` 和 `tianshu-frontend-*.tar.gz` 是无模型镜像。
- `models-offline.tar.gz` 是模型包，和镜像分开交付。
- `redis-*.tar.gz` 只有启用 Redis profile 时才必须使用，默认部署可以不启用 Redis。
- 构建脚本会把 `scripts/deploy-offline.sh` 复制为 `docker-images/deploy-offline.sh`。

## 2. 联网准备机

在可联网机器上执行以下操作。

### 2.1 下载模型

使用默认外置模型目录：

```bash
python3 backend/download_models.py --output ./models-offline --strict
```

使用自定义外置模型目录：

```bash
python3 backend/download_models.py --output /data/tianshu/models-offline --strict
```

如果模型目录已经存在，可以只校验不下载：

```bash
python3 backend/download_models.py --output ./models-offline --verify-only --strict
```

### 2.2 构建离线包

使用默认模型目录 `./models-offline`：

```bash
PLATFORM=amd64 bash scripts/build-offline.sh
```

使用自定义模型目录：

```bash
PLATFORM=amd64 OFFLINE_MODELS_PATH=/data/tianshu/models-offline bash scripts/build-offline.sh
```

构建脚本会执行：

- 校验或下载模型。
- 构建 `tianshu-backend:latest`。
- 构建 `tianshu-frontend:latest`。
- 拉取并导出 `rustfs/rustfs:latest`。
- 拉取并导出 `redis:7-alpine`。
- 打包模型目录为 `models-offline.tar.gz`。
- 复制离线 compose、环境变量模板和部署脚本到 `docker-images/`。

构建完成后检查：

```bash
ls -lh docker-images/
tar tzf docker-images/models-offline.tar.gz | head
```

## 3. 传输到离线服务器

把 `docker-images/` 里的所有文件传到离线服务器同一个目录，例如 `/opt/tianshu`。

```bash
rsync -avz --progress docker-images/ user@server:/opt/tianshu/
```

离线服务器上的目录示例：

```text
/opt/tianshu/
├── tianshu-backend-amd64.tar.gz
├── tianshu-frontend-amd64.tar.gz
├── rustfs-amd64.tar.gz
├── redis-amd64.tar.gz
├── models-offline.tar.gz
├── docker-compose.offline.yml
├── docker-compose.yml
├── .env.example
└── deploy-offline.sh
```

## 4. 离线服务器部署

### 4.1 前置要求

离线服务器需要提前安装：

- Docker 20.10 或更高版本。
- Docker Compose 2.0 或更高版本。
- NVIDIA Driver 525 或更高版本。
- NVIDIA Container Toolkit。

确认 GPU 可用：

```bash
nvidia-smi
```

### 4.2 默认部署

进入部署目录：

```bash
cd /opt/tianshu
```

执行部署：

```bash
bash deploy-offline.sh
```

默认情况下，模型会解压到当前目录下的 `./models-offline`，并由
`docker-compose.offline.yml` 挂载到容器内 `/app/models` 及相关缓存目录。

### 4.3 指定外置模型目录

可以通过环境变量指定宿主机模型目录：

```bash
OFFLINE_MODELS_PATH=/data/tianshu/models-offline bash deploy-offline.sh
```

也可以先写入 `.env`：

```env
OFFLINE_MODELS_PATH=/data/tianshu/models-offline
```

注意：`deploy-offline.sh` 会重新解压 `models-offline.tar.gz` 到
`OFFLINE_MODELS_PATH`。该路径应是专门给天枢模型使用的目录，不要指向已有重要数据目录。

### 4.4 环境变量

首次运行时，如果 `.env` 不存在，部署脚本会从 `.env.example` 创建 `.env`，
并尝试生成 `JWT_SECRET_KEY`。

部署后建议检查以下配置：

```env
OFFLINE_MODELS_PATH=./models-offline
API_PORT=8080
FRONTEND_PORT=80
GPU_COUNT=1
CUDA_VISIBLE_DEVICES=0
WORKER_GPUS=2
WORKER_MEMORY_LIMIT=16G
WORKER_MEMORY_RESERVATION=8G
RUSTFS_PUBLIC_URL=http://<server-ip>:9000
```

如果需要修改 `.env`，修改后重启：

```bash
docker compose -f docker-compose.offline.yml up -d
```

## 5. 启动与停止

查看服务状态：

```bash
docker compose -f docker-compose.offline.yml ps
```

查看日志：

```bash
docker compose -f docker-compose.offline.yml logs -f
docker compose -f docker-compose.offline.yml logs -f backend
docker compose -f docker-compose.offline.yml logs -f worker
```

停止服务：

```bash
docker compose -f docker-compose.offline.yml down
```

重新启动服务：

```bash
docker compose -f docker-compose.offline.yml up -d
```

## 6. Redis 可选模式

默认不启用 Redis，系统使用 SQLite 队列。

如需启用 Redis：

1. 确认 `redis-amd64.tar.gz` 已经传到离线服务器。
2. 在 `.env` 中设置：

```env
REDIS_QUEUE_ENABLED=true
```

3. 使用 Redis profile 启动：

```bash
docker compose -f docker-compose.offline.yml --profile redis up -d
```

不启用 Redis 时，不要把 `REDIS_QUEUE_ENABLED` 设置为 `true`。

## 7. 验证

### 7.1 健康检查

```bash
curl -f http://localhost:8080/api/v1/health
curl -f http://localhost:8001/health
curl -f http://localhost/
```

确认容器内 GPU 可用：

```bash
docker compose -f docker-compose.offline.yml exec worker nvidia-smi
```

### 7.2 模型路径检查

```bash
docker compose -f docker-compose.offline.yml exec worker test -f /app/models/mineru.json
docker compose -f docker-compose.offline.yml exec worker test -d /app/models/PDF-Extract-Kit-1.0/models
docker compose -f docker-compose.offline.yml exec worker test -d /app/models/MinerU2.5-2509-1.2B
docker compose -f docker-compose.offline.yml exec worker test -d /root/.paddlex/official_models/PaddleOCR-VL-1.5-0.9B
docker compose -f docker-compose.offline.yml exec worker test -d /root/.paddlex/official_models/PP-DocLayoutV3
docker compose -f docker-compose.offline.yml exec worker test -d /app/models/SenseVoiceSmall
docker compose -f docker-compose.offline.yml exec worker test -d /app/models/speech_fsmn_vad_zh-cn-16k-common-pytorch
```

### 7.3 离线检查

日志中不应出现下载或访问公网模型源：

```bash
docker compose -f docker-compose.offline.yml logs backend worker \
  | grep -Ei 'Downloading|auto-download|huggingface.co|hf-mirror.com|modelscope.cn|paddlepaddle.org.cn'
```

如果上面的命令没有输出，说明日志中没有匹配到已知下载关键词。

建议在完全断网环境中至少验证：

- PDF pipeline 模式解析成功。
- PDF vlm-transformers 模式解析成功。
- 图片 OCR / PaddleOCR-VL 解析成功。
- 音频识别成功。
- 去水印功能成功，或在未启用依赖时明确提示不可用。

## 8. 常见问题

### 8.1 提示缺少镜像 tar

确认所有构建产物都在离线服务器部署目录下：

```bash
ls -lh /opt/tianshu
```

如平台不是 `amd64`，部署时要指定相同的 `PLATFORM`：

```bash
PLATFORM=amd64 bash deploy-offline.sh
```

### 8.2 提示模型目录不完整

在联网准备机重新校验模型：

```bash
python3 backend/download_models.py --output ./models-offline --verify-only --strict
```

校验通过后重新构建或重新打包 `models-offline.tar.gz`，再传到离线服务器。

### 8.3 容器无法访问 GPU

先确认宿主机 GPU 正常：

```bash
nvidia-smi
```

再确认 NVIDIA Container Toolkit 已安装，并查看 worker 日志：

```bash
docker compose -f docker-compose.offline.yml logs -f worker
```

### 8.4 RustFS 图片无法外部访问

检查 `.env` 中的 `RUSTFS_PUBLIC_URL`，它必须是客户端能访问的地址：

```env
RUSTFS_PUBLIC_URL=http://<server-ip>:9000
```

修改后重启服务：

```bash
docker compose -f docker-compose.offline.yml up -d
```

## 9. 入口地址

部署完成后访问：

```text
Web UI:   http://<server-ip>
API:      http://<server-ip>:8080
API Docs: http://<server-ip>:8080/docs
RustFS:   http://<server-ip>:9001
```
