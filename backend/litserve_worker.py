"""
MinerU Tianshu - LitServe Worker
天枢 LitServe Worker

企业级 AI 数据预处理平台 - GPU Worker
支持文档、图片、音频、视频等多模态数据处理
使用 LitServe 实现 GPU 资源的自动负载均衡
Worker 主动循环拉取任务并处理

优化日志 (2026-02-16):
1. [并发] 强制限制 workers_per_device=1 (可通过 MAX_CONCURRENT_TASKS 调整)，防止爆显存
2. [修复] 强制回写源 PDF 到 output 目录，解决前端无法预览源文件的问题
3. [修复] PaddleOCR/MinerU 返回结果中补全 json_content 和 pdf_path 以支持双向定位
4. [性能] 移除单次任务后的强制显存清理 (clean_memory)，依赖引擎的智能休眠机制
5. [稳定] 增强 VLLM 容器互斥切换的健壮性
"""

import os
import json
import sys
import time
import threading
import signal
import atexit
import shutil
import socket
import multiprocessing
import requests
import warnings
import subprocess
import tempfile
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

# ==============================================================================
# 1. LitServe MCP Patch (Disable Internal MCP)
# ==============================================================================
try:
    import litserve.mcp as ls_mcp

    if not hasattr(ls_mcp, "MCPServer"):
        class DummyMCPServer:
            def __init__(self, *args, **kwargs): pass
        ls_mcp.MCPServer = DummyMCPServer
        if "litserve.mcp" in sys.modules:
            sys.modules["litserve.mcp"].MCPServer = DummyMCPServer

    if not hasattr(ls_mcp, "StreamableHTTPSessionManager"):
        class DummyStreamableHTTPSessionManager:
            def __init__(self, *args, **kwargs): pass
        ls_mcp.StreamableHTTPSessionManager = DummyStreamableHTTPSessionManager
        if "litserve.mcp" in sys.modules:
            sys.modules["litserve.mcp"].StreamableHTTPSessionManager = DummyStreamableHTTPSessionManager

    class DummyMCPConnector:
        """完全禁用 LitServe 内置 MCP 的 Dummy 实现"""
        def __init__(self, *args, **kwargs):
            self.mcp_server = None
            self.session_manager = None
            self.request_handler = None

        @asynccontextmanager
        async def lifespan(self, app):
            yield

        def connect_mcp_server(self, *args, **kwargs):
            pass

    ls_mcp._LitMCPServerConnector = DummyMCPConnector
    if "litserve.mcp" in sys.modules:
        sys.modules["litserve.mcp"]._LitMCPServerConnector = DummyMCPConnector

except Exception as e:
    warnings.warn(f"Failed to patch litserve.mcp (MCP will be disabled): {e}")

import litserve as ls
from litserve.connector import check_cuda_with_nvidia_smi
from loguru import logger

# Add parent dir to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Local imports
from task_db import TaskDB
from output_normalizer import normalize_output
from utils import parse_list_arg
import importlib.util

# ==============================================================================
# 2. Dependency Checks & Global Configurations
# ==============================================================================
def check_dependency(module_name: str, display_name: str) -> bool:
    """Helper to check if a module is installed and log the result."""
    available = importlib.util.find_spec(module_name) is not None
    icon = "✅" if available else "ℹ️ "
    msg = "available" if available else "not available (optional)"
    logger.info(f"{icon} {display_name} {msg}")
    return available

# Check optional dependencies
MARKITDOWN_AVAILABLE = False
try:
    from markitdown import MarkItDown
    MARKITDOWN_AVAILABLE = True
    logger.info("✅ MarkItDown available")
except ImportError:
    logger.info("ℹ️  MarkItDown not available (optional)")

PADDLEOCR_VL_AVAILABLE = check_dependency("paddleocr_vl", "PaddleOCR-VL")
PADDLEOCR_VL_VLLM_AVAILABLE = check_dependency("paddleocr_vl_vllm", "PaddleOCR-VL-VLLM")
MINERU_PIPELINE_AVAILABLE = check_dependency("mineru_pipeline", "MinerU Pipeline")
SENSEVOICE_AVAILABLE = check_dependency("audio_engines", "SenseVoice")
VIDEO_ENGINE_AVAILABLE = check_dependency("video_engines", "Video Engine")
WATERMARK_REMOVAL_AVAILABLE = check_dependency("remove_watermark", "Watermark Removal")

FORMAT_ENGINES_AVAILABLE = False
try:
    from format_engines import FormatEngineRegistry, FASTAEngine, GenBankEngine
    FormatEngineRegistry.register(FASTAEngine())
    FormatEngineRegistry.register(GenBankEngine())
    FORMAT_ENGINES_AVAILABLE = True
    logger.info(f"✅ Format Engines available: {', '.join(FormatEngineRegistry.get_supported_extensions())}")
except ImportError as e:
    logger.info(f"ℹ️  Format Engines not available: {e}")


# ==============================================================================
# 3. VLLM Container Controller
# ==============================================================================
class VLLMController:
    """管理 vLLM Docker 容器的互斥启动"""
    
    def __init__(self):
        pass

    def _get_client(self):
        """按需获取 Docker 客户端"""
        try:
            import docker
            return docker.from_env()
        except Exception as e:
            logger.warning(f"⚠️  Docker client init failed: {e}")
            return None

    def ensure_service(self, target_container: str, conflict_container: str):
        """
        确保目标容器运行，并关闭冲突容器 (严格互斥逻辑)
        """
        client = self._get_client()
        if not client:
            return
        
        try:
            # 1. 检查并关闭冲突容器
            try:
                conflict = client.containers.get(conflict_container)
                if conflict.status == 'running':
                    logger.info(f"🛑 Stopping conflicting service {conflict_container} to free VRAM...")
                    conflict.stop()
                    time.sleep(2) # 等待释放
                    logger.info(f"✅ Service {conflict_container} stopped.")
            except Exception:
                pass

            # 2. 检查并启动目标容器
            try:
                target = client.containers.get(target_container)
                if target.status == 'running':
                    return
                
                logger.info(f"🚀 Starting service {target_container} (Manual/Cold Start)...")
                target.start()
                
                # 等待服务健康 (简单轮询)
                for _ in range(30):
                    time.sleep(1)
                    target.reload()
                    if target.status == 'running':
                        break
                logger.info(f"✅ Service {target_container} started.")
                
            except Exception as e:
                logger.error(f"❌ Failed to start target container {target_container}: {e}")
                raise e
        finally:
            try:
                client.close()
            except:
                pass


# ==============================================================================
# 4. MinerU Worker API
# ==============================================================================
class MinerUWorkerAPI(ls.LitAPI):
    def __init__(
        self,
        paddleocr_vl_vllm_api_list=None,
        mineru_vllm_api_list=None,
        output_dir=None,
        poll_interval=0.5,
        enable_worker_loop=True,
        paddleocr_vl_vllm_engine_enabled=False,
    ):
        super().__init__()
        
        # 路径配置
        project_root = Path(__file__).parent.parent
        default_output = project_root / "data" / "output"
        self.output_dir = output_dir or os.getenv("OUTPUT_PATH", str(default_output))
        
        # 运行配置
        self.poll_interval = poll_interval
        self.enable_worker_loop = enable_worker_loop
        
        # API 配置
        self.paddleocr_vl_vllm_engine_enabled = paddleocr_vl_vllm_engine_enabled
        self.paddleocr_vl_vllm_api_list = paddleocr_vl_vllm_api_list or []
        self.mineru_vllm_api_list = mineru_vllm_api_list or []
        
        # 进程间共享计数器
        ctx = multiprocessing.get_context("spawn")
        self._global_worker_counter = ctx.Value("i", 0)

        # 初始化控制器
        self.vllm_controller = VLLMController()

    def setup(self, device):
        """初始化 Worker (每个 GPU 进程调用一次)"""
        with self._global_worker_counter.get_lock():
            my_global_index = self._global_worker_counter.value
            self._global_worker_counter.value += 1
        
        logger.info(f"🔢 [Init] I am Global Worker #{my_global_index} (on {device})")
        
        # API 分配
        self.paddleocr_vl_vllm_api = None
        if self.paddleocr_vl_vllm_engine_enabled and self.paddleocr_vl_vllm_api_list:
            assigned_api = self.paddleocr_vl_vllm_api_list[my_global_index % len(self.paddleocr_vl_vllm_api_list)]
            self.paddleocr_vl_vllm_api = assigned_api
            logger.info(f"🔧 Worker #{my_global_index} assigned Paddle OCR VL API: {assigned_api}")

        self.mineru_vllm_api = None
        if self.mineru_vllm_api_list:
            assigned_mineru_api = self.mineru_vllm_api_list[my_global_index % len(self.mineru_vllm_api_list)]
            self.mineru_vllm_api = assigned_mineru_api
            logger.info(f"🔧 Worker #{my_global_index} assigned MinerU VLLM API: {assigned_mineru_api}")

        # 设置 CUDA 隔离
        if "cuda:" in str(device):
            gpu_id = str(device).split(":")[-1]
            os.environ["CUDA_VISIBLE_DEVICES"] = gpu_id
            os.environ["MINERU_DEVICE_MODE"] = "cuda:0"
            logger.info(f"🎯 [GPU Isolation] Set CUDA_VISIBLE_DEVICES={gpu_id}")

        # 配置模型源
        model_source = os.getenv("MODEL_DOWNLOAD_SOURCE", "auto").lower()
        if model_source in ["modelscope", "auto"]:
            try:
                importlib.util.find_spec("modelscope")
                os.environ["MINERU_MODEL_SOURCE"] = "modelscope"
            except ImportError:
                if model_source == "modelscope":
                    logger.warning("⚠️  ModelScope not available, falling back to HuggingFace")

        if model_source == "huggingface":
            hf_endpoint = os.getenv("HF_ENDPOINT", "https://hf-mirror.com")
            os.environ.setdefault("HF_ENDPOINT", hf_endpoint)

        # 设备配置
        self.device = device
        if "cuda" in str(device):
            self.accelerator = "cuda"
            self.engine_device = "cuda:0"
        else:
            self.accelerator = "cpu"
            self.engine_device = "cpu"

        # MinerU VRAM 设置
        from mineru.utils.model_utils import get_vram
        if os.getenv("MINERU_VIRTUAL_VRAM_SIZE", None) is None:
            if self.accelerator == "cuda":
                try:
                    vram = round(get_vram("cuda:0"))
                    os.environ["MINERU_VIRTUAL_VRAM_SIZE"] = str(vram)
                except Exception:
                    os.environ["MINERU_VIRTUAL_VRAM_SIZE"] = "8"
            else:
                os.environ["MINERU_VIRTUAL_VRAM_SIZE"] = "1"

        # 初始化数据库
        db_path_env = os.getenv("DATABASE_PATH")
        if db_path_env:
            db_path = Path(db_path_env).resolve()
        else:
            project_root = Path(__file__).parent.parent
            db_path = (project_root / "data" / "db" / "mineru_tianshu.db").resolve()
        
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.task_db = TaskDB(str(db_path))

        # 初始化状态
        self.running = True
        self.current_task_id = None
        hostname = socket.gethostname()
        pid = os.getpid()
        self.worker_id = f"tianshu-{hostname}-{device}-{pid}"

        # 引擎占位符
        self.markitdown = MarkItDown() if MARKITDOWN_AVAILABLE else None
        self.mineru_pipeline_engine = None
        self.paddleocr_vl_engine = None
        self.paddleocr_vl_vllm_engine = None
        self.sensevoice_engine = None
        self.video_engine = None
        self.watermark_handler = None

        logger.info(f"🚀 Worker Setup Complete: {self.worker_id}")

        if WATERMARK_REMOVAL_AVAILABLE and self.accelerator == "cuda":
            try:
                from remove_watermark.pdf_watermark_handler import PDFWatermarkHandler
                self.watermark_handler = PDFWatermarkHandler(device="cuda:0", use_lama=True)
                logger.info(f"✅ Watermark engine initialized")
            except Exception as e:
                logger.error(f"❌ Failed to init watermark engine: {e}")

        if self.enable_worker_loop:
            self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self.worker_thread.start()

    def _worker_loop(self):
        logger.info(f"🔁 {self.worker_id} started task polling loop")
        loop_count = 0
        last_stats_log = 0

        while self.running:
            try:
                loop_count += 1
                task = self.task_db.get_next_task(worker_id=self.worker_id)

                if task:
                    task_id = task["task_id"]
                    self.current_task_id = task_id
                    logger.info(f"📥 {self.worker_id} pulled task: {task_id}")

                    try:
                        self._process_task(task)
                        logger.info(f"✅ {self.worker_id} completed task: {task_id}")
                    except Exception as e:
                        logger.error(f"❌ {self.worker_id} failed task {task_id}: {e}")
                        logger.exception(e)
                    finally:
                        self.current_task_id = None
                else:
                    if loop_count - last_stats_log >= 20:
                        try:
                            stats = self.task_db.get_queue_stats()
                            if loop_count % 100 == 0:
                                logger.info(f"💤 {self.worker_id} idle. Queue stats: {stats}")
                        except: pass
                        last_stats_log = loop_count
                    time.sleep(self.poll_interval)

            except Exception as e:
                logger.error(f"❌ Worker loop error: {e}")
                time.sleep(self.poll_interval)

    def _process_task(self, task: dict):
        """处理任务"""
        task_id = task["task_id"]
        file_path = task["file_path"]
        options = json.loads(task.get("options", "{}"))
        parent_task_id = task.get("parent_task_id")
        backend = task.get("backend", "auto")

        try:
            # 1. 智能服务切换
            paddle_container = "tianshu-vllm-paddleocr"
            mineru_container = "tianshu-vllm-mineru"

            if backend == "paddleocr-vl-vllm" and self.paddleocr_vl_vllm_api:
                self.vllm_controller.ensure_service(target_container=paddle_container, conflict_container=mineru_container)
            elif backend in ["vlm-auto-engine", "hybrid-auto-engine"] and self.mineru_vllm_api:
                self.vllm_controller.ensure_service(target_container=mineru_container, conflict_container=paddle_container)

            file_ext = Path(file_path).suffix.lower()

            # 2. 预处理
            if file_ext in [".docx", ".xlsx", ".pptx", ".doc", ".xls", ".ppt"] and options.get("convert_office_to_pdf", False):
                try:
                    pdf_path = self._convert_office_to_pdf(file_path)
                    file_path = pdf_path
                    file_ext = ".pdf"
                    logger.info(f"✅ Office converted to PDF: {pdf_path}")
                except Exception as e:
                    logger.warning(f"⚠️ Office conversion failed, falling back: {e}")

            # 3. PDF 拆分
            if file_ext == ".pdf" and not parent_task_id:
                if self._should_split_pdf(task_id, file_path, task, options):
                    return

            # 4. 去水印
            if file_ext == ".pdf" and options.get("remove_watermark", False) and self.watermark_handler:
                try:
                    cleaned_path = self._preprocess_remove_watermark(file_path, options)
                    file_path = str(cleaned_path)
                except Exception as e:
                    logger.warning(f"⚠️ Watermark removal failed: {e}")

            # 5. 引擎路由
            result = None

            if backend == "sensevoice":
                if not SENSEVOICE_AVAILABLE: raise ValueError("SenseVoice not available")
                result = self._process_audio(file_path, options)

            elif backend == "video":
                if not VIDEO_ENGINE_AVAILABLE: raise ValueError("Video engine not available")
                result = self._process_video(file_path, options)

            elif backend == "paddleocr-vl":
                if not PADDLEOCR_VL_AVAILABLE: raise ValueError("PaddleOCR-VL not available")
                result = self._process_with_paddleocr_vl(file_path, options)

            elif backend == "paddleocr-vl-vllm":
                if not PADDLEOCR_VL_VLLM_AVAILABLE: raise ValueError("PaddleOCR-VL-VLLM not available")
                result = self._process_with_paddleocr_vl_vllm(file_path, options)

            elif "pipeline" in backend or "vlm-" in backend or "hybrid-" in backend:
                if not MINERU_PIPELINE_AVAILABLE: raise ValueError("MinerU Pipeline not available")
                options["parse_mode"] = backend
                result = self._process_with_mineru(file_path, options)

            elif backend == "auto":
                if FORMAT_ENGINES_AVAILABLE and FormatEngineRegistry.is_supported(file_path):
                    result = self._process_with_format_engine(file_path, options)
                elif file_ext in [".wav", ".mp3", ".flac", ".m4a", ".ogg"] and SENSEVOICE_AVAILABLE:
                    result = self._process_audio(file_path, options)
                elif file_ext in [".mp4", ".avi", ".mkv", ".mov"] and VIDEO_ENGINE_AVAILABLE:
                    result = self._process_video(file_path, options)
                elif file_ext in [".pdf", ".png", ".jpg", ".jpeg"] and MINERU_PIPELINE_AVAILABLE:
                    options["parse_mode"] = "pipeline"
                    result = self._process_with_mineru(file_path, options)
                elif self.markitdown:
                    result = self._process_with_markitdown(file_path)
                else:
                    raise ValueError(f"Unsupported file type for Auto mode: {file_ext}")

            else:
                if FORMAT_ENGINES_AVAILABLE:
                    engine = FormatEngineRegistry.get_engine(backend)
                    if engine:
                        result = self._process_with_format_engine(file_path, options, engine_name=backend)
                    else:
                        raise ValueError(f"Unknown backend: {backend}")
                else:
                    raise ValueError(f"Unknown backend: {backend}")

            if not result:
                raise ValueError("No result generated by engine")

            # 6. 保存完整结果到数据库 (包含 json_content 和 pdf_path)
            self.task_db.update_task_status(
                task_id=task_id,
                status="completed",
                result_path=result["result_path"],
                error_message=None,
                data=json.dumps({
                    "pdf_path": result.get("pdf_path"),      # 关键：供前端左侧预览使用
                    "json_content": result.get("json_content"), # 关键：供前端右侧布局渲染使用
                    "markdown": result.get("content"),
                    "markdown_file": result.get("markdown_file") 
                })
            )

            # 7. 合并子任务
            if parent_task_id:
                parent_id_to_merge = self.task_db.on_child_task_completed(task_id)
                if parent_id_to_merge:
                    try:
                        self._merge_parent_task_results(parent_id_to_merge)
                    except Exception as e:
                        self.task_db.update_task_status(parent_id_to_merge, "failed", error_message=str(e))

        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            self.task_db.update_task_status(task_id, "failed", error_message=error_msg)
            if parent_task_id:
                self.task_db.on_child_task_failed(task_id, error_msg)
            raise

    # -------------------------------------------------------------------------
    # Helper: 确保 PDF 存在于 Output 目录
    # -------------------------------------------------------------------------
    def _ensure_pdf_in_output(self, file_path: str, output_dir: Path, preferred_name: str = None) -> str:
        """
        确保输出目录中有 PDF 文件，供前端预览使用。
        返回相对于 output_dir 的文件名。
        """
        output_dir = Path(output_dir)
        source_file = Path(file_path)
        
        # 1. 如果源文件不是 PDF (可能是图片)，尝试找转换后的 PDF
        if source_file.suffix.lower() != ".pdf":
             # 检查是否有 layout.pdf
            layout_pdfs = list(output_dir.glob("*_layout.pdf"))
            if layout_pdfs:
                return layout_pdfs[0].name
            return None

        # 2. 如果源文件是 PDF
        # 优先查找 MinerU 生成的带布局信息的 PDF
        layout_pdfs = list(output_dir.glob("*_layout.pdf"))
        if layout_pdfs:
            return layout_pdfs[0].name
        
        # 3. 如果没有布局 PDF，则复制源 PDF 到输出目录
        target_name = preferred_name or source_file.name
        target_path = output_dir / target_name
        
        if not target_path.exists():
            try:
                shutil.copy2(source_file, target_path)
                logger.info(f"📄 Copied source PDF to output: {target_name}")
            except Exception as e:
                logger.warning(f"Failed to copy source PDF: {e}")
                return None
        
        return target_name

    # -------------------------------------------------------------------------
    # Engine Processor Implementations
    # -------------------------------------------------------------------------
    def _process_with_mineru(self, file_path: str, options: dict) -> dict:
        if self.mineru_pipeline_engine is None:
            from mineru_pipeline import MinerUPipelineEngine
            self.mineru_pipeline_engine = MinerUPipelineEngine(
                device=self.engine_device,
                vlm_api_base=self.mineru_vllm_api
            )

        output_dir = Path(self.output_dir) / Path(file_path).stem
        output_dir.mkdir(parents=True, exist_ok=True)

        if "http-client" in options.get("parse_mode", "") and self.mineru_vllm_api:
            options.setdefault("server_url", self.mineru_vllm_api.replace("/v1", ""))

        result = self.mineru_pipeline_engine.parse(file_path, output_path=str(output_dir), options=options)
        
        actual_output = Path(result["result_path"])
        normalize_output(actual_output)

        # 扁平化目录结构
        if actual_output.resolve() != output_dir.resolve():
            try:
                for item in actual_output.iterdir():
                    dest = output_dir / item.name
                    if dest.exists():
                        if dest.is_dir(): shutil.rmtree(dest)
                        else: dest.unlink()
                    shutil.move(str(item), str(dest))
                shutil.rmtree(actual_output)
            except Exception as e:
                logger.warning(f"Flattening warning: {e}")
        
        # [修复] 确保 PDF 存在并返回路径
        pdf_path = self._ensure_pdf_in_output(file_path, output_dir)

        return {
            "result_path": str(output_dir),
            "content": result.get("markdown", ""),
            "json_content": result.get("json_content"),
            "pdf_path": pdf_path, # 返回给前端
            "markdown_file": result.get("markdown_file")
        }

    def _process_with_paddleocr_vl(self, file_path: str, options: dict) -> dict:
        if self.accelerator == "cpu":
            raise RuntimeError("PaddleOCR-VL requires GPU")
            
        if self.paddleocr_vl_engine is None:
            from paddleocr_vl import PaddleOCRVLEngine
            self.paddleocr_vl_engine = PaddleOCRVLEngine(device="cuda:0", model_name="PaddleOCR-VL-1.5")

        output_dir = Path(self.output_dir) / Path(file_path).stem
        output_dir.mkdir(parents=True, exist_ok=True)

        result = self.paddleocr_vl_engine.parse(file_path, output_path=str(output_dir), **options)
        
        pdf_path = self._ensure_pdf_in_output(file_path, output_dir)
        normalize_output(output_dir)
        
        return {
            "result_path": str(output_dir), 
            "content": result.get("markdown", ""),
            "json_content": result.get("json_content"), # 必须传递
            "pdf_path": pdf_path
        }

    def _process_with_paddleocr_vl_vllm(self, file_path: str, options: dict) -> dict:
        if self.accelerator == "cpu":
            raise RuntimeError("PaddleOCR-VL-VLLM requires GPU")

        if self.paddleocr_vl_vllm_engine is None:
            from paddleocr_vl_vllm import PaddleOCRVLVLLMEngine
            self.paddleocr_vl_vllm_engine = PaddleOCRVLVLLMEngine(
                device="cuda:0",
                vllm_api_base=self.paddleocr_vl_vllm_api,
                model_name="PaddleOCR-VL-1.5-0.9B"
            )

        output_dir = Path(self.output_dir) / Path(file_path).stem
        output_dir.mkdir(parents=True, exist_ok=True)

        result = self.paddleocr_vl_vllm_engine.parse(file_path, output_path=str(output_dir), **options)
        
        # [修复] 复制源文件以便预览 (关键修复)
        pdf_path = self._ensure_pdf_in_output(file_path, output_dir)
        
        normalize_output(output_dir, handle_method="paddleocr-vl")
        
        return {
            "result_path": str(output_dir), 
            "content": result.get("markdown", ""),
            "json_content": result.get("json_content"), # 关键：支持右侧高亮
            "pdf_path": pdf_path # 关键：支持左侧预览
        }

    def _process_audio(self, file_path: str, options: dict) -> dict:
        if self.sensevoice_engine is None:
            from audio_engines import SenseVoiceEngine
            self.sensevoice_engine = SenseVoiceEngine(device=self.engine_device)

        output_dir = Path(self.output_dir) / Path(file_path).stem
        output_dir.mkdir(parents=True, exist_ok=True)

        result = self.sensevoice_engine.parse(
            audio_path=file_path,
            output_path=str(output_dir),
            language=options.get("lang", "auto"),
            use_itn=options.get("use_itn", True),
            enable_speaker_diarization=options.get("enable_speaker_diarization", False)
        )
        normalize_output(output_dir)
        return {"result_path": str(output_dir), "content": result.get("markdown", "")}

    def _process_video(self, file_path: str, options: dict) -> dict:
        if self.video_engine is None:
            from video_engines import VideoProcessingEngine
            self.video_engine = VideoProcessingEngine(device=self.engine_device)

        output_dir = Path(self.output_dir) / Path(file_path).stem
        output_dir.mkdir(parents=True, exist_ok=True)

        result = self.video_engine.parse(
            video_path=file_path,
            output_path=str(output_dir),
            language=options.get("lang", "auto"),
            use_itn=options.get("use_itn", True),
            keep_audio=options.get("keep_audio", False),
            enable_keyframe_ocr=options.get("enable_keyframe_ocr", False),
            ocr_backend=options.get("ocr_backend", "paddleocr-vl"),
            keep_keyframes=options.get("keep_keyframes", False)
        )
        
        (output_dir / f"{Path(file_path).stem}_video_analysis.md").write_text(result["markdown"], encoding="utf-8")
        normalize_output(output_dir)
        return {"result_path": str(output_dir), "content": result["markdown"]}

    def _process_with_markitdown(self, file_path: str) -> dict:
        if not self.markitdown:
            raise RuntimeError("MarkItDown not available")

        output_dir = Path(self.output_dir) / Path(file_path).stem
        output_dir.mkdir(parents=True, exist_ok=True)

        result = self.markitdown.convert(file_path)
        markdown_content = result.text_content

        if Path(file_path).suffix.lower() == ".docx":
            try:
                from utils.docx_image_extractor import extract_images_from_docx, append_images_to_markdown
                images_dir = output_dir / "images"
                images = extract_images_from_docx(file_path, str(images_dir))
                if images:
                    markdown_content = append_images_to_markdown(markdown_content, images)
            except Exception as e:
                logger.warning(f"DOCX image extraction failed: {e}")

        (output_dir / f"{Path(file_path).stem}_markitdown.md").write_text(markdown_content, encoding="utf-8")
        normalize_output(output_dir)
        
        # MarkItDown 也可以尝试生成 PDF 预览 (如果源文件是 PDF)
        pdf_path = self._ensure_pdf_in_output(file_path, output_dir)
        
        return {"result_path": str(output_dir), "content": markdown_content, "pdf_path": pdf_path}

    def _process_with_format_engine(self, file_path: str, options: dict, engine_name: Optional[str] = None) -> dict:
        lang = options.get("language", "en")
        
        if engine_name:
            engine = FormatEngineRegistry.get_engine(engine_name)
        else:
            engine = FormatEngineRegistry.get_engine_by_extension(file_path)
            
        if not engine:
            raise ValueError("No format engine available")

        result = engine.parse(file_path, options={"language": lang})
        
        output_dir = Path(self.output_dir) / Path(file_path).stem
        output_dir.mkdir(parents=True, exist_ok=True)
        
        (output_dir / "result.md").write_text(result["markdown"], encoding="utf-8")
        (output_dir / "result.json").write_text(json.dumps(result["json_content"], indent=2, ensure_ascii=False), encoding="utf-8")
        
        normalize_output(output_dir)
        return {
            "result_path": str(output_dir),
            "content": result["content"],
            "json_content": result["json_content"]
        }

    # -------------------------------------------------------------------------
    # Utilities
    # -------------------------------------------------------------------------
    def _convert_office_to_pdf(self, file_path: str) -> str:
        input_file = Path(file_path)
        final_pdf = input_file.parent / f"{input_file.stem}.pdf"
        if final_pdf.exists(): final_pdf.unlink()

        try:
            with tempfile.TemporaryDirectory(prefix="libreoffice_") as temp_dir:
                temp_path = Path(temp_dir)
                temp_input = temp_path / input_file.name
                shutil.copy2(input_file, temp_input)

                cmd = [
                    "libreoffice", "--headless", "--convert-to", "pdf",
                    "--outdir", str(temp_path), str(temp_input)
                ]
                subprocess.run(cmd, check=True, timeout=120, capture_output=True)
                
                temp_pdf = temp_path / f"{input_file.stem}.pdf"
                if not temp_pdf.exists(): raise RuntimeError("PDF output missing")
                shutil.move(str(temp_pdf), str(final_pdf))
                return str(final_pdf)
        except Exception as e:
            raise RuntimeError(f"Office conversion failed: {e}")

    def _preprocess_remove_watermark(self, file_path: str, options: dict) -> Path:
        if not self.watermark_handler: raise RuntimeError("Watermark handler missing")
        output_file = Path(self.output_dir) / f"{Path(file_path).stem}_no_watermark.pdf"
        
        kwargs = {}
        for k in ["auto_detect", "force_scanned", "remove_text", "remove_images", 
                  "remove_annotations", "watermark_keywords", "watermark_dpi", 
                  "watermark_conf_threshold", "watermark_dilation"]:
            if k in options: kwargs[k.replace("watermark_", "")] = options[k]

        return self.watermark_handler.remove_watermark(input_path=file_path, output_path=str(output_file), **kwargs)

    def _should_split_pdf(self, task_id, file_path, task, options):
        from utils.pdf_utils import get_pdf_page_count, split_pdf_file
        if os.getenv("PDF_SPLIT_ENABLED", "true").lower() != "true": return False
        
        threshold = int(os.getenv("PDF_SPLIT_THRESHOLD_PAGES", "500"))
        chunk_size = int(os.getenv("PDF_SPLIT_CHUNK_SIZE", "500"))
        
        try:
            pages = get_pdf_page_count(Path(file_path))
            if pages <= threshold: return False
            
            logger.info(f"🔀 Splitting PDF ({pages} pages)...")
            self.task_db.convert_to_parent_task(task_id, child_count=0)
            split_dir = Path(self.output_dir) / "splits" / task_id
            split_dir.mkdir(parents=True, exist_ok=True)
            
            chunks = split_pdf_file(Path(file_path), split_dir, chunk_size, task_id)
            
            for chunk in chunks:
                c_ops = options.copy()
                c_ops["chunk_info"] = {k: chunk[k] for k in ["start_page", "end_page", "page_count"]}
                self.task_db.create_child_task(
                    parent_task_id=task_id,
                    file_name=f"{Path(file_path).stem}_p{chunk['start_page']}-{chunk['end_page']}.pdf",
                    file_path=chunk["path"],
                    backend=task.get("backend", "auto"),
                    options=c_ops,
                    priority=task.get("priority", 0),
                    user_id=task.get("user_id")
                )
            
            self.task_db.convert_to_parent_task(task_id, child_count=len(chunks))
            logger.info(f"✂️  Split into {len(chunks)} subtasks")
            return True
        except Exception as e:
            logger.error(f"❌ PDF split failed: {e}")
            return False

    def _merge_parent_task_results(self, parent_task_id):
        parent_task = self.task_db.get_task_with_children(parent_task_id)
        children = parent_task.get("children", [])
        if not children: return

        children.sort(key=lambda x: json.loads(x.get("options", "{}")).get("chunk_info", {}).get("start_page", 0))
        
        parent_out = Path(self.output_dir) / Path(parent_task["file_path"]).stem
        parent_out.mkdir(parents=True, exist_ok=True)
        
        md_parts, json_pages = [], []
        
        for child in children:
            if child["status"] != "completed": continue
            res_dir = Path(child["result_path"])
            
            md_file = next((f for f in res_dir.rglob("*.md") if f.name == "result.md"), None) or list(res_dir.rglob("*.md"))[0]
            md_parts.append(md_file.read_text(encoding="utf-8"))
            
            json_file = next((f for f in res_dir.rglob("*.json") if "result" in f.name or "content" in f.name), None)
            if json_file:
                try:
                    data = json.loads(json_file.read_text(encoding="utf-8"))
                    offset = json.loads(child.get("options", "{}")).get("chunk_info", {}).get("start_page", 1) - 1
                    
                    # 兼容不同的 JSON 格式
                    pages = []
                    if isinstance(data, list): pages = data
                    elif "pages" in data: pages = data["pages"]
                    
                    for p in pages:
                        # 修正页码偏移
                        if "page_idx" in p: p["page_idx"] += offset
                        json_pages.append(p)
                except: pass

        (parent_out / "result.md").write_text("\n\n\n\n".join(md_parts), encoding="utf-8")
        if json_pages:
            (parent_out / "result.json").write_text(json.dumps(json_pages, indent=2, ensure_ascii=False), encoding="utf-8")
        
        # [修复] 复制父任务的源文件到输出
        self._ensure_pdf_in_output(parent_task["file_path"], parent_out)

        normalize_output(parent_out)
        self.task_db.update_task_status(parent_task_id, "completed", result_path=str(parent_out))
        self._cleanup_child_task_files(children)

    def _cleanup_child_task_files(self, children):
        for child in children:
            try:
                if child.get("file_path"): Path(child["file_path"]).unlink(missing_ok=True)
            except: pass

    # LitServe Interfaces
    def decode_request(self, request): return request.get("action", "health")
    def predict(self, action):
        if action == "health":
            return {"status": "healthy", "worker_id": self.worker_id}
        elif action == "poll":
            if self.enable_worker_loop:
                return {"status": "skipped", "message": "Auto-loop active"}
            task = self.task_db.pull_task()
            if task:
                try:
                    self._process_task(task)
                    return {"status": "completed", "task_id": task["task_id"]}
                except Exception as e:
                    return {"status": "failed", "error": str(e)}
            return {"status": "empty"}
        return {"status": "error", "message": "Invalid action"}
    def encode_response(self, response): return response
    def teardown(self):
        self.running = False
        if hasattr(self, "worker_thread"): self.worker_thread.join(timeout=2)


def start_litserve_workers(
    output_dir=None, accelerator="auto", devices="auto", workers_per_device=1,
    port=8001, poll_interval=0.5, enable_worker_loop=True,
    paddleocr_vl_vllm_engine_enabled=False, paddleocr_vl_vllm_api_list=[],
    mineru_vllm_api_list=[]
):
    def resolve_auto_accelerator():
        try:
            from importlib.metadata import distribution
            distribution("torch")
            if check_cuda_with_nvidia_smi() > 0: return "cuda"
        except: pass
        return "cpu"

    if output_dir is None:
        output_dir = os.getenv("OUTPUT_PATH", str(Path(__file__).parent.parent / "data" / "output"))

    if accelerator == "auto":
        accelerator = resolve_auto_accelerator()

    logger.info(f"🚀 Starting Worker | Acc: {accelerator} | Devices: {devices} | Out: {output_dir}")

    api = MinerUWorkerAPI(
        output_dir=output_dir,
        poll_interval=poll_interval,
        enable_worker_loop=enable_worker_loop,
        paddleocr_vl_vllm_engine_enabled=paddleocr_vl_vllm_engine_enabled,
        paddleocr_vl_vllm_api_list=paddleocr_vl_vllm_api_list,
        mineru_vllm_api_list=mineru_vllm_api_list,
    )

    server = ls.LitServer(
        api,
        accelerator=accelerator,
        devices=devices,
        workers_per_device=workers_per_device,
        timeout=False,
    )

    def graceful_shutdown(signum=None, frame=None):
        if hasattr(api, "teardown"): api.teardown()
        sys.exit(0)

    signal.signal(signal.SIGINT, graceful_shutdown)
    signal.signal(signal.SIGTERM, graceful_shutdown)
    atexit.register(lambda: api.teardown() if hasattr(api, "teardown") else None)

    server.run(port=port, generate_client_file=False)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=str, default=None)
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--accelerator", type=str, default="auto")
    parser.add_argument("--workers-per-device", type=int, default=1)
    parser.add_argument("--devices", type=str, default="auto")
    parser.add_argument("--poll-interval", type=float, default=0.5)
    parser.add_argument("--disable-worker-loop", action="store_true")
    parser.add_argument("--paddleocr-vl-vllm-engine-enabled", action="store_true")
    parser.add_argument("--paddleocr-vl-vllm-api-list", type=parse_list_arg, default=[])
    parser.add_argument("--mineru-vllm-api-list", type=parse_list_arg, default=[])
    args = parser.parse_args()

    # Env Var Fallbacks
    devices = args.devices
    if devices == "auto":
        env_dev = os.getenv("CUDA_VISIBLE_DEVICES")
        if env_dev: devices = env_dev

    port = args.port
    if port == 8001:
        port = int(os.getenv("WORKER_PORT", "8001"))

    # [核心修复] 强制并发控制：优先使用环境变量，默认为 1
    # 用户可以在 .env 中设置 MAX_CONCURRENT_TASKS=1 来限制
    env_workers = os.getenv("MAX_CONCURRENT_TASKS", "1")
    workers_per_device = int(env_workers)
    
    logger.info(f"⚙️  Concurrency Config: workers_per_device={workers_per_device} (env: {env_workers})")

    start_litserve_workers(
        output_dir=args.output_dir,
        accelerator=args.accelerator,
        devices=devices,
        workers_per_device=workers_per_device, # 使用处理后的变量
        port=port,
        poll_interval=args.poll_interval,
        enable_worker_loop=not args.disable_worker_loop,
        paddleocr_vl_vllm_engine_enabled=args.paddleocr_vl_vllm_engine_enabled,
        paddleocr_vl_vllm_api_list=args.paddleocr_vl_vllm_api_list,
        mineru_vllm_api_list=args.mineru_vllm_api_list,
    )
