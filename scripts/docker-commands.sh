#!/bin/bash
# Tianshu - Docker Common Commands Reference
# This file contains common Docker operation commands, not an executable script

# ============================================================================
# Build images
# ============================================================================

# Build all images (parallel build)
docker-compose build --parallel

# Build backend image only
docker-compose build backend

# Build frontend image only
docker-compose build frontend

# Force rebuild (no cache)
docker-compose build --no-cache

# ============================================================================
# Start services
# ============================================================================

# Start all services (background)
docker-compose up -d

# Start all services (foreground, view logs)
docker-compose up

# Start specific services
docker-compose up -d backend worker

# Start development environment
docker-compose -f docker-compose.dev.yml up -d

# ============================================================================
# Stop services
# ============================================================================

# Stop all services (keep containers)
docker-compose stop

# Stop and remove containers
docker-compose down

# Stop and remove containers, volumes, networks
docker-compose down -v

# Stop specific service
docker-compose stop backend

# ============================================================================
# Restart services
# ============================================================================

# Restart all services
docker-compose restart

# Restart specific service
docker-compose restart backend

# Reload configuration (zero downtime)
docker-compose up -d --force-recreate --no-deps backend

# ============================================================================
# View status and logs
# ============================================================================

# View all service status
docker-compose ps

# View all service logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend

# View last 100 lines of logs
docker-compose logs --tail=100 backend

# View real-time logs (with timestamps)
docker-compose logs -f --timestamps backend

# ============================================================================
# Enter container
# ============================================================================

# Enter backend container
docker-compose exec backend bash

# Enter Worker container
docker-compose exec worker bash

# Enter as root user
docker-compose exec -u root backend bash

# Execute single command
docker-compose exec backend python --version

# ============================================================================
# Debug and test
# ============================================================================

# Check if GPU is available
docker-compose exec worker nvidia-smi

# Test PyTorch CUDA
docker-compose exec worker python -c "import torch; print('CUDA:', torch.cuda.is_available())"

# Test PaddlePaddle CUDA
docker-compose exec worker python -c "import paddle; print('CUDA:', paddle.device.is_compiled_with_cuda())"

# View environment variables
docker-compose exec backend env

# View disk usage
docker-compose exec backend df -h

# ============================================================================
# Data management
# ============================================================================

# Backup database
docker-compose exec backend cp mineru_tianshu.db mineru_tianshu.db.backup

# Copy file from host to container
docker cp local_file.txt mineru-backend:/app/

# Copy file from container to host
docker cp mineru-backend:/app/logs/backend.log ./

# Clean unused Docker resources
docker system prune -a

# ============================================================================
# Performance monitoring
# ============================================================================

# View container resource usage
docker stats

# View specific container resource usage
docker stats mineru-backend mineru-worker

# View container memory limit
docker-compose exec backend cat /sys/fs/cgroup/memory/memory.limit_in_bytes

# ============================================================================
# Network debugging
# ============================================================================

# View networks
docker network ls

# View network details
docker network inspect mineru-network

# Test inter-container connection
docker-compose exec backend ping worker

# Test external connection
docker-compose exec backend curl -I https://www.google.com

# ============================================================================
# Image management
# ============================================================================

# View local images
docker images | grep tianshu

# Delete image
docker rmi tianshu-backend:latest

# Export image
docker save -o tianshu-backend.tar tianshu-backend:latest

# Import image
docker load -i tianshu-backend.tar

# Push to private registry
docker tag tianshu-backend:latest registry.company.com/tianshu-backend:latest
docker push registry.company.com/tianshu-backend:latest

# ============================================================================
# Troubleshooting
# ============================================================================

# View container detailed information
docker inspect tianshu-backend

# View container startup command
docker inspect tianshu-backend | grep -A 10 "Cmd"

# View container environment variables
docker inspect tianshu-backend | grep -A 20 "Env"

# View container mounts
docker inspect tianshu-backend | grep -A 10 "Mounts"

# Force delete abnormal container
docker rm -f tianshu-backend

# Clean all stopped containers
docker container prune

# Clean all unused volumes
docker volume prune

# ============================================================================
# Production deployment
# ============================================================================

# Pull latest images
docker-compose pull

# Rolling update (zero downtime)
docker-compose up -d --no-deps --build backend

# View service health status
docker-compose ps | grep "healthy"

# Set service replica count (requires Swarm mode)
docker service scale tianshu_backend=3

# ============================================================================
# Development environment quick operations
# ============================================================================

# Rebuild and start specific service
docker-compose up -d --build backend

# View build process
docker-compose build --progress=plain backend

# Use specific config file
docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d

# Validate configuration file
docker-compose config

# ============================================================================
# Kubernetes deployment (advanced)
# ============================================================================

# Generate Kubernetes configuration
# kompose convert -f docker-compose.yml

# Deploy to Kubernetes
# kubectl apply -f .

# View Pod status
# kubectl get pods

# View services
# kubectl get services

# ============================================================================
# Notes
# ============================================================================
# 1. Ensure .env file is properly configured
# 2. GPU support requires NVIDIA Container Toolkit installation
# 3. Production environment recommends using docker-compose.yml
# 4. Development environment uses docker-compose.dev.yml
# 5. Regularly backup data/ and models/ directories
# 6. Monitor disk space, regularly clean logs and temporary files
