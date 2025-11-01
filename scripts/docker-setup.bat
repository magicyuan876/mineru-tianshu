@echo off
REM Tianshu - Docker Quick Setup for Windows
REM Quick deployment script for Windows users

setlocal enabledelayedexpansion

echo ========================================
echo    Tianshu Docker Setup Script
echo ========================================
echo.

REM Switch to project root directory
cd /d "%~dp0\.."

REM ============================================================================
REM Check Docker
REM ============================================================================
:check_docker
echo [INFO] Checking Docker...
docker --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not installed or not running
    echo [INFO] Please install Docker Desktop first: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)
echo [OK] Docker is installed

REM Check Docker Compose
docker-compose --version >nul 2>&1
if errorlevel 1 (
    docker compose version >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Docker Compose is not installed
        pause
        exit /b 1
    )
    set COMPOSE_CMD=docker compose
) else (
    set COMPOSE_CMD=docker-compose
)
echo [OK] Docker Compose is installed
echo.

REM ============================================================================
REM Check NVIDIA GPU
REM ============================================================================
:check_gpu
echo [INFO] Checking GPU support...
nvidia-smi >nul 2>&1
if errorlevel 1 (
    echo [WARNING] NVIDIA GPU not detected, will run in CPU mode
) else (
    echo [OK] NVIDIA GPU detected
    nvidia-smi
)
echo.

REM ============================================================================
REM Main Menu
REM ============================================================================
:menu
echo.
echo ========================================
echo    Select Deployment Option
echo ========================================
echo.
echo   1. Full Deployment (Setup + Build + Start)
echo   2. Start Services (Production)
echo   3. Start Services (Development)
echo   4. Stop All Services
echo   5. Restart Services
echo   6. View Service Status
echo   7. View Logs
echo   8. Clean All Data
echo   0. Exit
echo.
set /p choice="Please enter option [0-8]: "

if "%choice%"=="1" goto full_setup
if "%choice%"=="2" goto start_prod
if "%choice%"=="3" goto start_dev
if "%choice%"=="4" goto stop
if "%choice%"=="5" goto restart
if "%choice%"=="6" goto status
if "%choice%"=="7" goto logs
if "%choice%"=="8" goto clean
if "%choice%"=="0" goto end
echo [ERROR] Invalid option
goto menu

REM ============================================================================
REM Full Deployment
REM ============================================================================
:full_setup
echo.
echo [INFO] Starting full deployment...
echo.

REM Configure environment variables
if not exist .env (
    if exist .env.example (
        echo [INFO] Creating .env file...
        copy .env.example .env >nul
        echo [OK] .env file created
        echo [WARNING] Please edit .env file, especially JWT_SECRET_KEY
        pause
    ) else (
        echo [ERROR] .env.example file does not exist
        pause
        goto end
    )
) else (
    echo [OK] .env file already exists
)

REM Create necessary directories
echo [INFO] Creating directory structure...
if not exist models mkdir models
if not exist data\uploads mkdir data\uploads
if not exist data\output mkdir data\output
if not exist data\db mkdir data\db
if not exist logs\backend mkdir logs\backend
if not exist logs\worker mkdir logs\worker
if not exist logs\mcp mkdir logs\mcp
echo [OK] Directory structure created

REM Build images
echo.
echo [INFO] Building Docker images (first run may take 10-30 minutes)...
echo [INFO] Please wait patiently...
%COMPOSE_CMD% build --parallel
if errorlevel 1 (
    echo [ERROR] Image build failed
    pause
    goto end
)
echo [OK] Image build completed

REM Start services
echo.
echo [INFO] Starting services...
%COMPOSE_CMD% up -d
if errorlevel 1 (
    echo [ERROR] Service startup failed
    pause
    goto end
)

echo.
echo [OK] Waiting for services to be ready...
timeout /t 10 /nobreak >nul

goto show_info

REM ============================================================================
REM Start Production Environment
REM ============================================================================
:start_prod
echo [INFO] Starting production environment...
%COMPOSE_CMD% up -d
if errorlevel 1 (
    echo [ERROR] Service startup failed
    pause
    goto menu
)
goto show_info

REM ============================================================================
REM Start Development Environment
REM ============================================================================
:start_dev
echo [INFO] Starting development environment...
%COMPOSE_CMD% -f docker-compose.dev.yml up -d
if errorlevel 1 (
    echo [ERROR] Service startup failed
    pause
    goto menu
)
goto show_info

REM ============================================================================
REM Stop Services
REM ============================================================================
:stop
echo [INFO] Stopping services...
%COMPOSE_CMD% down
echo [OK] Services stopped
pause
goto menu

REM ============================================================================
REM Restart Services
REM ============================================================================
:restart
echo [INFO] Restarting services...
%COMPOSE_CMD% restart
echo [OK] Services restarted
pause
goto menu

REM ============================================================================
REM View Status
REM ============================================================================
:status
echo [INFO] Service status:
echo.
%COMPOSE_CMD% ps
echo.
pause
goto menu

REM ============================================================================
REM View Logs
REM ============================================================================
:logs
echo [INFO] Viewing logs (Press Ctrl+C to exit)...
%COMPOSE_CMD% logs -f
goto menu

REM ============================================================================
REM Clean Data
REM ============================================================================
:clean
echo.
echo [WARNING] This operation will delete all data (including database, uploaded files, models)
set /p confirm="Confirm deletion? (yes/no): "
if /i not "%confirm%"=="yes" (
    echo [INFO] Operation cancelled
    pause
    goto menu
)

echo [INFO] Cleaning data...
%COMPOSE_CMD% down -v
rmdir /s /q data 2>nul
rmdir /s /q logs 2>nul
rmdir /s /q models 2>nul
echo [OK] Data cleaned
pause
goto menu

REM ============================================================================
REM Show Access Information
REM ============================================================================
:show_info
echo.
echo ==========================================
echo      Tianshu Deployment Complete!
echo ==========================================
echo.
echo [INFO] Service access addresses:
echo   - Frontend:      http://localhost:80
echo   - API Docs:      http://localhost:8000/docs
echo   - Worker:        http://localhost:8001
echo   - MCP:           http://localhost:8002
echo.
echo [INFO] Common commands:
echo   - View logs:      docker-compose logs -f
echo   - Stop services: docker-compose down
echo   - Restart:       docker-compose restart
echo   - View status:   docker-compose ps
echo.
echo [WARNING] On first run, models will be automatically downloaded, this may take some time
echo [WARNING] Default admin account needs to be created via registration page
echo.
pause
goto menu

REM ============================================================================
REM Exit
REM ============================================================================
:end
echo [INFO] Exiting
exit /b 0
