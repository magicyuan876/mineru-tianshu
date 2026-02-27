"""
MinerU Pipeline Engine
单例模式，每个进程只加载一次模型
使用 MinerU 处理 PDF 和图片

更新日志 (2026-02-15):
- [新增] 智能显存休眠机制 (Auto-Sleep): 空闲 5 分钟自动释放显存
- [新增] 自动唤醒机制 (Auto-Wakeup): 新任务自动重新加载模型
- [优化] 移除每次任务后的强制显存清理，提升连续处理性能
- [核心修复] 深度文本清洗 (双重反转义、去重、清洗 LaTeX 符号)
- [核心修复] 使用临时纯英文目录处理，规避中文路径问题
"""

import json
import os
import shutil
import tempfile
import time
import urllib.request
import urllib.error
import re
import html
import gc
import threading
from pathlib import Path
from typing import Optional, Dict, Any
from threading import Lock
from loguru import logger
import img2pdf

# 尝试导入 torch 用于显存管理
try:
    import torch
except ImportError:
    torch = None

class MinerUPipelineEngine:
    """
    MinerU Pipeline 引擎
    集成自动显存管理与深度清洗功能
    """

    _instance: Optional["MinerUPipelineEngine"] = None
    _lock = Lock()
    _pipeline = None  # 这里的 pipeline 实际上是 do_parse 函数
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, device: str = "cuda:0", vlm_api_base: str = None):
        if self._initialized:
            return

        with self._lock:
            if self._initialized:
                return

            self.device = device
            self.vlm_api_base = vlm_api_base

            if "cuda:" in device:
                self.gpu_id = device.split(":")[-1]
            else:
                self.gpu_id = "0"

            # =========================================================
            # [新增] 智能显存管理状态变量
            # =========================================================
            self.last_active_time = time.time()  # 最后活动时间
            self.is_processing = False           # 是否正在处理任务
            self.is_offloaded = True             # 是否已卸载显存
            self.idle_timeout = 300              # 空闲超时时间 (秒) - 5分钟

            # 启动显存监控后台线程
            self._monitor_thread = threading.Thread(target=self._auto_sleep_monitor, daemon=True)
            self._monitor_thread.start()
            
            self._initialized = True
            logger.info(f"🔧 MinerU Pipeline Engine initialized on {device}")
            logger.info(f"⏳ Auto-sleep monitor enabled (Timeout: {self.idle_timeout}s)")
            if self.vlm_api_base:
                logger.info(f"   VLLM API Base: {self.vlm_api_base}")

    def _auto_sleep_monitor(self):
        """
        [后台线程] 监控系统空闲状态，超时自动释放显存
        """
        while True:
            time.sleep(10)  # 每10秒检查一次
            try:
                # 如果 1. 正在处理任务 或 2. 已经卸载，则跳过
                if self.is_processing or self.is_offloaded:
                    continue
                
                idle_duration = time.time() - self.last_active_time
                if idle_duration > self.idle_timeout:
                    logger.info(f"💤 System idle for {idle_duration:.0f}s. Unloading models to save VRAM...")
                    self.cleanup() # 执行清理
                    self.is_offloaded = True # 标记为已卸载
            except Exception as e:
                logger.error(f"Error in auto-sleep monitor: {e}")

    def _load_pipeline(self):
        """延迟加载 MinerU 管道 (do_parse)"""
        if self._pipeline is not None:
            return self._pipeline

        with self._lock:
            if self._pipeline is not None:
                return self._pipeline

            logger.info("=" * 60)
            logger.info("📥 Loading MinerU Pipeline (do_parse)...")
            logger.info("=" * 60)

            try:
                from mineru.cli.common import do_parse
                self._pipeline = do_parse
                logger.info("✅ MinerU Pipeline loaded successfully!")
                return self._pipeline
            except Exception as e:
                logger.error(f"❌ Error loading MinerU pipeline: {e}")
                raise

    def _wait_for_server(self, server_url: str, timeout: int = 60) -> bool:
        """等待 VLLM 服务就绪"""
        base_url = server_url.rstrip("/")
        if base_url.endswith("/v1"):
            base_url = base_url[:-3]
            
        health_url = f"{base_url}/v1/models"
        
        logger.info(f"⏳ Waiting for VLLM server at {base_url} (Timeout: {timeout}s)...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                with urllib.request.urlopen(health_url, timeout=2) as response:
                    if response.status == 200:
                        logger.info(f"✅ VLLM server is ready: {base_url}")
                        return True
            except (urllib.error.URLError, ConnectionRefusedError):
                pass
            except Exception as e:
                logger.debug(f"Health check warning: {e}")
            
            time.sleep(1)
            
        logger.warning(f"⚠️  VLLM server wait timed out after {timeout}s. Process may fail.")
        return False

    def _clean_markdown(self, text: str) -> str:
        """
        [关键功能] 深度清洗 Markdown 文本
        解决 HTML 转义、LaTeX 过度包装、非换行空格和重复内容问题
        """
        if not text:
            return ""

        if "117" in text or "LVEDd" in text:
            logger.debug(f"🧹 Executing _clean_markdown... (Length: {len(text)})")

        # 1. HTML 反转义 (执行两次以解决 &amp;gt; 这种双重转义问题)
        text = html.unescape(text)
        text = html.unescape(text)

        # 2. 暴力替换常见的未转义字符
        text = text.replace('&gt;', '>').replace('&lt;', '<').replace('&amp;', '&')

        # 3. 去除 LaTeX 的 \mathrm{} 包装
        text = re.sub(r'\\mathrm\{(.*?)\}', r'\1', text, flags=re.DOTALL)

        # 4. 清洗 LaTeX 特殊字符
        text = text.replace('~', ' ')
        
        # 5. 去除模型幻觉产生的 <del> 标签
        text = text.replace('<del>', '').replace('</del>', '')
        
        # 6. [加强版] 暴力去重逻辑 
        text = re.sub(r'(\S+)([\s\r\n]+)\1', r'\1', text)

        # 7. 去除连续的多余空行
        text = re.sub(r'\n{3,}', '\n\n', text)

        return text

    def cleanup(self):
        """
        [增强版] 清理显存与模型
        用于 Auto-Sleep 或程序退出时
        """
        with self._lock:
            logger.info("🧹 Starting memory cleanup...")
            try:
                from mineru.utils.model_utils import clean_memory
                clean_memory()
            except Exception:
                pass
            
            # 强制 GC 与 CUDA 缓存清理
            try:
                self._pipeline = None # 释放函数引用，促使下次重新加载
                gc.collect()
                if torch and torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    torch.cuda.ipc_collect()
                logger.info("✅ GPU Memory released completely.")
            except Exception as e:
                logger.warning(f"Hard cleanup warning: {e}")

    def parse(self, file_path: str, output_path: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        处理文件 (增强版：自动唤醒 + 临时目录 + 深度清洗)
        """
        # =========================================================
        # 1. 状态更新与自动唤醒 (Auto-Wakeup)
        # =========================================================
        self.is_processing = True
        self.last_active_time = time.time()
        
        if self.is_offloaded:
            logger.info("🚀 New task received. Waking up models (Auto-Wakeup)...")
            self.is_offloaded = False
            # 注意：下方的 _load_pipeline() 会自动处理重新加载逻辑
        
        try:
            options = options or {}
            
            final_output_dir = Path(output_path)
            final_output_dir.mkdir(parents=True, exist_ok=True)

            file_path_obj = Path(file_path)
            file_ext = file_path_obj.suffix.lower()

            # 1. 确定 Backend
            user_backend = options.get("parse_mode", "pipeline")
            if user_backend == "auto":
                user_backend = "pipeline"

            backend = user_backend
            server_url = options.get("server_url")

            # 智能切换 VLLM
            if not server_url and self.vlm_api_base:
                if user_backend == "vlm-auto-engine":
                    backend = "vlm-http-client"
                    server_url = self.vlm_api_base.replace("/v1", "")
                    logger.info(f"🔄 [Accelerate] Switching to {backend} using local vLLM")
                elif user_backend == "hybrid-auto-engine":
                    backend = "hybrid-http-client"
                    server_url = self.vlm_api_base.replace("/v1", "")
                    logger.info(f"🔄 [Accelerate] Switching to {backend} using local vLLM")

            # 服务健康检查
            if "http-client" in backend and server_url:
                self._wait_for_server(server_url)

            # 2. 准备参数
            parse_method = options.get("method", "auto")
            if options.get("force_ocr"):
                parse_method = "ocr"

            formula_enable = options.get("formula_enable", True)
            table_enable = options.get("table_enable", True)
            
            f_draw_layout_bbox = options.get("draw_layout_bbox", True)      
            f_draw_span_bbox = options.get("draw_span_bbox", True)          
            f_dump_md = options.get("dump_markdown", True)                  
            f_dump_middle_json = options.get("dump_middle_json", True)      
            f_dump_model_output = options.get("dump_model_output", True)    
            f_dump_content_list = options.get("dump_content_list", True)    
            f_dump_orig_pdf = options.get("dump_orig_pdf", True)            

            start_page_id = options.get("start_page_id", 0)
            end_page_id = options.get("end_page_id", None)
            
            try: start_page_id = int(start_page_id)
            except: start_page_id = 0
            
            try: 
                if end_page_id is not None and str(end_page_id).strip() != "": 
                    end_page_id = int(end_page_id)
                    if end_page_id == -1: end_page_id = None
                else: end_page_id = None
            except: end_page_id = None

            do_parse_func = self._load_pipeline()

            with open(file_path, "rb") as f:
                file_bytes = f.read()

            if file_ext in [".png", ".jpg", ".jpeg"]:
                logger.info("🖼️  Converting image to PDF...")
                try:
                    pdf_bytes = img2pdf.convert(file_bytes)
                except Exception as e:
                    raise ValueError(f"Image conversion failed: {e}")
            else:
                pdf_bytes = file_bytes

            lang = options.get("lang", "auto")
            if lang == "auto": lang = "ch"

            # 使用临时纯英文目录处理
            with tempfile.TemporaryDirectory(prefix="mineru_proc_") as temp_dir:
                temp_work_dir = Path(temp_dir)
                logger.info(f"🛠️  Working in temp directory: {temp_work_dir}")
                
                safe_file_name = "result.pdf"
                
                do_parse_func(
                    output_dir=str(temp_work_dir),
                    pdf_file_names=[safe_file_name],
                    pdf_bytes_list=[pdf_bytes],
                    p_lang_list=[lang],
                    
                    backend=backend,
                    parse_method=parse_method,
                    server_url=server_url,
                    
                    start_page_id=start_page_id,
                    end_page_id=end_page_id,
                    formula_enable=formula_enable,
                    table_enable=table_enable,
                    
                    f_draw_layout_bbox=f_draw_layout_bbox,
                    f_draw_span_bbox=f_draw_span_bbox,
                    f_dump_md=f_dump_md,
                    f_dump_middle_json=f_dump_middle_json,
                    f_dump_model_output=f_dump_model_output,
                    f_dump_orig_pdf=f_dump_orig_pdf,
                    f_dump_content_list=f_dump_content_list
                )

                # 结果提取与搬运
                generated_result_dir = temp_work_dir / "result"
                
                if not generated_result_dir.exists():
                    temp_md_files = list(temp_work_dir.rglob("*.md"))
                    if temp_md_files:
                        generated_result_dir = temp_md_files[0].parent.parent
                    else:
                        temp_json_files = list(temp_work_dir.rglob("*_content_list.json"))
                        if temp_json_files:
                             generated_result_dir = temp_json_files[0].parent.parent
                        else:
                             raise FileNotFoundError("Processing failed internally - No output generated")

                # 1. 读取内容并进行深度清洗
                content = ""
                json_content = None
                
                temp_md_files = list(generated_result_dir.rglob("*.md"))
                if temp_md_files:
                    md_file = temp_md_files[0]
                    raw_content = md_file.read_text(encoding="utf-8")
                    
                    # 深度清洗
                    content = self._clean_markdown(raw_content)
                    
                    # 覆盖写入清洗后的内容
                    md_file.write_text(content, encoding="utf-8")
                    
                    logger.info(f"✅ Read and cleaned MD content: {len(content)} chars")
                
                temp_json_files = list(generated_result_dir.rglob("*_content_list.json"))
                if temp_json_files:
                    try:
                        with open(temp_json_files[0], "r", encoding="utf-8") as f:
                            json_content = json.load(f)
                    except: pass

                # 2. 如果 MD 为空，尝试从 JSON 恢复
                if not content.strip() and json_content:
                    logger.warning("⚠️  Markdown file is empty, attempting to recover text from JSON...")
                    recovered_text = []
                    if isinstance(json_content, list):
                        for block in json_content:
                            text = block.get("text", "")
                            text = self._clean_markdown(text)
                            recovered_text.append(text)
                    content = "\n\n".join(recovered_text)
                    
                    if temp_md_files:
                        temp_md_files[0].write_text(content, encoding="utf-8")
                        
                    logger.info(f"ℹ️  Recovered {len(content)} chars from JSON")

                # 3. 搬运文件
                logger.info(f"📦 Moving results from {generated_result_dir} to {final_output_dir}")
                if generated_result_dir.exists():
                    for src_path in generated_result_dir.rglob("*"):
                        if src_path.is_file():
                            rel_path = src_path.relative_to(generated_result_dir)
                            dest_path = final_output_dir / rel_path
                            dest_path.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(src_path, dest_path)

                # 4. 返回路径
                final_md_path = None
                final_json_path = None
                
                final_mds = list(final_output_dir.rglob("*.md"))
                if final_mds:
                    final_md_path = str(final_mds[0])
                    # 覆盖写入
                    Path(final_md_path).write_text(content, encoding="utf-8")
                
                final_jsons = list(final_output_dir.rglob("*_content_list.json"))
                if final_jsons: final_json_path = str(final_jsons[0])

                if not content.strip():
                    layout_pdfs = list(final_output_dir.rglob("*_layout.pdf"))
                    if layout_pdfs:
                        content = "> ⚠️ Text extraction returned empty content. Please check layout PDF."
                    else:
                        raise FileNotFoundError("No valid content generated.")

                return {
                    "markdown": content,
                    "result_path": str(final_output_dir),
                    "markdown_file": final_md_path,
                    "json_path": final_json_path,
                    "json_content": json_content
                }

        except Exception as e:
            logger.error(f"❌ Pipeline processing failed: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            raise

        finally:
            # =========================================================
            # [关键修改]
            # 移除之前的强制 self.cleanup()
            # 改为更新活跃时间戳，让后台线程处理释放
            # =========================================================
            self.is_processing = False
            self.last_active_time = time.time()
            logger.info("🏁 Task finished. Model remains loaded for fast reuse (Auto-sleep in 5min).")


# 全局单例
_engine = None

def get_engine(vlm_api_base: str = None) -> MinerUPipelineEngine:
    global _engine
    if _engine is None:
        _engine = MinerUPipelineEngine(vlm_api_base=vlm_api_base)
    return _engine
