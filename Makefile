# Tianshu (天枢) - Makefile
# 提供友好的命令接口用于 Docker 操作
#
# 使用方式: make [命令]
# 例如: make setup, make start, make logs

.PHONY: help setup build start stop restart status logs clean dev test

# 默认目标
.DEFAULT_GOAL := help

# 检测操作系统
ifeq ($(OS),Windows_NT)
    DETECTED_OS := Windows
    COMPOSE_CMD := docker-compose
else
    DETECTED_OS := $(shell uname -s)
    # 尝试使用 docker compose (新版本) 否则使用 docker-compose
    COMPOSE_CMD := $(shell command -v docker 2>/dev/null && docker compose version 2>/dev/null && echo "docker compose" || echo "docker-compose")
endif

# 颜色输出
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
NC := \033[0m

# ============================================================================
# 帮助信息
# ============================================================================
help: ## 显示帮助信息
	@echo "╔════════════════════════════════════════════════════════╗"
	@echo "║         Tianshu (天枢) - Docker 管理命令              ║"
	@echo "╚════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "可用命令:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(BLUE)%-15s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "系统信息:"
	@echo "  操作系统: $(DETECTED_OS)"
	@echo "  Docker Compose: $(COMPOSE_CMD)"
	@echo ""

# ============================================================================
# 安装和配置
# ============================================================================
setup: ## 全新部署（配置环境 + 构建镜像 + 启动服务）
	@echo "$(BLUE)[INFO]$(NC) 开始全新部署..."
	@if [ ! -f .env ]; then \
		if [ -f .env.example ]; then \
			cp .env.example .env; \
			echo "$(GREEN)[OK]$(NC) .env 文件已创建"; \
			echo "$(YELLOW)[WARNING]$(NC) 请编辑 .env 文件，特别是 JWT_SECRET_KEY"; \
		else \
			echo "$(RED)[ERROR]$(NC) .env.example 文件不存在"; \
			exit 1; \
		fi; \
	else \
		echo "$(GREEN)[OK]$(NC) .env 文件已存在"; \
	fi
	@mkdir -p models data/uploads data/output data/db logs/backend logs/worker logs/mcp
	@echo "$(GREEN)[OK]$(NC) 目录结构创建完成"
	@$(MAKE) build
	@$(MAKE) start
	@$(MAKE) info

check: ## 检查系统依赖
	@echo "$(BLUE)[INFO]$(NC) 检查系统依赖..."
	@command -v docker >/dev/null 2>&1 || { echo "$(RED)[ERROR]$(NC) Docker 未安装"; exit 1; }
	@echo "$(GREEN)[OK]$(NC) Docker: $$(docker --version)"
	@$(COMPOSE_CMD) version >/dev/null 2>&1 || { echo "$(RED)[ERROR]$(NC) Docker Compose 未安装"; exit 1; }
	@echo "$(GREEN)[OK]$(NC) Docker Compose: $$($(COMPOSE_CMD) version)"
	@if command -v nvidia-smi >/dev/null 2>&1; then \
		echo "$(GREEN)[OK]$(NC) 检测到 NVIDIA GPU"; \
		nvidia-smi --query-gpu=gpu_name,driver_version --format=csv,noheader; \
	else \
		echo "$(YELLOW)[WARNING]$(NC) 未检测到 NVIDIA GPU"; \
	fi

# ============================================================================
# 构建
# ============================================================================
build: ## 构建所有 Docker 镜像
	@echo "$(BLUE)[INFO]$(NC) 构建 Docker 镜像..."
	@$(COMPOSE_CMD) build --parallel
	@echo "$(GREEN)[OK]$(NC) 镜像构建完成"

build-backend: ## 仅构建后端镜像
	@echo "$(BLUE)[INFO]$(NC) 构建后端镜像..."
	@$(COMPOSE_CMD) build backend

build-frontend: ## 仅构建前端镜像
	@echo "$(BLUE)[INFO]$(NC) 构建前端镜像..."
	@$(COMPOSE_CMD) build frontend

build-no-cache: ## 强制重新构建（不使用缓存）
	@echo "$(BLUE)[INFO]$(NC) 强制重新构建镜像..."
	@$(COMPOSE_CMD) build --no-cache --parallel

# ============================================================================
# 启动和停止
# ============================================================================
start: ## 启动所有服务（生产环境）
	@echo "$(BLUE)[INFO]$(NC) 启动生产环境..."
	@$(COMPOSE_CMD) up -d
	@echo "$(GREEN)[OK]$(NC) 服务启动中，等待就绪..."
	@sleep 10
	@$(MAKE) status

stop: ## 停止所有服务
	@echo "$(BLUE)[INFO]$(NC) 停止服务..."
	@$(COMPOSE_CMD) stop
	@echo "$(GREEN)[OK]$(NC) 服务已停止"

down: ## 停止并删除容器
	@echo "$(BLUE)[INFO]$(NC) 停止并删除容器..."
	@$(COMPOSE_CMD) down
	@echo "$(GREEN)[OK]$(NC) 容器已删除"

restart: ## 重启所有服务
	@echo "$(BLUE)[INFO]$(NC) 重启服务..."
	@$(COMPOSE_CMD) restart
	@echo "$(GREEN)[OK]$(NC) 服务已重启"

# ============================================================================
# 开发环境
# ============================================================================
dev: ## 启动开发环境
	@echo "$(BLUE)[INFO]$(NC) 启动开发环境..."
	@$(COMPOSE_CMD) -f docker-compose.dev.yml up -d
	@echo "$(GREEN)[OK]$(NC) 开发环境启动中..."
	@sleep 10
	@$(COMPOSE_CMD) -f docker-compose.dev.yml ps

dev-stop: ## 停止开发环境
	@$(COMPOSE_CMD) -f docker-compose.dev.yml down

dev-logs: ## 查看开发环境日志
	@$(COMPOSE_CMD) -f docker-compose.dev.yml logs -f

# ============================================================================
# 日志和状态
# ============================================================================
status: ## 查看服务状态
	@$(COMPOSE_CMD) ps

logs: ## 查看所有服务日志
	@$(COMPOSE_CMD) logs -f

logs-backend: ## 查看后端日志
	@$(COMPOSE_CMD) logs -f backend

logs-worker: ## 查看 Worker 日志
	@$(COMPOSE_CMD) logs -f worker

logs-frontend: ## 查看前端日志
	@$(COMPOSE_CMD) logs -f frontend

# ============================================================================
# 容器操作
# ============================================================================
shell-backend: ## 进入后端容器
	@$(COMPOSE_CMD) exec backend bash

shell-worker: ## 进入 Worker 容器
	@$(COMPOSE_CMD) exec worker bash

shell-frontend: ## 进入前端容器
	@$(COMPOSE_CMD) exec frontend sh

# ============================================================================
# 测试和调试
# ============================================================================
test-gpu: ## 测试 GPU 可用性
	@echo "$(BLUE)[INFO]$(NC) 测试 GPU..."
	@$(COMPOSE_CMD) exec worker nvidia-smi || echo "$(YELLOW)[WARNING]$(NC) GPU 不可用"
	@$(COMPOSE_CMD) exec worker python -c "import torch; print('PyTorch CUDA:', torch.cuda.is_available())"
	@$(COMPOSE_CMD) exec worker python -c "import paddle; print('Paddle CUDA:', paddle.device.is_compiled_with_cuda())"

test-api: ## 测试 API 是否可访问
	@echo "$(BLUE)[INFO]$(NC) 测试 API..."
	@curl -f http://localhost:8000/health && echo "$(GREEN)[OK]$(NC) API 正常" || echo "$(RED)[ERROR]$(NC) API 不可访问"

health: ## 检查所有服务健康状态
	@echo "$(BLUE)[INFO]$(NC) 检查服务健康状态..."
	@$(COMPOSE_CMD) ps | grep "healthy" && echo "$(GREEN)[OK]$(NC) 所有服务健康" || echo "$(YELLOW)[WARNING]$(NC) 部分服务不健康"

# ============================================================================
# 数据管理
# ============================================================================
backup-db: ## 备份数据库
	@echo "$(BLUE)[INFO]$(NC) 备份数据库..."
	@mkdir -p backups
	@$(COMPOSE_CMD) exec -T backend cp mineru_tianshu.db mineru_tianshu.db.backup
	@docker cp tianshu-backend:/app/backend/mineru_tianshu.db.backup ./backups/mineru_tianshu_$$(date +%Y%m%d_%H%M%S).db
	@echo "$(GREEN)[OK]$(NC) 数据库备份完成"

clean: ## 清理所有数据（危险操作！）
	@echo "$(RED)[WARNING]$(NC) 此操作将删除所有数据"
	@read -p "确认删除? [yes/N]: " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		$(COMPOSE_CMD) down -v; \
		rm -rf data/ logs/ models/; \
		echo "$(GREEN)[OK]$(NC) 数据已清理"; \
	else \
		echo "$(BLUE)[INFO]$(NC) 操作已取消"; \
	fi

clean-docker: ## 清理 Docker 资源
	@echo "$(BLUE)[INFO]$(NC) 清理 Docker 资源..."
	@docker system prune -f
	@echo "$(GREEN)[OK]$(NC) Docker 资源已清理"

# ============================================================================
# 信息展示
# ============================================================================
info: ## 显示访问信息
	@echo ""
	@echo "$(GREEN)========================================$(NC)"
	@echo "$(GREEN)   Tianshu (天枢) 部署完成！$(NC)"
	@echo "$(GREEN)========================================$(NC)"
	@echo ""
	@echo "$(BLUE)[INFO]$(NC) 服务访问地址:"
	@echo "  - 前端界面: http://localhost:80"
	@echo "  - API 文档: http://localhost:8000/docs"
	@echo "  - Worker:   http://localhost:8001"
	@echo "  - MCP:      http://localhost:8002"
	@echo ""
	@echo "$(BLUE)[INFO]$(NC) 常用命令:"
	@echo "  - 查看状态: make status"
	@echo "  - 查看日志: make logs"
	@echo "  - 停止服务: make stop"
	@echo "  - 重启服务: make restart"
	@echo ""

version: ## 显示版本信息
	@echo "Tianshu (天枢) Docker 版本信息:"
	@echo "  Docker: $$(docker --version)"
	@echo "  Docker Compose: $$($(COMPOSE_CMD) version)"
	@$(COMPOSE_CMD) exec backend python --version || true

# ============================================================================
# 生产环境部署
# ============================================================================
pull: ## 拉取最新镜像
	@$(COMPOSE_CMD) pull

deploy: ## 部署更新（零停机）
	@echo "$(BLUE)[INFO]$(NC) 部署更新..."
	@$(COMPOSE_CMD) up -d --no-deps --build backend worker
	@echo "$(GREEN)[OK]$(NC) 部署完成"

validate: ## 验证配置文件
	@$(COMPOSE_CMD) config
