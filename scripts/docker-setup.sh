#!/bin/bash
# Tianshu (天枢) - Docker 快速部署脚本
# 一键检查依赖、配置环境、启动服务

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[⚠]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }

# ============================================================================
# 检查依赖
# ============================================================================
check_dependencies() {
    log_info "检查系统依赖..."

    # 检查 Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装，请先安装 Docker"
        log_info "安装指南: https://docs.docker.com/get-docker/"
        exit 1
    fi
    log_success "Docker 已安装: $(docker --version)"

    # 检查 Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose 未安装"
        log_info "安装指南: https://docs.docker.com/compose/install/"
        exit 1
    fi

    if command -v docker-compose &> /dev/null; then
        log_success "Docker Compose 已安装: $(docker-compose --version)"
        COMPOSE_CMD="docker-compose"
    else
        log_success "Docker Compose 已安装: $(docker compose version)"
        COMPOSE_CMD="docker compose"
    fi

    # 检查 NVIDIA Container Toolkit（GPU 支持）
    if command -v nvidia-smi &> /dev/null; then
        log_success "检测到 NVIDIA GPU"

        if docker run --rm --gpus all nvidia/cuda:12.6.2-base-ubuntu22.04 nvidia-smi &> /dev/null; then
            log_success "NVIDIA Container Toolkit 已正确配置"
        else
            log_warning "NVIDIA Container Toolkit 未配置或配置不正确"
            log_info "安装指南: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html"
            log_warning "将以 CPU 模式运行"
        fi
    else
        log_warning "未检测到 NVIDIA GPU，将以 CPU 模式运行"
    fi
}

# ============================================================================
# 配置环境
# ============================================================================
setup_environment() {
    log_info "配置环境变量..."

    if [ ! -f .env ]; then
        if [ -f .env.example ]; then
            cp .env.example .env
            log_success "已创建 .env 文件"
            log_warning "请编辑 .env 文件，特别是 JWT_SECRET_KEY"

            # 生成随机 JWT 密钥
            if command -v openssl &> /dev/null; then
                JWT_SECRET=$(openssl rand -hex 32)
                sed -i "s/CHANGE_THIS_TO_A_SECURE_RANDOM_STRING_IN_PRODUCTION/$JWT_SECRET/" .env
                log_success "已自动生成 JWT_SECRET_KEY"
            else
                log_warning "请手动修改 .env 中的 JWT_SECRET_KEY"
            fi
        else
            log_error ".env.example 文件不存在"
            exit 1
        fi
    else
        log_success ".env 文件已存在"
    fi
}

# ============================================================================
# 创建必要目录
# ============================================================================
create_directories() {
    log_info "创建必要的目录..."

    mkdir -p models
    mkdir -p data/uploads
    mkdir -p data/output
    mkdir -p data/db
    mkdir -p logs/backend
    mkdir -p logs/worker
    mkdir -p logs/mcp

    log_success "目录结构创建完成"
}

# ============================================================================
# 构建镜像
# ============================================================================
build_images() {
    log_info "构建 Docker 镜像（首次运行可能需要 10-30 分钟）..."
    log_warning "首次构建需下载大型 AI 包：PaddlePaddle ~1.8GB, PyTorch ~2GB"
    echo ""

    $COMPOSE_CMD build --parallel

    log_success "镜像构建完成"
}

# ============================================================================
# 启动服务
# ============================================================================
start_services() {
    local mode=${1:-prod}

    if [ "$mode" = "dev" ]; then
        log_info "启动开发环境..."
        $COMPOSE_CMD -f docker-compose.dev.yml up -d
    else
        log_info "启动生产环境..."
        $COMPOSE_CMD up -d
    fi

    log_success "服务启动中..."

    # 等待服务就绪
    log_info "等待服务就绪..."
    sleep 10

    # 检查服务状态
    $COMPOSE_CMD ps
}

# ============================================================================
# 显示访问信息
# ============================================================================
show_info() {
    log_success "=========================================="
    log_success "Tianshu (天枢) 部署完成！"
    log_success "=========================================="
    echo ""
    log_info "服务访问地址:"
    echo "  - 前端界面: http://localhost:$(grep FRONTEND_PORT .env | cut -d'=' -f2 || echo 80)"
    echo "  - API 文档: http://localhost:$(grep API_PORT .env | cut -d'=' -f2 || echo 8000)/docs"
    echo "  - Worker:   http://localhost:$(grep WORKER_PORT .env | cut -d'=' -f2 || echo 8001)"
    echo "  - MCP:      http://localhost:$(grep MCP_PORT .env | cut -d'=' -f2 || echo 8002)"
    echo ""
    log_info "常用命令:"
    echo "  - 查看日志: $COMPOSE_CMD logs -f"
    echo "  - 停止服务: $COMPOSE_CMD down"
    echo "  - 重启服务: $COMPOSE_CMD restart"
    echo "  - 查看状态: $COMPOSE_CMD ps"
    echo ""
    log_warning "首次运行时，模型会自动下载，这可能需要一些时间"
    log_warning "默认管理员账号需要通过注册页面创建"
}

# ============================================================================
# 主菜单
# ============================================================================
show_menu() {
    echo ""
    echo "╔════════════════════════════════════════╗"
    echo "║   Tianshu (天枢) Docker 部署脚本         ║"
    echo "╚════════════════════════════════════════╝"
    echo ""
    echo "请选择操作:"
    echo "  1) 全新部署（检查依赖 + 构建 + 启动）"
    echo "  2) 仅启动服务（生产环境）"
    echo "  3) 启动开发环境"
    echo "  4) 停止所有服务"
    echo "  5) 重启服务"
    echo "  6) 查看服务状态"
    echo "  7) 查看日志"
    echo "  8) 清理所有数据（危险操作）"
    echo "  0) 退出"
    echo ""
    read -p "请输入选项 [0-8]: " choice

    case $choice in
        1)
            check_dependencies
            setup_environment
            create_directories
            build_images
            start_services prod
            show_info
            ;;
        2)
            start_services prod
            show_info
            ;;
        3)
            setup_environment
            create_directories
            start_services dev
            show_info
            ;;
        4)
            log_info "停止服务..."
            $COMPOSE_CMD down
            log_success "服务已停止"
            ;;
        5)
            log_info "重启服务..."
            $COMPOSE_CMD restart
            log_success "服务已重启"
            ;;
        6)
            $COMPOSE_CMD ps
            ;;
        7)
            $COMPOSE_CMD logs -f
            ;;
        8)
            log_warning "此操作将删除所有数据（包括数据库、上传文件、模型）"
            read -p "确认删除? (yes/no): " confirm
            if [ "$confirm" = "yes" ]; then
                $COMPOSE_CMD down -v
                rm -rf data/ logs/ models/
                log_success "数据已清理"
            else
                log_info "操作已取消"
            fi
            ;;
        0)
            log_info "退出"
            exit 0
            ;;
        *)
            log_error "无效选项"
            show_menu
            ;;
    esac
}

# ============================================================================
# 入口
# ============================================================================
main() {
    # 切换到项目根目录
    cd "$(dirname "$0")/.."

    # 如果有参数，直接执行
    if [ $# -gt 0 ]; then
        case $1 in
            setup)
                check_dependencies
                setup_environment
                create_directories
                build_images
                start_services prod
                show_info
                ;;
            start)
                start_services prod
                ;;
            dev)
                start_services dev
                ;;
            stop)
                $COMPOSE_CMD down
                ;;
            *)
                log_error "未知命令: $1"
                echo "用法: $0 [setup|start|dev|stop]"
                exit 1
                ;;
        esac
    else
        # 显示菜单
        show_menu
    fi
}

main "$@"
