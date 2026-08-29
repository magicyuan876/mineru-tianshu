#!/usr/bin/env bash
# ============================================================================
# Tianshu - Pipeline-only one-click deployment
#
# Deploys the stack with MinerU "pipeline" as the only parsing engine:
#   - vllm-paddleocr is NOT started (frees ~60% of GPU VRAM)
#   - only PDF-Extract-Kit models are downloaded (saves ~4GB)
#   - worker concurrency and per-worker VRAM budget are wired up from .env
#
# Companion file: docker-compose.pipeline.yml (override on docker-compose.yml)
# ============================================================================

set -euo pipefail

# ----------------------------------------------------------------------------
# Output helpers
# ----------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

usage() {
    cat << 'USAGE'
Tianshu - Pipeline-only deployment

Usage:
  ./scripts/deploy-pipeline.sh [action] [options]

Actions:
  deploy      Check deps, prepare .env, build images, start services (default)
  start       Start services without rebuilding
  stop        Stop services (containers kept)
  down        Stop and remove containers (volumes kept)
  restart     Restart services
  status      Show service status
  logs        Follow logs of all services
  verify      Run the post-deploy health checks only

Options:
  -c, --concurrency N   Worker processes per GPU (default: keep .env value, else 1)
  -g, --gpus N          GPUs exposed to the worker (default: detected on first run)
      --vram GB         Per-worker VRAM budget (default: per-GPU VRAM / concurrency)
      --no-build        Skip the image build step
      --skip-checks     Skip Docker / NVIDIA dependency checks
  -h, --help            Show this help

Concurrency model:
  concurrent tasks = GPU_COUNT x MAX_CONCURRENT_TASKS

Examples:
  ./scripts/deploy-pipeline.sh                          # single GPU, 1 task at a time
  ./scripts/deploy-pipeline.sh -g 2 -c 2                # 2 GPUs x 2 workers = 4 tasks
  ./scripts/deploy-pipeline.sh start --no-build         # restart without rebuilding
USAGE
}

# ----------------------------------------------------------------------------
# Defaults / argument parsing
# ----------------------------------------------------------------------------
ACTION="deploy"
OPT_CONCURRENCY=""
OPT_GPUS=""
OPT_VRAM=""
DO_BUILD=1
DO_CHECKS=1
ENV_CREATED=0
MIN_VRAM_PER_WORKER=6

while [ $# -gt 0 ]; do
    case "$1" in
        deploy | start | stop | down | restart | status | logs | verify)
            ACTION="$1"
            shift
            ;;
        -c | --concurrency)
            OPT_CONCURRENCY="${2:-}"
            shift 2
            ;;
        -g | --gpus)
            OPT_GPUS="${2:-}"
            shift 2
            ;;
        --vram)
            OPT_VRAM="${2:-}"
            shift 2
            ;;
        --no-build)
            DO_BUILD=0
            shift
            ;;
        --skip-checks)
            DO_CHECKS=0
            shift
            ;;
        -h | --help)
            usage
            exit 0
            ;;
        *)
            log_error "Unknown argument: $1"
            echo "Run '$0 --help' for usage."
            exit 1
            ;;
    esac
done

# Move to the project root so every relative path below resolves
cd "$(dirname "$0")/.." || exit 1

# ----------------------------------------------------------------------------
# Compose command
# ----------------------------------------------------------------------------
if docker compose version > /dev/null 2>&1; then
    DC=(docker compose)
    COMPOSE_BIN=(docker compose)
elif command -v docker-compose > /dev/null 2>&1; then
    DC=(docker-compose)
    COMPOSE_BIN=(docker-compose)
else
    log_error "Docker Compose not found. See https://docs.docker.com/compose/install/"
    exit 1
fi

DC+=(-f docker-compose.yml -f docker-compose.pipeline.yml)

# Activate the redis profile up-front so stop/logs/status see those containers too
if [ -f .env ] && grep -qE '^REDIS_QUEUE_ENABLED=true' .env; then
    DC+=(--profile redis)
fi

# ----------------------------------------------------------------------------
# .env helpers
# ----------------------------------------------------------------------------
get_env_key() {
    local key="$1"
    if [ ! -f .env ]; then
        return 0
    fi
    grep -E "^${key}=" .env | head -n1 | cut -d= -f2- || true
}

set_env_key() {
    local key="$1"
    local val="$2"
    if grep -qE "^${key}=" .env; then
        sed -i "s|^${key}=.*|${key}=${val}|" .env
    else
        printf '%s=%s\n' "$key" "$val" >> .env
    fi
}

# ----------------------------------------------------------------------------
# Detection
# ----------------------------------------------------------------------------
detect_gpu_count() {
    local n
    n=$(nvidia-smi -L 2> /dev/null | grep -c '^GPU ' || true)
    echo "${n:-0}"
}

# Smallest per-GPU VRAM in GB, so the budget stays safe on mixed-GPU hosts
detect_min_vram_gb() {
    local mib
    mib=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2> /dev/null \
        | tr -d ' ' | sort -n | head -n1 || true)
    if [ -z "$mib" ]; then
        echo 0
    else
        echo $((mib / 1024))
    fi
}

detect_server_ip() {
    local ip=""
    if command -v ip > /dev/null 2>&1; then
        ip=$(ip route get 1.1.1.1 2> /dev/null \
            | awk '{for (i = 1; i <= NF; i++) if ($i == "src") print $(i + 1)}' | head -n1 || true)
    fi
    if [ -z "$ip" ] && command -v hostname > /dev/null 2>&1; then
        ip=$(hostname -I 2> /dev/null | awk '{print $1}' || true)
    fi
    echo "$ip"
}

container_running() {
    docker ps --filter "name=$1" --filter "status=running" --format '{{.Names}}' 2> /dev/null \
        | grep -q "$1"
}

# ----------------------------------------------------------------------------
# Dependency checks
# ----------------------------------------------------------------------------
check_dependencies() {
    log_info "Checking dependencies..."

    if ! command -v docker > /dev/null 2>&1; then
        log_error "Docker is not installed. See https://docs.docker.com/get-docker/"
        exit 1
    fi
    log_success "Docker: $(docker --version)"
    log_success "Compose: $("${COMPOSE_BIN[@]}" version 2> /dev/null | head -n1)"

    if ! command -v nvidia-smi > /dev/null 2>&1; then
        log_error "nvidia-smi not found, but the MinerU pipeline engine needs a GPU."
        log_error "For a CPU-only host use docker-compose.cpu.yml instead."
        exit 1
    fi
    log_success "NVIDIA driver present:"
    nvidia-smi --query-gpu=index,name,memory.total --format=csv,noheader || true

    if docker run --rm --gpus all nvidia/cuda:12.6.2-base-ubuntu22.04 nvidia-smi > /dev/null 2>&1; then
        log_success "NVIDIA Container Toolkit works inside Docker"
    else
        log_error "Docker cannot access the GPU (NVIDIA Container Toolkit missing or misconfigured)."
        log_error "Guide: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html"
        exit 1
    fi
}

# ----------------------------------------------------------------------------
# Environment preparation
# ----------------------------------------------------------------------------
prepare_env() {
    if [ ! -f .env ]; then
        if [ ! -f .env.example ]; then
            log_error ".env.example not found, cannot create .env"
            exit 1
        fi
        cp .env.example .env
        ENV_CREATED=1
        log_success ".env created from .env.example"
    else
        log_info ".env exists - only the pipeline-related keys will be updated"
    fi
}

tune_env() {
    local detected_gpus
    local min_vram
    detected_gpus=$(detect_gpu_count)
    min_vram=$(detect_min_vram_gb)

    # --- JWT secret ---------------------------------------------------------
    local jwt
    jwt=$(get_env_key JWT_SECRET_KEY)
    case "$jwt" in
        "" | your-secret-key-change-in-production | CHANGE_THIS_TO_A_SECURE_RANDOM_STRING_IN_PRODUCTION)
            if command -v openssl > /dev/null 2>&1; then
                set_env_key JWT_SECRET_KEY "$(openssl rand -hex 32)"
                log_success "JWT_SECRET_KEY generated"
            else
                log_warning "openssl missing - set JWT_SECRET_KEY in .env manually before exposing this host"
            fi
            ;;
        *)
            log_info "JWT_SECRET_KEY already customised, left untouched"
            ;;
    esac

    # --- GPU count ----------------------------------------------------------
    local gpu_count
    if [ -n "$OPT_GPUS" ]; then
        gpu_count="$OPT_GPUS"
        set_env_key GPU_COUNT "$gpu_count"
        log_success "GPU_COUNT = ${gpu_count} (from --gpus)"
    elif [ "$ENV_CREATED" -eq 1 ] && [ "$detected_gpus" -gt 0 ]; then
        gpu_count="$detected_gpus"
        set_env_key GPU_COUNT "$gpu_count"
        log_success "GPU_COUNT = ${gpu_count} (detected)"
    else
        gpu_count=$(get_env_key GPU_COUNT)
        gpu_count="${gpu_count:-1}"
        log_info "GPU_COUNT = ${gpu_count} (kept; host has ${detected_gpus} GPU(s))"
        if [ "$detected_gpus" -gt "$gpu_count" ]; then
            log_warning "Only ${gpu_count}/${detected_gpus} GPUs will be used - pass --gpus ${detected_gpus} to use all."
        fi
    fi

    # --- Worker concurrency -------------------------------------------------
    # NOTE: litserve_worker.py ignores --workers-per-device and reads
    # MAX_CONCURRENT_TASKS instead, so this env var is the only real knob.
    local concurrency
    if [ -n "$OPT_CONCURRENCY" ]; then
        concurrency="$OPT_CONCURRENCY"
    else
        concurrency=$(get_env_key MAX_CONCURRENT_TASKS)
        concurrency="${concurrency:-1}"
    fi
    if ! [ "$concurrency" -ge 1 ] 2> /dev/null; then
        log_error "Invalid concurrency value: ${concurrency}"
        exit 1
    fi
    set_env_key MAX_CONCURRENT_TASKS "$concurrency"
    log_success "MAX_CONCURRENT_TASKS = ${concurrency} (worker processes per GPU)"

    # --- Per-worker VRAM budget --------------------------------------------
    # MinerU sizes its batches from MINERU_VIRTUAL_VRAM_SIZE and every worker
    # process applies it independently, so co-located workers must split the card.
    local vram
    if [ -n "$OPT_VRAM" ]; then
        vram="$OPT_VRAM"
    elif [ "$min_vram" -gt 0 ]; then
        vram=$((min_vram / concurrency))
        if [ "$vram" -lt "$MIN_VRAM_PER_WORKER" ]; then
            vram="$MIN_VRAM_PER_WORKER"
        fi
    else
        vram=8
    fi
    set_env_key MINERU_VIRTUAL_VRAM_SIZE "$vram"
    log_success "MINERU_VIRTUAL_VRAM_SIZE = ${vram} GB per worker (card has ${min_vram} GB)"

    if [ "$min_vram" -gt 0 ] && [ $((vram * concurrency)) -gt "$min_vram" ]; then
        log_warning "VRAM over-committed (${vram} x ${concurrency} > ${min_vram} GB) - lower --concurrency or --vram if you hit CUDA OOM."
    fi

    # --- RustFS public URL --------------------------------------------------
    # Parsed images are rewritten to absolute URLs using this value, so it must
    # be reachable from the user's browser, not from inside the container.
    local rustfs_url
    local rustfs_port
    local server_ip
    rustfs_url=$(get_env_key RUSTFS_PUBLIC_URL)
    rustfs_port=$(get_env_key RUSTFS_PORT)
    rustfs_port="${rustfs_port:-9000}"
    server_ip=$(detect_server_ip)

    case "$rustfs_url" in
        "" | *192.168.1.100*)
            if [ -n "$server_ip" ]; then
                set_env_key RUSTFS_PUBLIC_URL "http://${server_ip}:${rustfs_port}"
                log_success "RUSTFS_PUBLIC_URL = http://${server_ip}:${rustfs_port}"
            else
                log_warning "Server IP not detected - set RUSTFS_PUBLIC_URL in .env manually,"
                log_warning "otherwise images in the parsed output will not load in the browser."
            fi
            ;;
        *)
            log_info "RUSTFS_PUBLIC_URL already set (${rustfs_url}), left untouched"
            ;;
    esac

    # --- Worker memory sanity ----------------------------------------------
    if [ "$concurrency" -gt 1 ]; then
        local mem_limit
        mem_limit=$(get_env_key WORKER_MEMORY_LIMIT)
        log_warning "WORKER_MEMORY_LIMIT is ${mem_limit:-16G} for ${concurrency} worker processes."
        log_warning "Budget roughly 8-10G per worker; raise it in .env if the worker gets OOM-killed."
    fi
}

create_directories() {
    log_info "Creating host directories..."
    mkdir -p models models/paddlex_cache models/paddleocr_cache \
        input output data/db \
        logs/backend logs/worker logs/mcp logs/scheduler
    log_success "Directories ready"
}

# ----------------------------------------------------------------------------
# Build / run
# ----------------------------------------------------------------------------
build_images() {
    log_info "Building images (the first build pulls ~4GB of wheels, 10-30 min)..."
    DOCKER_BUILDKIT=1 COMPOSE_DOCKER_CLI_BUILD=1 "${DC[@]}" build --parallel
    log_success "Images built"
}

start_services() {
    log_info "Starting services (pipeline-only)..."
    "${DC[@]}" up -d
    log_success "Containers started"
    log_info "init-models downloads PDF-Extract-Kit on first run; the worker waits for it."
}

# ----------------------------------------------------------------------------
# Verification
# ----------------------------------------------------------------------------
verify_deployment() {
    local api_port
    local frontend_port
    local rc=0
    api_port=$(get_env_key API_PORT)
    api_port="${api_port:-8000}"
    frontend_port=$(get_env_key FRONTEND_PORT)
    frontend_port="${frontend_port:-80}"

    log_info "Waiting for the API to report healthy (up to 180s)..."
    local ok=0
    local waited=0
    while [ "$waited" -lt 180 ]; do
        if curl -fsS "http://localhost:${api_port}/api/v1/health" > /dev/null 2>&1; then
            ok=1
            break
        fi
        sleep 3
        waited=$((waited + 3))
    done

    if [ "$ok" -eq 1 ]; then
        log_success "API healthy on port ${api_port}"
    else
        log_error "API never became healthy. Inspect: ${DC[*]} logs backend"
        return 1
    fi

    # The browser talks to the API through nginx in the frontend container.
    # That is a different path than the one checked above, so test it explicitly.
    if curl -fsS "http://localhost:${frontend_port}/api/v1/health" > /dev/null 2>&1; then
        log_success "Frontend -> API proxy healthy on port ${frontend_port}"
    else
        log_error "nginx cannot reach the API: /api/v1/health failed on port ${frontend_port}."
        log_error "Every UI request will fail. Check 'location /api/' proxy_pass in frontend/Dockerfile,"
        log_error "then: ${DC[*]} build frontend && ${DC[*]} up -d frontend"
        rc=1
    fi

    if container_running tianshu-worker; then
        log_success "Worker container running"
    else
        log_warning "Worker not running yet (it waits for init-models to finish)."
        log_warning "Follow it with: ${DC[*]} logs -f init-models worker"
    fi

    if container_running tianshu-vllm-paddleocr; then
        log_warning "vllm-paddleocr is running - it should stay down in pipeline mode."
        log_warning "Stop it with: docker stop tianshu-vllm-paddleocr"
        rc=1
    else
        log_success "vllm-paddleocr is down (as intended)"
    fi

    return "$rc"
}

show_info() {
    local api_port
    local frontend_port
    local gpu_count
    local concurrency
    local server_ip
    api_port=$(get_env_key API_PORT)
    api_port="${api_port:-8000}"
    frontend_port=$(get_env_key FRONTEND_PORT)
    frontend_port="${frontend_port:-80}"
    gpu_count=$(get_env_key GPU_COUNT)
    gpu_count="${gpu_count:-1}"
    concurrency=$(get_env_key MAX_CONCURRENT_TASKS)
    concurrency="${concurrency:-1}"
    server_ip=$(detect_server_ip)
    server_ip="${server_ip:-localhost}"

    echo ""
    log_success "=========================================="
    log_success " Tianshu (pipeline-only) is up"
    log_success "=========================================="
    echo ""
    echo "  Web UI:   http://${server_ip}:${frontend_port}"
    echo "  API docs: http://${server_ip}:${api_port}/docs"
    echo "  Engine:   MinerU pipeline (submit tasks with backend=\"pipeline\")"
    echo "  Capacity: ${gpu_count} GPU x ${concurrency} worker = $((gpu_count * concurrency)) concurrent task(s)"
    echo ""
    echo "  Logs:     $0 logs"
    echo "  Status:   $0 status"
    echo "  Stop:     $0 stop"
    echo ""
    log_warning "No admin user is seeded - register the first account from the Web UI."
    echo ""
}

# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
case "$ACTION" in
    deploy)
        if [ "$DO_CHECKS" -eq 1 ]; then
            check_dependencies
        fi
        prepare_env
        tune_env
        create_directories
        if [ "$DO_BUILD" -eq 1 ]; then
            build_images
        fi
        start_services
        if ! verify_deployment; then
            log_warning "Deployment finished with warnings - see the messages above."
        fi
        show_info
        ;;
    start)
        prepare_env
        tune_env
        start_services
        verify_deployment || true
        show_info
        ;;
    stop)
        "${DC[@]}" stop
        log_success "Services stopped"
        ;;
    down)
        "${DC[@]}" down
        log_success "Containers removed (volumes kept)"
        ;;
    restart)
        "${DC[@]}" restart
        log_success "Services restarted"
        ;;
    status)
        "${DC[@]}" ps
        ;;
    logs)
        "${DC[@]}" logs -f
        ;;
    verify)
        verify_deployment
        ;;
    *)
        log_error "Unknown action: ${ACTION}"
        exit 1
        ;;
esac
