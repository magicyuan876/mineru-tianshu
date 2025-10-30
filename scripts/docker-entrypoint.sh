#!/bin/bash
# Tianshu (天枢) - Docker Entrypoint Script
# 容器启动脚本，处理初始化和健康检查

set -e

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
# 环境检查
# ============================================================================
check_environment() {
    local service_type=$1

    log_info "检查环境配置..."

    # 检查 Python 版本
    PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
    log_info "Python 版本: $PYTHON_VERSION"

    # 检查 CUDA
    if command -v nvidia-smi &> /dev/null; then
        log_success "检测到 NVIDIA GPU"
        nvidia-smi --query-gpu=gpu_name,driver_version,memory.total --format=csv,noheader
    else
        log_warning "未检测到 NVIDIA GPU 或驱动"
    fi

    # 检查必要的环境变量（仅 API Server 需要 JWT）
    if [ "$service_type" != "worker" ] && [ "$service_type" != "mcp" ]; then
        if [ -z "$JWT_SECRET_KEY" ]; then
            log_error "JWT_SECRET_KEY 未设置！请在 .env 中配置"
            exit 1
        fi

        if [ "$JWT_SECRET_KEY" = "CHANGE_THIS_TO_A_SECURE_RANDOM_STRING_IN_PRODUCTION" ]; then
            log_warning "JWT_SECRET_KEY 使用默认值，生产环境必须修改！"
        fi
    fi
}

# ============================================================================
# 目录初始化
# ============================================================================
initialize_directories() {
    log_info "初始化目录结构..."

    mkdir -p /app/models
    mkdir -p /app/data/uploads
    mkdir -p /app/data/output
    mkdir -p /app/logs

    log_success "目录结构初始化完成"
}

# ============================================================================
# 模型检查
# ============================================================================
check_models() {
    log_info "检查模型文件..."

    MODEL_PATH=${MODEL_PATH:-/app/models}

    if [ ! -d "$MODEL_PATH" ]; then
        log_warning "模型目录不存在，将创建 $MODEL_PATH"
        mkdir -p "$MODEL_PATH"
    fi

    # 检查关键模型
    if [ -d "$MODEL_PATH/deepseek_ocr" ]; then
        log_success "找到 DeepSeek OCR 模型"
    else
        log_warning "DeepSeek OCR 模型未找到，首次运行将自动下载"
    fi

    if [ -d "$MODEL_PATH/paddleocr_vl" ]; then
        log_success "找到 PaddleOCR-VL 模型"
    else
        log_warning "PaddleOCR-VL 模型未找到，首次运行将自动下载"
    fi

    if [ -d "$MODEL_PATH/sensevoice" ]; then
        log_success "找到 SenseVoice 模型"
    else
        log_warning "SenseVoice 模型未找到，音频处理功能将受限"
    fi
}

# ============================================================================
# 数据库初始化
# ============================================================================
initialize_database() {
    log_info "检查数据库..."

    DB_PATH=${DATABASE_PATH:-mineru_tianshu.db}

    if [ -f "$DB_PATH" ]; then
        log_success "数据库已存在: $DB_PATH"
    else
        log_info "首次运行，数据库将自动创建"
    fi
}

# ============================================================================
# 健康检查
# ============================================================================
wait_for_service() {
    local service_url=$1
    local service_name=$2
    local max_retries=30
    local retry_count=0

    log_info "等待 $service_name 启动..."

    while [ $retry_count -lt $max_retries ]; do
        if curl -f -s "$service_url" > /dev/null 2>&1; then
            log_success "$service_name 已就绪"
            return 0
        fi

        retry_count=$((retry_count + 1))
        log_info "等待中... ($retry_count/$max_retries)"
        sleep 2
    done

    log_error "$service_name 启动超时"
    return 1
}

# ============================================================================
# GPU 检查
# ============================================================================
check_gpu() {
    log_info "检查 GPU 可用性..."

    # 检查 PyTorch
    python -c "import torch; print('PyTorch CUDA:', torch.cuda.is_available())" 2>&1 | while read line; do
        log_info "$line"
    done

    # 检查 PaddlePaddle
    python -c "import paddle; print('Paddle CUDA:', paddle.device.is_compiled_with_cuda())" 2>&1 | while read line; do
        log_info "$line"
    done

    # 检查设备信息
    if python -c "import torch; print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'No GPU')" 2>&1 | grep -q "No GPU"; then
        log_warning "未检测到可用的 GPU 设备"
    else
        GPU_NAME=$(python -c "import torch; print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else '')")
        log_success "GPU 设备: $GPU_NAME"
    fi
}

# ============================================================================
# 主入口
# ============================================================================
main() {
    log_info "=========================================="
    log_info "Tianshu (天枢) 启动中..."
    log_info "=========================================="

    # 首先确定服务类型
    SERVICE_TYPE=${1:-api}

    # 运行检查（传递服务类型）
    check_environment "$SERVICE_TYPE"
    initialize_directories
    initialize_database
    check_models

    # 根据服务类型执行不同的检查

    if [ "$SERVICE_TYPE" = "worker" ]; then
        log_info "启动类型: LitServe Worker"
        check_gpu
        shift  # 移除第一个参数（服务类型）
    elif [ "$SERVICE_TYPE" = "mcp" ]; then
        log_info "启动类型: MCP Server"
        shift  # 移除第一个参数（服务类型）
    else
        log_info "启动类型: API Server"
        # 如果第一个参数是 "api"，也需要移除
        if [ "$1" = "api" ]; then
            shift
        fi
    fi

    log_info "=========================================="
    log_success "初始化完成，启动服务..."
    log_info "=========================================="

    # 执行传入的命令（此时 $@ 已经不包含服务类型参数）
    exec "$@"
}

# 捕获信号以优雅关闭
trap 'log_warning "收到终止信号，正在关闭..."; exit 0' SIGTERM SIGINT

# 执行主函数
main "$@"
