"""
MinerU Tianshu - LitServe Worker
天枢 LitServe Worker

企业级 AI 数据预处理平台 - GPU Worker
支持文档、图片、音频、视频等多模态数据处理
使用 LitServe 实现 GPU 资源的自动负载均衡
Worker 主动循环拉取任务并处理
"""

import os
import json
import sys
import time
import threading
import signal
import atexit
from pathlib import Path
from typing import Optional

# Fix litserve MCP compatibility with mcp>=1.1.0
# Completely disable LitServe's internal MCP to avoid conflicts with our standalone MCP Server
import litserve as ls

try:
    # Patch LitServe's MCP module to disable it completely
    import litserve.mcp as ls_mcp
    import sys
    from contextlib import asynccontextmanager

    # Inject MCPServer (mcp.server.lowlevel.Server) as dummy
    if not hasattr(ls_mcp, "MCPServer"):

        class DummyMCPServer:
            def __init__(self, *args, **kwargs):
                pass

        ls_mcp.MCPServer = DummyMCPServer
        if "litserve.mcp" in sys.modules:
            sys.modules["litserve.mcp"].MCPServer = DummyMCPServer

    # Inject StreamableHTTPSessionManager as dummy
    if not hasattr(ls_mcp, "StreamableHTTPSessionManager"):

        class DummyStreamableHTTPSessionManager:
            def __init__(self, *args, **kwargs):
                pass

        ls_mcp.StreamableHTTPSessionManager = DummyStreamableHTTPSessionManager
        if "litserve.mcp" in sys.modules:
            sys.modules["litserve.mcp"].StreamableHTTPSessionManager = DummyStreamableHTTPSessionManager

    # Replace _LitMCPServerConnector with a complete dummy implementation
    class DummyMCPConnector:
        """完全禁用 LitServe 内置 MCP 的 Dummy 实现"""

        def __init__(self, *args, **kwargs):
            self.mcp_server = None
            self.session_manager = None
            self.request_handler = None

        @asynccontextmanager
        async def lifespan(self, app):
            """空的 lifespan context manager，不做任何事情"""
            yield  # 什么都不做，直接让服务器启动

        def connect_mcp_server(self, *args, **kwargs):
            """空的 connect_mcp_server 方法，不做任何事情"""
            pass  # 什么都不做，跳过 MCP 初始化

    # 替换 _LitMCPServerConnector 类
    ls_mcp._LitMCPServerConnector = DummyMCPConnector

    # 同时更新 sys.modules 中的引用
    if "litserve.mcp" in sys.modules:
        sys.modules["litserve.mcp"]._LitMCPServerConnector = DummyMCPConnector

except Exception as e:
    # If patching fails, log warning and continue
    # The server might still work or fail with a clearer error message
    import warnings

    warnings.warn(f"Failed to patch litserve.mcp (MCP will be disabled): {e}")

from loguru import logger

# 添加父目录到路径以导入 MinerU
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from task_db import TaskDB
from mineru.cli.common import do_parse
from mineru.utils.model_utils import get_vram, clean_memory

# 尝试导入 markitdown
try:
    from markitdown import MarkItDown

    MARKITDOWN_AVAILABLE = True
except ImportError:
    MARKITDOWN_AVAILABLE = False
    logger.warning("⚠️  markitdown not available, Office format parsing will be disabled")

# 尝试导入 DeepSeek OCR
try:
    from deepseek_ocr import DeepSeekOCREngine  # noqa: F401

    DEEPSEEK_OCR_AVAILABLE = True
    logger.info("✅ DeepSeek OCR engine available")
except ImportError:
    DEEPSEEK_OCR_AVAILABLE = False
    logger.info("ℹ️  DeepSeek OCR not available (optional)")

# 尝试导入 PaddleOCR-VL
try:
    from paddleocr_vl import PaddleOCRVLEngine  # noqa: F401

    PADDLEOCR_VL_AVAILABLE = True
    logger.info("✅ PaddleOCR-VL engine available")
except ImportError:
    PADDLEOCR_VL_AVAILABLE = False
    logger.info("ℹ️  PaddleOCR-VL not available (optional)")

# 尝试导入 SenseVoice 音频处理
import importlib.util

SENSEVOICE_AVAILABLE = importlib.util.find_spec("audio_engines") is not None
if SENSEVOICE_AVAILABLE:
    logger.info("✅ SenseVoice audio engine available")
else:
    logger.info("ℹ️  SenseVoice not available (optional)")

# 尝试导入视频处理引擎
VIDEO_ENGINE_AVAILABLE = importlib.util.find_spec("video_engines") is not None
if VIDEO_ENGINE_AVAILABLE:
    logger.info("✅ Video processing engine available")
else:
    logger.info("ℹ️  Video processing engine not available (optional)")

# 尝试导入水印去除引擎
try:
    from remove_watermark.watermark_remover import WatermarkRemover  # noqa: F401
    from remove_watermark.pdf_watermark_handler import PDFWatermarkHandler

    WATERMARK_REMOVAL_AVAILABLE = True
    logger.info("✅ Watermark removal engine available")
except ImportError as e:
    WATERMARK_REMOVAL_AVAILABLE = False
    logger.info(f"ℹ️  Watermark removal engine not available (optional): {e}")

# 尝试导入格式引擎（专业领域格式支持）
try:
    from format_engines import FormatEngineRegistry, FASTAEngine, GenBankEngine

    # 注册所有引擎
    FormatEngineRegistry.register(FASTAEngine())
    FormatEngineRegistry.register(GenBankEngine())

    FORMAT_ENGINES_AVAILABLE = True
    logger.info("✅ Format engines available")
    logger.info(f"   Supported extensions: {', '.join(FormatEngineRegistry.get_supported_extensions())}")
except ImportError as e:
    FORMAT_ENGINES_AVAILABLE = False
    logger.info(f"ℹ️  Format engines not available (optional): {e}")


class MinerUWorkerAPI(ls.LitAPI):
    """
    MinerU Tianshu Worker API

    继承自 LitServe 的 LitAPI，实现自动负载均衡
    Worker 主动循环拉取任务并处理，无需外部调度
    """

    def __init__(self):
        """初始化 API (不接受参数，参数通过类属性传递)"""
        super().__init__()
        # 这些属性会在创建实例前设置（通过类属性）
        # 在 setup() 中会用到

    def setup(self, device):
        """
        初始化 Worker (每个 GPU 上调用一次)

        Args:
            device: 设备 ID (cuda:0, cuda:1, cpu 等)
        """
        import socket

        self.device = device
        # 从类属性获取配置（由 start_litserve_workers 设置）
        # 默认使用共享输出目录（Docker 环境）
        default_output = os.getenv("OUTPUT_PATH", "/app/output")
        self.output_dir = getattr(self.__class__, "_output_dir", default_output)
        self.poll_interval = getattr(self.__class__, "_poll_interval", 0.5)
        self.enable_worker_loop = getattr(self.__class__, "_enable_worker_loop", True)

        # 创建输出目录
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

        # 初始化任务数据库（从环境变量读取，兼容 Docker 和本地）
        db_path_env = os.getenv("DATABASE_PATH")
        if db_path_env:
            db_path = Path(db_path_env)
        else:
            # 默认路径（本地开发）
            db_path = Path(__file__).parent / "mineru_tianshu.db"
        self.task_db = TaskDB(str(db_path))

        # Worker 状态
        self.running = True
        self.current_task_id = None

        # 生成唯一的 worker_id: tianshu-{hostname}-{device}-{pid}
        hostname = socket.gethostname()
        pid = os.getpid()
        self.worker_id = f"tianshu-{hostname}-{device}-{pid}"

        # 初始化可选的处理引擎
        self.markitdown = MarkItDown() if MARKITDOWN_AVAILABLE else None
        self.deepseek_ocr_engine = None  # 延迟加载
        self.paddleocr_vl_engine = None  # 延迟加载
        self.sensevoice_engine = None  # 延迟加载
        self.video_engine = None  # 延迟加载
        self.watermark_handler = None  # 延迟加载

        logger.info("=" * 60)
        logger.info(f"🚀 Worker Setup: {self.worker_id}")
        logger.info("=" * 60)
        logger.info(f"📍 Device: {device}")
        logger.info(f"📂 Output Dir: {self.output_dir}")
        logger.info(f"🗃️  Database: {db_path}")
        logger.info(f"🔄 Worker Loop: {'Enabled' if self.enable_worker_loop else 'Disabled'}")
        if self.enable_worker_loop:
            logger.info(f"⏱️  Poll Interval: {self.poll_interval}s")
        logger.info("")

        # 打印可用的引擎
        logger.info("📦 Available Engines:")
        logger.info(f"   • MarkItDown: {'✅' if MARKITDOWN_AVAILABLE else '❌'}")
        logger.info(f"   • DeepSeek OCR: {'✅' if DEEPSEEK_OCR_AVAILABLE else '❌'}")
        logger.info(f"   • PaddleOCR-VL: {'✅' if PADDLEOCR_VL_AVAILABLE else '❌'}")
        logger.info(f"   • SenseVoice: {'✅' if SENSEVOICE_AVAILABLE else '❌'}")
        logger.info(f"   • Video Engine: {'✅' if VIDEO_ENGINE_AVAILABLE else '❌'}")
        logger.info(f"   • Watermark Removal: {'✅' if WATERMARK_REMOVAL_AVAILABLE else '❌'}")
        logger.info(f"   • Format Engines: {'✅' if FORMAT_ENGINES_AVAILABLE else '❌'}")
        logger.info("")

        # 检测和初始化水印去除引擎（仅 CUDA）
        if WATERMARK_REMOVAL_AVAILABLE and "cuda" in str(device).lower():
            try:
                logger.info("🎨 Initializing watermark removal engine...")
                # PDFWatermarkHandler 只接受 device 和 use_lama 参数
                self.watermark_handler = PDFWatermarkHandler(device=device, use_lama=True)
                logger.info("✅ Watermark removal engine initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize watermark removal engine: {e}")
                self.watermark_handler = None

        logger.info("✅ Worker ready")
        logger.info(f"   Device: {device}")
        if "cuda" in str(device).lower():
            try:
                vram_gb = get_vram(device.split(":")[-1])
                if vram_gb is not None:
                    logger.info(f"   VRAM: {vram_gb:.0f}GB")
                else:
                    logger.info("   VRAM: Unknown")
            except Exception as e:
                logger.warning(f"   VRAM: Unable to detect ({e})")

        # 如果启用了 worker 循环，启动后台线程拉取任务
        if self.enable_worker_loop:
            self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self.worker_thread.start()
            logger.info(f"🔄 Worker loop started (poll_interval={self.poll_interval}s)")
        else:
            logger.info("⏸️  Worker loop disabled, waiting for manual triggers")

    def _worker_loop(self):
        """
        Worker 后台循环：持续拉取任务并处理

        这个循环在后台线程中运行，不断检查是否有新任务
        一旦有任务，立即处理，处理完成后继续循环
        """
        logger.info(f"🔁 {self.worker_id} started task polling loop")

        while self.running:
            try:
                # 拉取任务（原子操作，防止重复处理）
                task = self.task_db.get_next_task(worker_id=self.worker_id)

                if task:
                    task_id = task["task_id"]
                    self.current_task_id = task_id
                    logger.info(f"📥 {self.worker_id} pulled task: {task_id}")

                    try:
                        # 处理任务
                        self._process_task(task)
                        logger.info(f"✅ {self.worker_id} completed task: {task_id}")
                    except Exception as e:
                        logger.error(f"❌ {self.worker_id} failed task {task_id}: {e}")
                        logger.exception(e)
                    finally:
                        self.current_task_id = None
                else:
                    # 没有任务，空闲等待（降低日志噪音，不输出 debug 日志）
                    time.sleep(self.poll_interval)

            except Exception as e:
                logger.error(f"❌ Worker loop error: {e}")
                logger.exception(e)
                time.sleep(self.poll_interval)

    def _process_task(self, task: dict):
        """
        处理单个任务

        Args:
            task: 任务字典（从数据库拉取）
        """
        task_id = task["task_id"]
        file_path = task["file_path"]
        options = json.loads(task.get("options", "{}"))

        try:
            # 根据 backend 选择处理方式（从 task 字段读取，不是从 options 读取）
            backend = task.get("backend", "auto")

            # 检查文件扩展名
            file_ext = Path(file_path).suffix.lower()

            # 0. 可选：预处理 - 去除水印（仅 PDF，作为预处理步骤）
            if file_ext == ".pdf" and options.get("remove_watermark", False) and self.watermark_handler:
                logger.info(f"🎨 [Preprocessing] Removing watermark from PDF: {file_path}")
                try:
                    cleaned_pdf_path = self._preprocess_remove_watermark(file_path, options)
                    file_path = str(cleaned_pdf_path)  # 使用去水印后的文件继续处理
                    logger.info(f"✅ [Preprocessing] Watermark removed, continuing with: {file_path}")
                except Exception as e:
                    logger.warning(f"⚠️ [Preprocessing] Watermark removal failed: {e}, continuing with original file")
                    # 继续使用原文件处理

            # 统一的引擎路由逻辑：优先使用用户指定的 backend，否则自动选择
            result = None  # 初始化 result

            # 1. 用户指定了音频引擎
            if backend == "sensevoice":
                if not SENSEVOICE_AVAILABLE:
                    raise ValueError("SenseVoice engine is not available")
                logger.info(f"🎤 Processing with SenseVoice: {file_path}")
                result = self._process_audio(file_path, options)

            # 3. 用户指定了视频引擎
            elif backend == "video":
                if not VIDEO_ENGINE_AVAILABLE:
                    raise ValueError("Video processing engine is not available")
                logger.info(f"🎬 Processing with video engine: {file_path}")
                result = self._process_video(file_path, options)

            # 4. 用户指定了 DeepSeek OCR
            elif backend == "deepseek-ocr":
                if not DEEPSEEK_OCR_AVAILABLE:
                    raise ValueError("DeepSeek OCR engine is not available")
                logger.info(f"🔍 Processing with DeepSeek OCR: {file_path}")
                result = self._process_with_deepseek_ocr(file_path, options)

            # 5. 用户指定了 PaddleOCR-VL
            elif backend == "paddleocr-vl":
                if not PADDLEOCR_VL_AVAILABLE:
                    raise ValueError("PaddleOCR-VL engine is not available")
                logger.info(f"🔍 Processing with PaddleOCR-VL: {file_path}")
                result = self._process_with_paddleocr_vl(file_path, options)

            # 6. 用户指定了 MinerU Pipeline
            elif backend == "pipeline":
                logger.info(f"🔧 Processing with MinerU Pipeline: {file_path}")
                result = self._process_with_mineru(file_path, options)

            # 7. auto 模式：根据文件类型自动选择引擎
            elif backend == "auto":
                # 7.1 检查是否是专业格式（FASTA, GenBank 等）
                if FORMAT_ENGINES_AVAILABLE and FormatEngineRegistry.is_supported(file_path):
                    logger.info(f"🧬 [Auto] Processing with format engine: {file_path}")
                    result = self._process_with_format_engine(file_path, options)

                # 7.2 检查是否是音频文件
                elif file_ext in [".wav", ".mp3", ".flac", ".m4a", ".ogg"] and SENSEVOICE_AVAILABLE:
                    logger.info(f"🎤 [Auto] Processing audio file: {file_path}")
                    result = self._process_audio(file_path, options)

                # 7.3 检查是否是视频文件
                elif file_ext in [".mp4", ".avi", ".mkv", ".mov", ".flv", ".wmv"] and VIDEO_ENGINE_AVAILABLE:
                    logger.info(f"🎬 [Auto] Processing video file: {file_path}")
                    result = self._process_video(file_path, options)

                # 7.4 默认使用 MinerU Pipeline 处理 PDF/图片
                elif file_ext in [".pdf", ".png", ".jpg", ".jpeg"]:
                    logger.info(f"🔧 [Auto] Processing with MinerU Pipeline: {file_path}")
                    result = self._process_with_mineru(file_path, options)

                # 7.5 兜底：Office 文档/文本/HTML 使用 MarkItDown（如果可用）
                elif (
                    file_ext in [".docx", ".xlsx", ".pptx", ".doc", ".xls", ".ppt", ".html", ".txt", ".csv"]
                    and self.markitdown
                ):
                    logger.info(f"📄 [Auto] Processing Office/Text file with MarkItDown: {file_path}")
                    result = self._process_with_markitdown(file_path)

                else:
                    # 没有合适的处理器
                    supported_formats = (
                        "PDF, PNG, JPG (MinerU/DeepSeek/PaddleOCR), Audio (SenseVoice), Video, FASTA, GenBank"
                    )
                    if self.markitdown:
                        supported_formats += ", Office/Text (MarkItDown)"
                    raise ValueError(
                        f"Unsupported file type: file={file_path}, ext={file_ext}. "
                        f"Supported formats: {supported_formats}"
                    )

            else:
                # 8. 尝试使用格式引擎（用户明确指定了 fasta, genbank 等）
                if FORMAT_ENGINES_AVAILABLE:
                    engine = FormatEngineRegistry.get_engine(backend)
                    if engine is not None:
                        logger.info(f"🧬 Processing with format engine: {backend}")
                        result = self._process_with_format_engine(file_path, options, engine_name=backend)
                    else:
                        # 未知的 backend
                        raise ValueError(
                            f"Unknown backend: {backend}. "
                            f"Supported backends: auto, pipeline, deepseek-ocr, paddleocr-vl, sensevoice, video, fasta, genbank"
                        )
                else:
                    # 格式引擎不可用
                    raise ValueError(
                        f"Unknown backend: {backend}. "
                        f"Supported backends: auto, pipeline, deepseek-ocr, paddleocr-vl, sensevoice, video"
                    )

            # 检查 result 是否被正确赋值
            if result is None:
                raise ValueError(f"No result generated for backend: {backend}, file: {file_path}")

            # 更新任务状态为完成
            self.task_db.update_task_status(
                task_id=task_id,
                status="completed",
                result_path=result["result_path"],
                error_message=None,
            )

            # 清理显存（如果是 GPU）
            if "cuda" in str(self.device).lower():
                clean_memory()

        except Exception as e:
            # 更新任务状态为失败
            error_msg = f"{type(e).__name__}: {str(e)}"
            self.task_db.update_task_status(task_id=task_id, status="failed", result_path=None, error_message=error_msg)
            raise

    def _process_with_mineru(self, file_path: str, options: dict) -> dict:
        """使用 MinerU 处理文档"""
        file_stem = Path(file_path).stem
        output_dir = Path(self.output_dir) / file_stem
        output_dir.mkdir(parents=True, exist_ok=True)

        # 读取 PDF 文件为字节
        with open(file_path, "rb") as f:
            pdf_bytes = f.read()

        # 获取文件名
        file_name = Path(file_path).name

        # 获取语言设置
        lang = options.get("lang", "auto")

        # 调用 MinerU 新版 API（批量处理接口）
        # 新版 API 接受列表参数，即使只有一个文件也要用列表
        # output_format 支持: "md", "md_json" (同时输出 markdown 和 JSON)
        do_parse(
            pdf_file_names=[file_name],  # 文件名列表
            pdf_bytes_list=[pdf_bytes],  # 文件字节列表
            p_lang_list=[lang],  # 语言列表
            output_dir=str(output_dir),  # 输出目录
            output_format="md_json",  # 同时输出 Markdown 和 JSON
            end_page_id=options.get("end_page_id"),
            layout_mode=options.get("layout_mode", True),
            formula_enable=options.get("formula_enable", True),
            table_enable=options.get("table_enable", True),
        )

        # MinerU 新版输出结构: {output_dir}/{file_name}/auto/{file_stem}.md
        # 递归查找 markdown 文件和 JSON 文件
        md_files = list(output_dir.rglob("*.md"))

        if md_files:
            # 使用第一个找到的 md 文件
            md_file = md_files[0]
            logger.info(f"✅ Found MinerU output: {md_file}")
            content = md_file.read_text(encoding="utf-8")

            # 返回实际的输出目录（包含 auto/ 子目录）
            actual_output_dir = md_file.parent

            # 查找 JSON 文件
            # MinerU 输出的 JSON 文件格式: {filename}_content_list.json, {filename}_middle.json, {filename}_model.json
            # 我们主要关注 content_list.json（包含结构化内容）
            json_files = [
                f
                for f in actual_output_dir.rglob("*.json")
                if "_content_list.json" in f.name and not f.parent.name.startswith("page_")
            ]

            result = {
                "result_path": str(actual_output_dir),  # 返回包含所有输出的目录
                "content": content,
            }

            # 如果找到 JSON 文件，也读取它
            if json_files:
                json_file = json_files[0]
                logger.info(f"✅ Found MinerU JSON output: {json_file}")
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        json_content = json.load(f)
                    result["json_path"] = str(json_file)
                    result["json_content"] = json_content
                except Exception as e:
                    logger.warning(f"⚠️  Failed to load JSON: {e}")
            else:
                logger.info("ℹ️  No JSON output found (MinerU may not generate it by default)")

            return result
        else:
            # 如果找不到 md 文件，列出输出目录内容以便调试
            logger.error("❌ MinerU output directory structure:")
            for item in output_dir.rglob("*"):
                logger.error(f"   {item}")
            raise FileNotFoundError(f"MinerU output not found in: {output_dir}")

    def _process_with_markitdown(self, file_path: str) -> dict:
        """使用 MarkItDown 处理文档"""
        result = self.markitdown.convert(file_path)
        content = result.text_content

        # 保存结果
        output_file = Path(self.output_dir) / f"{Path(file_path).stem}_markitdown.md"
        output_file.write_text(content, encoding="utf-8")

        return {"result_path": str(output_file), "content": content}

    def _process_with_deepseek_ocr(self, file_path: str, options: dict) -> dict:
        """使用 DeepSeek OCR 处理图片"""
        # 延迟加载 DeepSeek OCR（单例模式）
        if self.deepseek_ocr_engine is None:
            from deepseek_ocr import DeepSeekOCREngine

            self.deepseek_ocr_engine = DeepSeekOCREngine(device=self.device)
            logger.info("✅ DeepSeek OCR engine loaded (singleton)")

        # 处理图片
        result = self.deepseek_ocr_engine.process_image(file_path, output_format="markdown")

        # 保存结果
        output_file = Path(self.output_dir) / f"{Path(file_path).stem}_deepseek_ocr.md"
        output_file.write_text(result["markdown"], encoding="utf-8")

        return {"result_path": str(output_file), "content": result["markdown"]}

    def _process_with_paddleocr_vl(self, file_path: str, options: dict) -> dict:
        """使用 PaddleOCR-VL 处理图片或 PDF"""
        # 延迟加载 PaddleOCR-VL（单例模式）
        if self.paddleocr_vl_engine is None:
            from paddleocr_vl import PaddleOCRVLEngine

            # PaddleOCRVLEngine 不接受参数，内部自动管理设备
            self.paddleocr_vl_engine = PaddleOCRVLEngine()
            logger.info("✅ PaddleOCR-VL engine loaded (singleton)")

        # 设置输出目录
        output_dir = Path(self.output_dir) / Path(file_path).stem
        output_dir.mkdir(parents=True, exist_ok=True)

        # 处理文件（parse 方法需要 output_path）
        result = self.paddleocr_vl_engine.parse(file_path, output_path=str(output_dir))

        # 返回结果
        return {"result_path": str(output_dir), "content": result.get("markdown", "")}

    def _process_audio(self, file_path: str, options: dict) -> dict:
        """使用 SenseVoice 处理音频文件"""
        # 延迟加载 SenseVoice（单例模式）
        if self.sensevoice_engine is None:
            from audio_engines import SenseVoiceEngine

            self.sensevoice_engine = SenseVoiceEngine(device=self.device)
            logger.info("✅ SenseVoice engine loaded (singleton)")

        # 处理音频
        result = self.sensevoice_engine.transcribe(file_path, language=options.get("lang", "auto"))

        # 保存结果
        output_file = Path(self.output_dir) / f"{Path(file_path).stem}_transcription.txt"
        output_file.write_text(result["text"], encoding="utf-8")

        return {"result_path": str(output_file), "content": result["text"]}

    def _process_video(self, file_path: str, options: dict) -> dict:
        """使用视频处理引擎处理视频文件"""
        # 延迟加载视频引擎（单例模式）
        if self.video_engine is None:
            from video_engines import VideoProcessingEngine

            self.video_engine = VideoProcessingEngine(device=self.device, output_dir=self.output_dir)
            logger.info("✅ Video processing engine loaded (singleton)")

        # 处理视频
        result = self.video_engine.process_video(
            video_path=file_path,
            extract_keyframes=options.get("extract_keyframes", True),
            transcribe_audio=options.get("transcribe_audio", True),
            keyframe_interval=options.get("keyframe_interval", 30),
            language=options.get("lang", "auto"),
        )

        # 保存结果（Markdown 格式）
        output_file = Path(self.output_dir) / f"{Path(file_path).stem}_video_analysis.md"
        output_file.write_text(result["markdown"], encoding="utf-8")

        return {"result_path": str(output_file), "content": result["markdown"]}

    def _preprocess_remove_watermark(self, file_path: str, options: dict) -> Path:
        """
        预处理：去除 PDF 水印

        这是一个可选的预处理步骤，去除水印后的文件会被后续的解析引擎处理

        返回：
            去除水印后的 PDF 路径

        支持的 options 参数：
            - auto_detect: 是否自动检测 PDF 类型（默认 True）
            - force_scanned: 强制使用扫描件模式（默认 False）
            - remove_text: 是否删除文本对象（可编辑 PDF，默认 True）
            - remove_images: 是否删除图片对象（可编辑 PDF，默认 True）
            - remove_annotations: 是否删除注释（可编辑 PDF，默认 True）
            - keywords: 文本关键词列表（可编辑 PDF，只删除包含这些关键词的文本）
            - dpi: 转换分辨率（扫描件 PDF，默认 200）
            - conf_threshold: YOLO 置信度阈值（扫描件 PDF，默认 0.35）
            - dilation: 掩码膨胀（扫描件 PDF，默认 10）
        """
        if not self.watermark_handler:
            raise RuntimeError("Watermark removal is not available (CUDA required)")

        # 设置输出路径
        output_file = Path(self.output_dir) / f"{Path(file_path).stem}_no_watermark.pdf"

        # 构建参数字典（只传递实际提供的参数）
        kwargs = {}

        # 通用参数
        if "auto_detect" in options:
            kwargs["auto_detect"] = options["auto_detect"]
        if "force_scanned" in options:
            kwargs["force_scanned"] = options["force_scanned"]

        # 可编辑 PDF 参数
        if "remove_text" in options:
            kwargs["remove_text"] = options["remove_text"]
        if "remove_images" in options:
            kwargs["remove_images"] = options["remove_images"]
        if "remove_annotations" in options:
            kwargs["remove_annotations"] = options["remove_annotations"]
        if "watermark_keywords" in options:
            kwargs["keywords"] = options["watermark_keywords"]

        # 扫描件 PDF 参数
        if "watermark_dpi" in options:
            kwargs["dpi"] = options["watermark_dpi"]
        if "watermark_conf_threshold" in options:
            kwargs["conf_threshold"] = options["watermark_conf_threshold"]
        if "watermark_dilation" in options:
            kwargs["dilation"] = options["watermark_dilation"]

        # 去除水印（返回输出路径）
        cleaned_pdf_path = self.watermark_handler.remove_watermark(
            input_path=file_path, output_path=str(output_file), **kwargs
        )

        return cleaned_pdf_path

    def _process_with_format_engine(self, file_path: str, options: dict, engine_name: Optional[str] = None) -> dict:
        """
        使用格式引擎处理专业领域格式文件

        Args:
            file_path: 文件路径
            options: 处理选项
            engine_name: 指定的引擎名称（如 fasta, genbank），为 None 时自动选择
        """
        # 获取语言设置
        lang = options.get("language", "en")

        # 根据指定的引擎名称或文件扩展名选择引擎
        if engine_name:
            # 用户明确指定了引擎
            engine = FormatEngineRegistry.get_engine(engine_name)
            if engine is None:
                raise ValueError(f"Format engine '{engine_name}' not found or not registered")

            # 验证文件是否适合该引擎
            if not engine.validate_file(file_path):
                raise ValueError(
                    f"File '{file_path}' is not supported by '{engine_name}' engine. "
                    f"Supported extensions: {', '.join(engine.SUPPORTED_EXTENSIONS)}"
                )

            # 使用指定引擎处理
            result = engine.parse(file_path, options={"language": lang})
        else:
            # 自动选择引擎（根据文件扩展名）
            engine = FormatEngineRegistry.get_engine_by_extension(file_path)
            if engine is None:
                raise ValueError(f"No format engine available for file: {file_path}")

            result = engine.parse(file_path, options={"language": lang})

        # 为每个任务创建专属输出目录（与其他引擎保持一致）
        output_dir = Path(self.output_dir) / Path(file_path).stem
        output_dir.mkdir(parents=True, exist_ok=True)

        # 保存结果（与其他引擎保持一致的命名规范）
        # 主结果文件：result.md 和 result.json
        output_file = output_dir / "result.md"
        output_file.write_text(result["markdown"], encoding="utf-8")
        logger.info("📄 Main result saved: result.md")

        # 备份文件：使用原始文件名（便于调试）
        backup_md_file = output_dir / f"{Path(file_path).stem}_{result['format']}.md"
        backup_md_file.write_text(result["markdown"], encoding="utf-8")
        logger.info(f"📄 Backup saved: {backup_md_file.name}")

        # 也保存 JSON 结构化数据
        json_file = output_dir / "result.json"
        json_file.write_text(json.dumps(result["json_content"], indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("📄 Main JSON saved: result.json")

        # 备份 JSON 文件
        backup_json_file = output_dir / f"{Path(file_path).stem}_{result['format']}.json"
        backup_json_file.write_text(json.dumps(result["json_content"], indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info(f"📄 Backup JSON saved: {backup_json_file.name}")

        return {
            "result_path": str(output_dir),  # 返回任务专属目录
            "content": result["markdown"],
            "json_path": str(json_file),
            "json_content": result["json_content"],
        }

    def decode_request(self, request):
        """
        解码请求

        LitServe 会调用这个方法来解析请求
        我们的请求格式: {"action": "health" | "poll"}
        """
        return request.get("action", "health")

    def predict(self, action):
        """
        处理请求

        Args:
            action: 请求动作
                - "health": 健康检查
                - "poll": 手动拉取任务（当 worker loop 禁用时）

        Returns:
            响应字典
        """
        if action == "health":
            # 健康检查
            vram_gb = None
            if "cuda" in str(self.device).lower():
                try:
                    vram_gb = get_vram(self.device.split(":")[-1])
                except Exception:
                    pass

            return {
                "status": "healthy",
                "worker_id": self.worker_id,
                "device": str(self.device),
                "vram_gb": vram_gb,
                "running": self.running,
                "current_task": self.current_task_id,
                "worker_loop_enabled": self.enable_worker_loop,
            }

        elif action == "poll":
            # 手动拉取任务（用于测试或禁用 worker loop 时）
            if self.enable_worker_loop:
                return {
                    "status": "skipped",
                    "message": "Worker is in auto-loop mode, manual polling is disabled",
                    "worker_id": self.worker_id,
                }

            task = self.task_db.pull_task()
            if task:
                task_id = task["task_id"]
                logger.info(f"📥 {self.worker_id} manually pulled task: {task_id}")

                try:
                    self._process_task(task)
                    logger.info(f"✅ {self.worker_id} completed task: {task_id}")

                    return {"status": "completed", "task_id": task["task_id"], "worker_id": self.worker_id}
                except Exception as e:
                    return {
                        "status": "failed",
                        "task_id": task["task_id"],
                        "error": str(e),
                        "worker_id": self.worker_id,
                    }
            else:
                # Worker 循环模式：返回状态信息
                return {
                    "status": "auto_mode",
                    "message": "Worker is running in auto-loop mode, tasks are processed automatically",
                    "worker_id": self.worker_id,
                    "worker_running": self.running,
                }

        else:
            return {
                "status": "error",
                "message": f'Invalid action: {action}. Use "health" or "poll".',
                "worker_id": self.worker_id,
            }

    def encode_response(self, response):
        """编码响应"""
        return response

    def teardown(self):
        """清理资源（Worker 关闭时调用）"""
        # 获取 worker_id（可能在 setup 失败时未初始化）
        worker_id = getattr(self, "worker_id", "unknown")

        logger.info(f"🛑 Worker {worker_id} shutting down...")

        # 设置 running 标志（如果已初始化）
        if hasattr(self, "running"):
            self.running = False

        # 等待 worker 线程结束
        if hasattr(self, "worker_thread") and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=5)

        logger.info(f"✅ Worker {worker_id} stopped")


def start_litserve_workers(
    output_dir=None,  # 默认从环境变量读取
    accelerator="auto",
    devices="auto",
    workers_per_device=1,
    port=9000,
    poll_interval=0.5,
    enable_worker_loop=True,
):
    """
    启动 LitServe Worker Pool

    Args:
        output_dir: 输出目录
        accelerator: 加速器类型 (auto/cuda/cpu/mps)
        devices: 使用的设备 (auto/[0,1,2])
        workers_per_device: 每个 GPU 的 worker 数量
        port: 服务端口
        poll_interval: Worker 拉取任务的间隔（秒）
        enable_worker_loop: 是否启用 worker 自动循环拉取任务
    """
    # 如果没有指定输出目录，从环境变量读取
    if output_dir is None:
        output_dir = os.getenv("OUTPUT_PATH", "/app/output")

    logger.info("=" * 60)
    logger.info("🚀 Starting MinerU Tianshu LitServe Worker Pool")
    logger.info("=" * 60)
    logger.info(f"📂 Output Directory: {output_dir}")
    logger.info(f"🎮 Accelerator: {accelerator}")
    logger.info(f"💾 Devices: {devices}")
    logger.info(f"👷 Workers per Device: {workers_per_device}")
    logger.info(f"🔌 Port: {port}")
    logger.info(f"🔄 Worker Loop: {'Enabled' if enable_worker_loop else 'Disabled'}")
    if enable_worker_loop:
        logger.info(f"⏱️  Poll Interval: {poll_interval}s")
    logger.info("=" * 60)

    # 创建 LitServe 服务器
    # 注意：LitAPI 不支持 __init__ 参数，需要通过类属性传递配置
    MinerUWorkerAPI._output_dir = output_dir
    MinerUWorkerAPI._poll_interval = poll_interval
    MinerUWorkerAPI._enable_worker_loop = enable_worker_loop

    api = MinerUWorkerAPI()
    server = ls.LitServer(
        api,
        accelerator=accelerator,
        devices=devices,
        workers_per_device=workers_per_device,
        timeout=False,  # 不设置超时
    )

    # 注册优雅关闭处理器
    def graceful_shutdown(signum=None, frame=None):
        """处理关闭信号，优雅地停止 worker"""
        logger.info("🛑 Received shutdown signal, gracefully stopping workers...")
        # 注意：LitServe 会为每个设备创建多个 worker 实例
        # 这里的 api 只是模板，实际的 worker 实例由 LitServe 管理
        # teardown 会在每个 worker 进程中被调用
        if hasattr(api, "teardown"):
            api.teardown()
        sys.exit(0)

    # 注册信号处理器（Ctrl+C 等）
    signal.signal(signal.SIGINT, graceful_shutdown)
    signal.signal(signal.SIGTERM, graceful_shutdown)

    # 注册 atexit 处理器（正常退出时调用）
    atexit.register(lambda: api.teardown() if hasattr(api, "teardown") else None)

    logger.info("✅ LitServe worker pool initialized")
    logger.info(f"📡 Listening on: http://0.0.0.0:{port}/predict")
    if enable_worker_loop:
        logger.info("🔁 Workers will continuously poll and process tasks")
    else:
        logger.info("🔄 Workers will wait for scheduler triggers")
    logger.info("=" * 60)

    # 启动服务器
    # 注意：LitServe 内置 MCP 已通过 monkeypatch 完全禁用（我们有独立的 MCP Server）
    server.run(port=port, generate_client_file=False)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="MinerU Tianshu LitServe Worker Pool")
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory for processed files (default: from OUTPUT_PATH env or /app/output)",
    )
    parser.add_argument("--port", type=int, default=9000, help="Server port (default: 9000)")
    parser.add_argument(
        "--accelerator",
        type=str,
        default="auto",
        choices=["auto", "cuda", "cpu", "mps"],
        help="Accelerator type (default: auto)",
    )
    parser.add_argument("--workers-per-device", type=int, default=1, help="Number of workers per device (default: 1)")
    parser.add_argument("--devices", type=str, default="auto", help="Devices to use, comma-separated (default: auto)")
    parser.add_argument(
        "--poll-interval", type=float, default=0.5, help="Worker poll interval in seconds (default: 0.5)"
    )
    parser.add_argument(
        "--disable-worker-loop",
        action="store_true",
        help="Disable automatic worker loop (workers will wait for manual triggers)",
    )

    args = parser.parse_args()

    # 处理 devices 参数
    devices = args.devices
    if devices != "auto":
        try:
            devices = [int(d.strip()) for d in devices.split(",")]
        except ValueError:
            logger.error(f"❌ Invalid devices format: {devices}. Use comma-separated integers (e.g., '0,1,2')")
            sys.exit(1)

    start_litserve_workers(
        output_dir=args.output_dir,
        accelerator=args.accelerator,
        devices=devices,
        workers_per_device=args.workers_per_device,
        port=args.port,
        poll_interval=args.poll_interval,
        enable_worker_loop=not args.disable_worker_loop,
    )
