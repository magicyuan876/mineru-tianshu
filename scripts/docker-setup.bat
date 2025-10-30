@echo off
REM Tianshu (天枢) - Docker Quick Setup for Windows
REM Windows 用户快速部署脚本

setlocal enabledelayedexpansion

echo ========================================
echo    Tianshu (天枢) Docker 部署脚本
echo ========================================
echo.

REM 切换到项目根目录
cd /d "%~dp0\.."

REM ============================================================================
REM 检查 Docker
REM ============================================================================
:check_docker
echo [INFO] 检查 Docker...
docker --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker 未安装或未启动
    echo [INFO] 请先安装 Docker Desktop: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)
echo [OK] Docker 已安装

REM 检查 Docker Compose
docker-compose --version >nul 2>&1
if errorlevel 1 (
    docker compose version >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Docker Compose 未安装
        pause
        exit /b 1
    )
    set COMPOSE_CMD=docker compose
) else (
    set COMPOSE_CMD=docker-compose
)
echo [OK] Docker Compose 已安装
echo.

REM ============================================================================
REM 检查 NVIDIA GPU
REM ============================================================================
:check_gpu
echo [INFO] 检查 GPU 支持...
nvidia-smi >nul 2>&1
if errorlevel 1 (
    echo [WARNING] 未检测到 NVIDIA GPU，将以 CPU 模式运行
) else (
    echo [OK] 检测到 NVIDIA GPU
    nvidia-smi
)
echo.

REM ============================================================================
REM 主菜单
REM ============================================================================
:menu
echo.
echo ╔════════════════════════════════════════╗
echo ║         选择部署选项                   ║
echo ╚════════════════════════════════════════╝
echo.
echo   1. 全新部署（配置 + 构建 + 启动）
echo   2. 启动服务（生产环境）
echo   3. 启动服务（开发环境）
echo   4. 停止所有服务
echo   5. 重启服务
echo   6. 查看服务状态
echo   7. 查看日志
echo   8. 清理所有数据
echo   0. 退出
echo.
set /p choice="请输入选项 [0-8]: "

if "%choice%"=="1" goto full_setup
if "%choice%"=="2" goto start_prod
if "%choice%"=="3" goto start_dev
if "%choice%"=="4" goto stop
if "%choice%"=="5" goto restart
if "%choice%"=="6" goto status
if "%choice%"=="7" goto logs
if "%choice%"=="8" goto clean
if "%choice%"=="0" goto end
echo [ERROR] 无效选项
goto menu

REM ============================================================================
REM 全新部署
REM ============================================================================
:full_setup
echo.
echo [INFO] 开始全新部署...
echo.

REM 配置环境变量
if not exist .env (
    if exist .env.example (
        echo [INFO] 创建 .env 文件...
        copy .env.example .env >nul
        echo [OK] .env 文件已创建
        echo [WARNING] 请编辑 .env 文件，特别是 JWT_SECRET_KEY
        pause
    ) else (
        echo [ERROR] .env.example 文件不存在
        pause
        goto end
    )
) else (
    echo [OK] .env 文件已存在
)

REM 创建必要目录
echo [INFO] 创建目录结构...
if not exist models mkdir models
if not exist data\uploads mkdir data\uploads
if not exist data\output mkdir data\output
if not exist data\db mkdir data\db
if not exist logs\backend mkdir logs\backend
if not exist logs\worker mkdir logs\worker
if not exist logs\mcp mkdir logs\mcp
echo [OK] 目录结构创建完成

REM 构建镜像
echo.
echo [INFO] 构建 Docker 镜像（首次运行可能需要 10-30 分钟）...
echo [INFO] 请耐心等待...
%COMPOSE_CMD% build --parallel
if errorlevel 1 (
    echo [ERROR] 镜像构建失败
    pause
    goto end
)
echo [OK] 镜像构建完成

REM 启动服务
echo.
echo [INFO] 启动服务...
%COMPOSE_CMD% up -d
if errorlevel 1 (
    echo [ERROR] 服务启动失败
    pause
    goto end
)

echo.
echo [OK] 等待服务就绪...
timeout /t 10 /nobreak >nul

goto show_info

REM ============================================================================
REM 启动生产环境
REM ============================================================================
:start_prod
echo [INFO] 启动生产环境...
%COMPOSE_CMD% up -d
if errorlevel 1 (
    echo [ERROR] 服务启动失败
    pause
    goto menu
)
goto show_info

REM ============================================================================
REM 启动开发环境
REM ============================================================================
:start_dev
echo [INFO] 启动开发环境...
%COMPOSE_CMD% -f docker-compose.dev.yml up -d
if errorlevel 1 (
    echo [ERROR] 服务启动失败
    pause
    goto menu
)
goto show_info

REM ============================================================================
REM 停止服务
REM ============================================================================
:stop
echo [INFO] 停止服务...
%COMPOSE_CMD% down
echo [OK] 服务已停止
pause
goto menu

REM ============================================================================
REM 重启服务
REM ============================================================================
:restart
echo [INFO] 重启服务...
%COMPOSE_CMD% restart
echo [OK] 服务已重启
pause
goto menu

REM ============================================================================
REM 查看状态
REM ============================================================================
:status
echo [INFO] 服务状态:
echo.
%COMPOSE_CMD% ps
echo.
pause
goto menu

REM ============================================================================
REM 查看日志
REM ============================================================================
:logs
echo [INFO] 查看日志（按 Ctrl+C 退出）...
%COMPOSE_CMD% logs -f
goto menu

REM ============================================================================
REM 清理数据
REM ============================================================================
:clean
echo.
echo [WARNING] 此操作将删除所有数据（包括数据库、上传文件、模型）
set /p confirm="确认删除? (yes/no): "
if /i not "%confirm%"=="yes" (
    echo [INFO] 操作已取消
    pause
    goto menu
)

echo [INFO] 清理数据...
%COMPOSE_CMD% down -v
rmdir /s /q data 2>nul
rmdir /s /q logs 2>nul
rmdir /s /q models 2>nul
echo [OK] 数据已清理
pause
goto menu

REM ============================================================================
REM 显示访问信息
REM ============================================================================
:show_info
echo.
echo ==========================================
echo      Tianshu (天枢) 部署完成！
echo ==========================================
echo.
echo [INFO] 服务访问地址:
echo   - 前端界面: http://localhost:80
echo   - API 文档: http://localhost:8000/docs
echo   - Worker:   http://localhost:8001
echo   - MCP:      http://localhost:8002
echo.
echo [INFO] 常用命令:
echo   - 查看日志: docker-compose logs -f
echo   - 停止服务: docker-compose down
echo   - 重启服务: docker-compose restart
echo   - 查看状态: docker-compose ps
echo.
echo [WARNING] 首次运行时，模型会自动下载，这可能需要一些时间
echo [WARNING] 默认管理员账号需要通过注册页面创建
echo.
pause
goto menu

REM ============================================================================
REM 退出
REM ============================================================================
:end
echo [INFO] 退出
exit /b 0
