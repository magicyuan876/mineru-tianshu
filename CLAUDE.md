# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Tianshu (天枢) is an enterprise-grade AI data preprocessing platform that converts unstructured data (documents, images, audio, video) into AI-ready structured formats (Markdown/JSON). Built with Vue 3 frontend + FastAPI backend + LitServe GPU load balancing.

## Common Commands

### Docker Deployment (Recommended)
```bash
make setup          # Full deployment: config + build + start
make start          # Start all services
make stop           # Stop all services
make logs           # View all logs
make status         # Check service status
make build          # Build Docker images
make dev            # Start development environment (docker-compose.dev.yml)
```

### Local Development

**Backend:**
```bash
cd backend
pip install -r requirements.txt
python start_all.py                    # Start all services
python start_all.py --enable-mcp       # With MCP protocol
python start_all.py --workers-per-device 2 --devices 0,1  # Custom GPU config
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev         # Development server at localhost:3000
npm run build       # tsc type-check + Vite build (output in dist/)
npm run preview     # Preview the production build locally
```

### Linting & Tests
- **Python**: Ruff is configured at the repo root in `pyproject.toml` (target py312, line-length 120, rules `E`+`F`, ignores `E402`/`E501`). Run `ruff check .` / `ruff format .`. Ruff is a dev/pre-commit tool, not in `requirements.txt`.
- **Frontend**: type-checking happens via `tsc` inside `npm run build` (strict mode). No ESLint/Prettier configured.
- **Tests**: there is currently **no test framework** in either backend (no pytest/conftest) or frontend (no Vitest/Jest). Do not assume a test runner exists — verify before claiming tests pass.

### Service Ports
- Frontend: http://localhost:80 (Docker) or http://localhost:3000 (dev)
- API: http://localhost:8000 (OpenAPI docs at /docs)
- Worker: http://localhost:8001
- MCP: http://localhost:8002

## Architecture

### Process Orchestration (start_all.py)

`backend/start_all.py` (`TianshuLauncher`) loads `.env` first (exits if missing), then spawns processes **in strict order**, each as a subprocess waited on for readiness:
1. API Server (8000) → 2. LitServe Worker Pool (8001, ~5s wait) → 3. Task Scheduler (optional, monitoring/stale-reset only) → 4. MCP Server (optional, 8002, `--enable-mcp`).

All processes must share the same `OUTPUT_PATH` and `DATABASE_PATH`. Graceful shutdown via SIGINT/SIGTERM.

### Core Task Flow

Submission → claim → process → result spans several files:
1. **Submit** (`api_server.py`): `POST /api/v1/tasks/submit` → `db.create_task()` inserts row with `status='pending'`.
2. **Claim** (`task_db.py`): each worker loop calls `get_next_task(worker_id)` — atomically `SELECT ... WHERE status='pending' ORDER BY priority DESC, created_at ASC LIMIT 1` then flips to `processing` in one transaction (retries on conflict). Uses Redis `BZPOPMIN` first when `REDIS_QUEUE_ENABLED`, else SQLite `BEGIN IMMEDIATE`.
3. **Process** (`litserve_worker.py`): worker auto-loop (daemon thread, **enabled by default** — the scheduler is mostly monitoring) routes by backend param + file type to the right engine.
4. **Result**: `update_task_status(..., 'completed', data=json.dumps({pdf_path, json_content, markdown}))`. Results live in the `data` column **as a JSON string** — deserialize before use. Fetch via `GET /api/v1/tasks/{task_id}`.

### Backend Services (backend/)

Three main processes work together:

1. **api_server.py** - FastAPI REST API
   - Handles file uploads, task submission, status queries
   - JWT authentication + API key support
   - Routes under `/api/v1/`

2. **litserve_worker.py** - GPU Worker Pool
   - Uses LitServe for GPU load balancing
   - Workers actively poll tasks from SQLite (0.5s interval)
   - Supports MinerU, PaddleOCR-VL, SenseVoice engines
   - Handles document/image/audio/video processing

3. **task_db.py** - Hybrid task queue (SQLite + Redis)
   - SQLite: Task metadata storage, history, results
   - Redis (optional): High-performance queue for task claiming
   - Atomic task claiming with `BEGIN IMMEDIATE` (SQLite) or `BZPOPMIN` (Redis)
   - Task states: pending → processing → completed/failed

4. **redis_queue.py** - Redis queue module (optional)
   - Priority queue using Redis Sorted Sets
   - Enables horizontal scaling and higher throughput (10K+ QPS)
   - Graceful fallback to SQLite when Redis unavailable

**Processing Engines** (in backend/, dispatched from `litserve_worker.py`):
- `mineru_pipeline/engine.py` - `MinerUPipelineEngine`, singleton with GPU auto-sleep (~5min idle) + VRAM monitoring. Document backends: `pipeline`, `vlm-transformers`, `vlm-vllm-engine`, `hybrid-*`.
- `paddleocr_vl/` - Multi-language OCR. Optional vLLM mode via `--paddleocr-vl-vllm-engine-enabled` + `--paddleocr-vl-vllm-api-list`.
- `audio_engines/` - SenseVoice for speech recognition
- `video_engines/` - FFmpeg + keyframe OCR
- `format_engines/` - registry pattern (`base.py`); FASTA/GenBank engines registered in `litserve_worker.py`
- `remove_watermark/` - YOLO11x + LaMa watermark removal

**Engine gotchas:**
- **GPU isolation**: each worker gets its own `CUDA_VISIBLE_DEVICES`, so a worker sees only one GPU even when several are assigned.
- **vLLM containers** (`tianshu-vllm-paddleocr`, `tianshu-vllm-mineru`) are mutually exclusive — only one runs at a time (managed by `VLLMController`).
- **PDF splitting**: when `PDF_SPLIT_ENABLED=true`, large PDFs (`PDF_SPLIT_THRESHOLD_PAGES`, chunk `PDF_SPLIT_CHUNK_SIZE`) become child tasks with `parent_task_id`; the parent waits for all children, then merges results.
- **Models**: MinerU uses `MINERU_MODEL_SOURCE` (modelscope/huggingface, `HF_ENDPOINT` mirror supported); PaddleOCR auto-downloads to `~/.paddleocr/models/` (~2GB) on first use. `Dockerfile.offline` preloads from `OFFLINE_MODELS_PATH`.

**MCP server** (`mcp_server.py`, port 8002, standalone): SSE transport, exposes `parse_document`, `get_task_status`, `list_tasks`, `get_queue_stats`; proxies to the API server at `API_BASE_URL`.

### Frontend (frontend/src/)

Vue 3 + TypeScript + Composition API:

- `api/` - Axios client and typed API wrappers
- `stores/` - Pinia stores (auth, tasks, queue)
- `views/` - Page components (Dashboard, TaskList, TaskDetail, etc.)
- `components/` - Reusable UI components
- `router/` - Vue Router with auth guards

**API client** (`src/api/client.ts`): Axios instance, 5min timeout. Base URL resolution: `VITE_API_BASE_URL` env → production auto-detects domain + `VITE_API_PORT` (default 8000) → dev `http://localhost:8000`. Request interceptor reads the JWT from `localStorage` (`auth_token` or `token`) and sets `Authorization: Bearer`; all routes are normalized to `/api/v1/...`. Response interceptor clears the token and redirects to `/login` on 401. Env files: `.env.development` → `http://127.0.0.1:8000`, `.env.production` → `/api` (relative, served by Nginx).

**Dev proxy / Nginx**: Vite dev server proxies `/api` → `localhost:8000`. In Docker, the frontend Nginx (config inlined in `frontend/Dockerfile`) handles Vue Router history mode (`try_files ... /index.html`), proxies `/api/` and `/ws/` to `backend:8000` (strips `/api`), and caps uploads via `NGINX_CLIENT_MAX_BODY_SIZE` (default 0 = unlimited). The backend has matching middleware (`api_server.py`) that re-inserts the `/api/` prefix Nginx strips.

### Authentication

JWT-based authentication in `backend/auth/`:
- `jwt_handler.py` - Token creation/validation
- `dependencies.py` - FastAPI dependency injection
- `routes.py` - Login/register endpoints
- `sso.py` - OIDC/SAML integration (optional)

## Key Configuration

Environment variables (copy `.env.example` to `.env`):
```bash
JWT_SECRET_KEY=...     # Required for production
API_PORT=8000
WORKERS_PER_DEVICE=2
GPU_DEVICES=0
DATABASE_PATH=/app/data/db/mineru_tianshu.db

# Redis Queue (optional - for high concurrency)
REDIS_QUEUE_ENABLED=true   # Enable Redis queue
REDIS_HOST=localhost       # Redis host (use 'redis' in Docker)
REDIS_PORT=6379

# Output & frontend / Nginx
OUTPUT_PATH=/app/data/output      # Must match across all backend processes
FRONTEND_PORT=80
VITE_API_PORT=8000                # Backend port the frontend targets in production
NGINX_CLIENT_MAX_BODY_SIZE=0      # Upload size limit (0 = unlimited)
```

Dockerfile variants: `Dockerfile` (GPU, CUDA 12.1), `Dockerfile.cpu` (CPU-only), `Dockerfile.offline` (preloaded models, no download).

## API Endpoints

Main task endpoints:
- `POST /api/v1/tasks/submit` - Submit file for processing
- `GET /api/v1/tasks/{task_id}` - Get task status/result
- `DELETE /api/v1/tasks/{task_id}` - Cancel task
- `GET /api/v1/queue/stats` - Queue statistics
- `POST /api/v1/admin/reset-stale` - Reset stuck tasks

## Database

SQLite database (`mineru_tianshu.db`) with tasks table. Key fields:
- task_id, file_name, status, priority, backend, result_path, user_id
- Concurrent access handled via short-lived connections and timeouts
