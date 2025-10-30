# Tianshu (天枢) Backend - Multi-stage Docker Build
# 企业级 AI 数据预处理平台 - 支持 GPU 加速的多模态文档处理服务
#
# 构建方式:
#   docker build -t tianshu-backend:latest -f backend/Dockerfile .
#
# 运行方式:
#   docker run --gpus all -p 8000:8000 tianshu-backend:latest

# ============================================================================
# Stage 1: Base Image with CUDA Support
# ============================================================================
FROM nvidia/cuda:12.6.2-cudnn-runtime-ubuntu24.04 AS base

# 设置环境变量
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    CUDA_HOME=/usr/local/cuda \
    PATH=/usr/local/cuda/bin:$PATH \
    LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.12 \
    python3.12-dev \
    python3-pip \
    python3.12-venv \
    git \
    wget \
    curl \
    libgomp1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgl1 \
    libgstreamer1.0-0 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 创建符号链接，让 python3 指向 python3.12
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1 \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3.12 1

# 升级 pip
RUN python3 -m pip install --upgrade pip setuptools wheel --break-system-packages --ignore-installed

# ============================================================================
# Stage 2: Dependencies Installation
# ============================================================================
FROM base AS dependencies

WORKDIR /tmp

# 复制 requirements.txt
COPY backend/requirements.txt /tmp/requirements.txt

# 分步安装依赖（解决 PyTorch + PaddlePaddle CUDA 冲突）
# Step 1: 安装 PaddlePaddle GPU 版本（~1.8GB，耐心等待）
RUN pip install paddlepaddle-gpu==3.2.0 \
    -i https://www.paddlepaddle.org.cn/packages/stable/cu126/ \
    --break-system-packages

# Step 2: 安装 PyTorch (CUDA 12.6, ~2GB)
RUN pip install torch==2.6.0+cu126 torchvision==0.21.0+cu126 \
    --index-url https://download.pytorch.org/whl/cu126 \
    --break-system-packages

# Step 3: 预先安装 Python 3.12 关键依赖
RUN pip install "kiwisolver>=1.4.5" "Pillow>=11.0.0" \
    "numpy>=1.26.0,<2.0.0" "setuptools>=75.0.0" "lxml>=5.3.0" \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    --break-system-packages

# Step 4: 安装其他依赖（跳过已安装的 torch 和 paddle）
RUN pip install -r /tmp/requirements.txt \
    --no-deps \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    --break-system-packages || true

# Step 5: 补充安装缺失的依赖
RUN pip install -r /tmp/requirements.txt \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    --break-system-packages

# 验证安装
RUN python -c "import paddle, torch; from transformers import AutoModel; print('✅ All frameworks OK')" && \
    python -c "import paddle, torch; print('Paddle CUDA:', paddle.device.is_compiled_with_cuda()); print('PyTorch CUDA:', torch.cuda.is_available())"

# ============================================================================
# Stage 3: Application
# ============================================================================
FROM dependencies AS application

# 创建应用目录
WORKDIR /app

# 复制后端代码
COPY backend/ /app/backend/
COPY pyproject.toml /app/

# 复制启动脚本
COPY scripts/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# 创建必要的目录
RUN mkdir -p /app/models /app/data /app/uploads /app/output /app/logs

# 设置工作目录为后端
WORKDIR /app/backend

# 暴露端口
# 8000: API Server
# 8001: LitServe Worker
# 8002: MCP Server
EXPOSE 8000 8001 8002

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 使用 entrypoint 脚本
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

# 默认启动 API Server
CMD ["python", "api_server.py"]
