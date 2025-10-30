#!/bin/bash
# Tianshu (天枢) - Docker 常用命令参�?
# 这个文件包含了常用的 Docker 操作命令，不是可执行脚本

# ============================================================================
# 构建镜像
# ============================================================================

# 构建所有镜像（并行构建�?
docker-compose build --parallel

# 仅构建后端镜�?
docker-compose build backend

# 仅构建前端镜�?
docker-compose build frontend

# 强制重新构建（不使用缓存�?
docker-compose build --no-cache

# ============================================================================
# 启动服务
# ============================================================================

# 启动所有服务（后台运行�?
docker-compose up -d

# 启动所有服务（前台运行，查看日志）
docker-compose up

# 启动特定服务
docker-compose up -d backend worker

# 启动开发环�?
docker-compose -f docker-compose.dev.yml up -d

# ============================================================================
# 停止服务
# ============================================================================

# 停止所有服务（保留容器�?
docker-compose stop

# 停止并删除容�?
docker-compose down

# 停止并删除容器、卷、网�?
docker-compose down -v

# 停止特定服务
docker-compose stop backend

# ============================================================================
# 重启服务
# ============================================================================

# 重启所有服�?
docker-compose restart

# 重启特定服务
docker-compose restart backend

# 重新加载配置（不停机�?
docker-compose up -d --force-recreate --no-deps backend

# ============================================================================
# 查看状态和日志
# ============================================================================

# 查看所有服务状�?
docker-compose ps

# 查看所有服务日�?
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f backend

# 查看最�?100 行日�?
docker-compose logs --tail=100 backend

# 查看实时日志（带时间戳）
docker-compose logs -f --timestamps backend

# ============================================================================
# 进入容器
# ============================================================================

# 进入后端容器
docker-compose exec backend bash

# 进入 Worker 容器
docker-compose exec worker bash

# �?root 身份进入
docker-compose exec -u root backend bash

# 执行单个命令
docker-compose exec backend python --version

# ============================================================================
# 调试和测�?
# ============================================================================

# 检�?GPU 是否可用
docker-compose exec worker nvidia-smi

# 测试 PyTorch CUDA
docker-compose exec worker python -c "import torch; print('CUDA:', torch.cuda.is_available())"

# 测试 PaddlePaddle CUDA
docker-compose exec worker python -c "import paddle; print('CUDA:', paddle.device.is_compiled_with_cuda())"

# 查看环境变量
docker-compose exec backend env

# 查看磁盘使用
docker-compose exec backend df -h

# ============================================================================
# 数据管理
# ============================================================================

# 备份数据�?
docker-compose exec backend cp mineru_tianshu.db mineru_tianshu.db.backup

# 从宿主机复制文件到容�?
docker cp local_file.txt mineru-backend:/app/

# 从容器复制文件到宿主�?
docker cp mineru-backend:/app/logs/backend.log ./

# 清理未使用的 Docker 资源
docker system prune -a

# ============================================================================
# 性能监控
# ============================================================================

# 查看容器资源使用
docker stats

# 查看特定容器资源使用
docker stats mineru-backend mineru-worker

# 查看容器内存限制
docker-compose exec backend cat /sys/fs/cgroup/memory/memory.limit_in_bytes

# ============================================================================
# 网络调试
# ============================================================================

# 查看网络
docker network ls

# 查看网络详情
docker network inspect mineru-network

# 测试容器间连�?
docker-compose exec backend ping worker

# 测试外部连接
docker-compose exec backend curl -I https://www.google.com

# ============================================================================
# 镜像管理
# ============================================================================

# 查看本地镜像
docker images | grep tianshu

# 删除镜像
docker rmi tianshu-backend:latest

# 导出镜像
docker save -o tianshu-backend.tar tianshu-backend:latest

# 导入镜像
docker load -i tianshu-backend.tar

# 推送到私有仓库
docker tag tianshu-backend:latest registry.company.com/tianshu-backend:latest
docker push registry.company.com/tianshu-backend:latest

# ============================================================================
# 故障排查
# ============================================================================

# 查看容器详细信息
docker inspect tianshu-backend

# 查看容器启动命令
docker inspect tianshu-backend | grep -A 10 "Cmd"

# 查看容器环境变量
docker inspect tianshu-backend | grep -A 20 "Env"

# 查看容器挂载�?
docker inspect tianshu-backend | grep -A 10 "Mounts"

# 强制删除异常容器
docker rm -f tianshu-backend

# 清理所有停止的容器
docker container prune

# 清理所有未使用的卷
docker volume prune

# ============================================================================
# 生产环境部署
# ============================================================================

# 拉取最新镜�?
docker-compose pull

# 滚动更新（零停机�?
docker-compose up -d --no-deps --build backend

# 查看服务健康状�?
docker-compose ps | grep "healthy"

# 设置服务副本数量（需�?Swarm 模式�?
docker service scale tianshu_backend=3

# ============================================================================
# 开发环境快捷操�?
# ============================================================================

# 重新构建并启动特定服�?
docker-compose up -d --build backend

# 查看构建过程
docker-compose build --progress=plain backend

# 使用特定配置文件
docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d

# 验证配置文件
docker-compose config

# ============================================================================
# Kubernetes 部署（进阶）
# ============================================================================

# 生成 Kubernetes 配置
# kompose convert -f docker-compose.yml

# 部署�?Kubernetes
# kubectl apply -f .

# 查看 Pod 状�?
# kubectl get pods

# 查看服务
# kubectl get services

# ============================================================================
# 注意事项
# ============================================================================
# 1. 确保 .env 文件已正确配�?
# 2. GPU 支持需要安�?NVIDIA Container Toolkit
# 3. 生产环境建议使用 docker-compose.yml
# 4. 开发环境使�?docker-compose.dev.yml
# 5. 定期备份 data/ �?models/ 目录
# 6. 监控磁盘空间，定期清理日志和临时文件
