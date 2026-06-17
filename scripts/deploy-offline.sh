#!/bin/bash
# Tianshu 离线部署脚本
# 用于在生产环境(离线)中部署 Tianshu (GPU版本)
# 要求: NVIDIA GPU + NVIDIA Driver 525+ + NVIDIA Container Toolkit

set -e

# ============================================================================
# 配置
# ============================================================================
COMPOSE_FILE="docker-compose.offline.yml"
PLATFORM="${PLATFORM:-amd64}"
BACKEND_IMAGE_TAR="${BACKEND_IMAGE_TAR:-tianshu-backend-${PLATFORM}.tar.gz}"
FRONTEND_IMAGE_TAR="${FRONTEND_IMAGE_TAR:-tianshu-frontend-${PLATFORM}.tar.gz}"
RUSTFS_IMAGE_TAR="${RUSTFS_IMAGE_TAR:-rustfs-${PLATFORM}.tar.gz}"
REDIS_IMAGE_TAR="${REDIS_IMAGE_TAR:-redis-${PLATFORM}.tar.gz}"
MODELS_TAR="${MODELS_TAR:-models-offline.tar.gz}"

if [ -z "${OFFLINE_MODELS_PATH:-}" ] && [ -f ".env" ]; then
    OFFLINE_MODELS_PATH="$(grep -E '^OFFLINE_MODELS_PATH=' .env 2>/dev/null | tail -n 1 | cut -d= -f2- || true)"
    OFFLINE_MODELS_PATH="${OFFLINE_MODELS_PATH%\"}"
    OFFLINE_MODELS_PATH="${OFFLINE_MODELS_PATH#\"}"
    OFFLINE_MODELS_PATH="${OFFLINE_MODELS_PATH%\'}"
    OFFLINE_MODELS_PATH="${OFFLINE_MODELS_PATH#\'}"
fi

OFFLINE_MODELS_PATH="${OFFLINE_MODELS_PATH:-./models-offline}"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# ============================================================================
# 检查函数
# ============================================================================
check_nvidia_driver() {
    log_info "Checking NVIDIA environment..."

    if ! command -v nvidia-smi &> /dev/null; then
        log_error "nvidia-smi not found!"
        log_error "NVIDIA driver is required for GPU deployment"
        exit 1
    fi

    # 显示 GPU 信息
    if nvidia-smi &> /dev/null 2>&1; then
        nvidia-smi
        log_success "NVIDIA driver detected"
    else
        log_error "NVIDIA driver found but not working"
        exit 1
    fi
    echo ""
}

check_nvidia_container_toolkit() {
    log_info "Checking NVIDIA Container Toolkit..."

    local test_image="${GPU_TEST_IMAGE:-tianshu-backend:latest}"

    # 测试 GPU 是否可以被 Docker 访问。离线环境不应依赖额外拉取 nvidia/cuda 测试镜像。
    if ! docker image inspect "$test_image" > /dev/null 2>&1; then
        log_warning "GPU test image not loaded yet: $test_image"
        log_warning "Skipping pre-load container toolkit check; worker startup will verify GPU access after images are loaded"
        echo ""
        return 0
    fi

    if docker run --rm --gpus all --entrypoint nvidia-smi "$test_image" &> /dev/null 2>&1; then
        log_success "NVIDIA Container Toolkit is working"
        log_info "Will use GPU acceleration"
    else
        log_error "NVIDIA Container Toolkit not working!"
        log_info "To enable GPU support, install NVIDIA Container Toolkit:"
        log_info "  https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html"
        exit 1
    fi
    echo ""
}

check_files() {
    log_info "Checking required files..."

    local missing_files=()

    if [ ! -f "$BACKEND_IMAGE_TAR" ]; then
        missing_files+=("$BACKEND_IMAGE_TAR")
    fi

    if [ ! -f "$FRONTEND_IMAGE_TAR" ]; then
        missing_files+=("$FRONTEND_IMAGE_TAR")
    fi

    if [ ! -f "$RUSTFS_IMAGE_TAR" ]; then
        missing_files+=("$RUSTFS_IMAGE_TAR")
    fi

    if [ ! -f "$MODELS_TAR" ] && [ ! -L "$MODELS_TAR" ]; then
        log_warning "$MODELS_TAR not found"
        missing_files+=("$MODELS_TAR")
    fi

    if [ ${#missing_files[@]} -ne 0 ]; then
        log_error "Missing required files:"
        for file in "${missing_files[@]}"; do
            echo "  - $file"
        done
        echo ""
        log_error "Please ensure all files are transferred to this directory"
        exit 1
    fi

    log_success "All required files found"
}

check_models() {
    log_info "Checking offline model directory..."

    local missing_paths=()
    local required_paths=(
        "$OFFLINE_MODELS_PATH/mineru.json"
        "$OFFLINE_MODELS_PATH/PDF-Extract-Kit-1.0/models"
        "$OFFLINE_MODELS_PATH/MinerU2.5-2509-1.2B"
        "$OFFLINE_MODELS_PATH/paddlex_cache/official_models/PaddleOCR-VL-1.5-0.9B"
        "$OFFLINE_MODELS_PATH/paddlex_cache/official_models/PP-DocLayoutV3"
        "$OFFLINE_MODELS_PATH/SenseVoiceSmall"
        "$OFFLINE_MODELS_PATH/speech_fsmn_vad_zh-cn-16k-common-pytorch"
    )

    for path in "${required_paths[@]}"; do
        if [ ! -e "$path" ]; then
            missing_paths+=("$path")
        fi
    done

    if [ ${#missing_paths[@]} -ne 0 ]; then
        log_error "Offline model directory is incomplete:"
        for path in "${missing_paths[@]}"; do
            echo "  - $path"
        done
        exit 1
    fi

    log_success "Offline model directory looks complete"
}

extract_models() {
    if [ -z "$OFFLINE_MODELS_PATH" ] || [ "$OFFLINE_MODELS_PATH" = "/" ]; then
        log_error "Refusing to extract models to unsafe OFFLINE_MODELS_PATH: $OFFLINE_MODELS_PATH"
        exit 1
    fi

    rm -rf "$OFFLINE_MODELS_PATH"
    mkdir -p "$OFFLINE_MODELS_PATH"

    local first_entry
    first_entry="$(tar tzf "$MODELS_TAR" | head -n 1)"
    case "$first_entry" in
        models-offline|models-offline/*|./models-offline|./models-offline/*)
            tar xzf "$MODELS_TAR" -C "$OFFLINE_MODELS_PATH" --strip-components=1
            ;;
        *)
            tar xzf "$MODELS_TAR" -C "$OFFLINE_MODELS_PATH"
            ;;
    esac
}

# ============================================================================
# 主函数
# ============================================================================
main() {
    log_info "=========================================="
    log_info "🚀 Deploying Tianshu (Offline - GPU Version)"
    log_info "=========================================="
    log_info "Offline models path: $OFFLINE_MODELS_PATH"
    echo ""

    # 1. 检查 NVIDIA 环境
    check_nvidia_driver

    # 2. 检查文件
    check_files
    echo ""

    # 3. 加载 Docker 镜像
    log_info "📥 Loading Docker images..."
    log_info "   This may take 5-10 minutes..."
    echo ""

    log_info "   Loading backend image..."
    docker load < "$BACKEND_IMAGE_TAR"

    log_info "   Loading frontend image..."
    docker load < "$FRONTEND_IMAGE_TAR"

    log_info "   Loading rustfs image..."
    docker load < "$RUSTFS_IMAGE_TAR"

    if [ -f "$REDIS_IMAGE_TAR" ]; then
        log_info "   Loading redis image..."
        docker load < "$REDIS_IMAGE_TAR"
    else
        log_warning "Redis image tar not found ($REDIS_IMAGE_TAR); redis profile will not work offline"
    fi

    log_success "All images loaded successfully"
    echo ""

    # 3.5 检查容器 GPU 访问（使用已加载的后端镜像，避免离线环境拉取测试镜像）
    check_nvidia_container_toolkit

    # 4. 解压模型文件
    if [ ! -L "$MODELS_TAR" ]; then
        log_info "📦 Extracting models..."
    else
        log_info "📦 Models are linked, extracting from source..."
    fi
    log_info "   This may take 5-10 minutes..."
    extract_models
    log_success "Models extracted successfully"
    echo ""

    # 4.5 校验模型目录
    check_models
    echo ""

    # 5. 创建目录结构
    log_info "📁 Creating directories..."
    mkdir -p data/{uploads,output,db}
    mkdir -p logs/{backend,worker,mcp}
    log_success "Directories created"
    echo ""

    # 6. 配置环境变量
    if [ ! -f ".env" ]; then
        log_info "⚙️  Creating .env from template..."

        if [ -f ".env.example" ]; then
            cp .env.example .env
        else
            log_error ".env.example not found!"
            log_info "Please create .env manually or copy it from the source"
            exit 1
        fi

        # 生成 JWT 密钥
        if command -v openssl &> /dev/null; then
            JWT_KEY=$(openssl rand -hex 32)
            sed -i.bak "s/your-secret-key-change-in-production/$JWT_KEY/" .env
            rm -f .env.bak
            log_success "JWT secret key generated"
        else
            log_warning "openssl not found, please manually set JWT_SECRET_KEY in .env"
        fi

        # 获取服务器 IP
        if command -v hostname &> /dev/null; then
            SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
            if [ -n "$SERVER_IP" ]; then
                # 兼容不同的 IP 占位符格式
                sed -i.bak "s|http://192.168.1.100:9000|http://$SERVER_IP:9000|" .env
                sed -i.bak "s|http://192.168.100.126:9000|http://$SERVER_IP:9000|" .env
                rm -f .env.bak
                log_success "RUSTFS_PUBLIC_URL set to http://$SERVER_IP:9000"
            else
                log_warning "Could not detect server IP, please manually set RUSTFS_PUBLIC_URL in .env"
            fi
        fi

        log_success ".env created"
        log_warning "Please review and adjust .env if needed before starting services"
        echo ""
    else
        log_info ".env already exists, skipping creation"
        echo ""
    fi

    # 7. 启动服务
    log_info "🚀 Starting services..."
    log_info "   Using docker-compose file: $COMPOSE_FILE"
    echo ""

    # 检查 docker-compose 命令
    if command -v docker-compose &> /dev/null; then
        COMPOSE_CMD="docker-compose"
    elif docker compose version &> /dev/null 2>&1; then
        COMPOSE_CMD="docker compose"
    else
        log_error "Docker Compose not found!"
        exit 1
    fi

    $COMPOSE_CMD -f $COMPOSE_FILE up -d

    log_success "Services started successfully"
    echo ""

    # 8. 健康检查
    log_info "🔍 Waiting for services to start..."
    log_info "   This may take 1-2 minutes..."
    echo ""

    for i in {1..30}; do
        if curl -f -s http://localhost:8000/api/v1/health > /dev/null 2>&1; then
            log_success "Backend is healthy"
            break
        fi
        echo -n "."
        sleep 2

        if [ "$i" -eq 30 ]; then
            echo ""
            log_warning "Backend health check timeout"
            log_info "Services may still be starting, check logs with:"
            log_info "  $COMPOSE_CMD -f $COMPOSE_FILE logs -f backend"
        fi
    done
    echo ""

    # 9. 验证 GPU 访问
    log_info "🔍 Verifying GPU access in containers..."
    sleep 5  # 等待 worker 完全启动

    if $COMPOSE_CMD -f $COMPOSE_FILE exec -T worker nvidia-smi &> /dev/null; then
        log_success "GPU is accessible in worker container"
        log_info "GPU information:"
        $COMPOSE_CMD -f $COMPOSE_FILE exec -T worker nvidia-smi
    else
        log_warning "Could not verify GPU (worker may be initializing)"
    fi
    echo ""

    # 10. 显示访问信息
    log_info "=========================================="
    log_success "✅ Deployment Complete!"
    log_info "=========================================="
    echo ""

    # 获取服务器 IP
    SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
    if [ -z "$SERVER_IP" ]; then
        SERVER_IP="<your-server-ip>"
    fi

    log_info "🌐 Access URLs:"
    echo "   Web UI:     http://$SERVER_IP"
    echo "   API:        http://$SERVER_IP:8000"
    echo "   API Docs:   http://$SERVER_IP:8000/docs"
    echo "   RustFS:     http://$SERVER_IP:9001"
    echo ""

    log_info "📊 Check status:"
    echo "   $COMPOSE_CMD -f $COMPOSE_FILE ps"
    echo ""

    log_info "📋 View logs:"
    echo "   $COMPOSE_CMD -f $COMPOSE_FILE logs -f"
    echo "   $COMPOSE_CMD -f $COMPOSE_FILE logs -f backend"
    echo "   $COMPOSE_CMD -f $COMPOSE_FILE logs -f worker"
    echo ""

    log_info "🔍 Verify GPU:"
    echo "   $COMPOSE_CMD -f $COMPOSE_FILE exec worker nvidia-smi"
    echo ""

    log_info "🛑 Stop services:"
    echo "   $COMPOSE_CMD -f $COMPOSE_FILE down"
    echo ""

    log_success "Deployment script completed!"
    echo ""
    log_info "✅ Running with GPU acceleration"
    echo "     - Processing speed: 5-10x faster than CPU"
    echo "     - Monitor GPU usage: watch nvidia-smi"
    echo ""
    log_info "⚠️  Remember to:"
    echo "     1. Check .env configuration (especially RUSTFS_PUBLIC_URL)"
    echo "     2. Upload a test file to verify processing"
}

# 捕获中断信号
trap 'log_warning "Deployment interrupted by user"; exit 130' SIGINT SIGTERM

# 执行主函数
main
