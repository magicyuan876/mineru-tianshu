"""
PaddleOCR-VL-VLLM 解析引擎 (Ultimate Optimized Edition)
单例模式，每个进程只加载一次基础版面识别模型, OCR部分调用配置的API

功能增强:
1. [稳定性] 恢复串行流式处理，防止并发风暴冲垮 vLLM 服务
2. [防崩溃] 每次任务后严格清理 Pipeline 状态，防止跨任务状态污染导致的 NoneType 异常
3. [双向定位] 输出包含 bbox 的结构化数据 (json_content)，并注入 order 和 _page_width
4. [高可用] 内部闭包重试机制，支持单页降级
"""

import os
import gc
import json
import time
import requests
import traceback
import threading
from pathlib import Path
from typing import Optional, Dict, Any
from threading import Lock
from loguru import logger

# ==============================================================================
# 🚨 全局环境配置 (必须在导入 paddle/paddlex 之前设置)
# ==============================================================================
# 1. 限制 PaddleX 内部推理并发数为 1，绝对防止高并发请求冲垮 vLLM 的 Tokenizer
os.environ["PADDLEX_INFERENCE_PARALLEL_WORKER_NUM"] = "1"
# 2. 禁用模型源检查，加快启动速度 (内网环境必备)
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
# ==============================================================================

class PaddleOCRVLVLLMEngine:
    """
    PaddleOCR-VL-VLLM 解析引擎（企业级高可用版）
    """

    _instance: Optional["PaddleOCRVLVLLMEngine"] = None
    _lock = Lock()
    _pipeline = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, 
                 device: str = "cuda:0", 
                 vllm_api_base: str = None, 
                 model_name: str = "PaddleOCR-VL-1.5-0.9B"):
        if self._initialized:
            return

        with self._lock:
            if self._initialized:
                return

            self.device = device
            self.vllm_api_base = vllm_api_base or os.getenv("VLLM_API_BASE", "http://vllm-paddleocr:30023/v1")
            self.model_name = model_name

            if "cuda:" in device:
                try:
                    self.gpu_id = int(device.split(":")[-1])
                except ValueError:
                    self.gpu_id = 0
            else:
                self.gpu_id = 0

            self._check_gpu_availability()
            self._initialized = True

            logger.info("🔧 PaddleOCR-VL-VLLM Engine Initialized")
            logger.info(f"   Device: {self.device} (Physical GPU: {self.gpu_id})")
            logger.info(f"   VLLM API: {self.vllm_api_base}")
            logger.info(f"   Concurrency: Strict Serial Streaming")

    def _check_gpu_availability(self):
        try:
            import paddle
            if not paddle.is_compiled_with_cuda():
                logger.error("❌ PaddlePaddle is running on CPU! This model requires GPU.")
                return
            
            gpu_name = paddle.device.cuda.get_device_name(self.gpu_id)
            logger.info(f"✅ GPU Detected: {gpu_name}")
        except Exception:
            logger.warning("⚠️ Could not verify GPU status via PaddlePaddle")

    def _check_vllm_health(self) -> bool:
        """检查 VLLM 服务是否健康"""
        try:
            base_url = self.vllm_api_base.replace("/v1", "")
            health_url = f"{base_url}/health"
            try:
                requests.get(health_url, timeout=2)
                return True
            except:
                models_url = f"{self.vllm_api_base}/models"
                resp = requests.get(models_url, timeout=2)
                return resp.status_code == 200
        except Exception as e:
            logger.warning(f"⚠️ VLLM service check failed: {e}")
            return False

    def _load_pipeline(self):
        """加载管道"""
        if self._pipeline is not None:
            return self._pipeline

        with self._lock:
            if self._pipeline is not None:
                return self._pipeline

            if not self._check_vllm_health():
                logger.error(f"❌ VLLM service unreachable at {self.vllm_api_base}")

            logger.info("📥 Loading PaddleOCR-VL-VLLM Pipeline...")
            try:
                import paddle
                from paddleocr import PaddleOCRVL

                if paddle.is_compiled_with_cuda():
                    paddle.set_device(f"gpu:{self.gpu_id}")

                os.environ.setdefault("PADDLEX_HOME", "/root/.paddlex")
                
                self._pipeline = PaddleOCRVL(
                    vl_rec_backend="vllm-server",
                    vl_rec_server_url=self.vllm_api_base,
                )
                
                logger.info("✅ Pipeline loaded successfully")
                return self._pipeline

            except Exception as e:
                logger.error(f"❌ Pipeline load failed: {e}")
                logger.error(traceback.format_exc())
                raise

    def cleanup(self):
        """严格的资源和状态清理，防止跨任务污染"""
        with self._lock:
            self._pipeline = None 
            try:
                import paddle
                if paddle.device.is_compiled_with_cuda():
                    paddle.device.cuda.empty_cache()
                gc.collect()
            except:
                pass

    def parse(self, file_path: str, output_path: str, **kwargs) -> Dict[str, Any]:
        """
        解析文档入口
        """
        try:
            file_path = Path(file_path)
            output_path = Path(output_path)
            output_path.mkdir(parents=True, exist_ok=True)

            logger.info(f"🤖 Processing: {file_path.name}")
            
            # 每次任务重新加载，防止状态被上一个任务污染导致 NoneType 崩溃
            self.cleanup()
            pipeline = self._load_pipeline()

            # 参数映射
            param_mapping = {
                "useDocOrientationClassify": "use_doc_orientation_classify",
                "useDocUnwarping": "use_doc_unwarping",
                "useLayoutDetection": "use_layout_parsing",
                "useChartRecognition": "use_chart_recognition",
                "useSealRecognition": "use_seal_recognition",
                "useOcrForImageBlock": "use_ocr_for_image_block",
                "layoutNms": "layout_nms",
                "markdownIgnoreLabels": "markdown_ignore_labels",
                "mergeTables": "merge_tables",
                "relevelTitles": "relevel_titles",
                "restructurePages": "restructure_pages",
                "minPixels": "min_pixels",
                "maxPixels": "max_pixels",
            }

            predict_params = {"input": str(file_path)}
            defaults = {
                "use_layout_parsing": True,
                "use_doc_orientation_classify": False, 
                "use_doc_unwarping": False,
                "use_seal_recognition": True
            }
            for k, v in kwargs.items():
                if k in param_mapping:
                    predict_params[param_mapping[k]] = v
            for k, v in defaults.items():
                if k not in predict_params:
                    predict_params[k] = v

            # 内部状态存储
            markdown_pages = []
            markdown_list_obj = []
            json_list = []
            full_content_list = []
            page_count = 0

            # 闭包封装流式处理过程，保护内存
            def process_stream(params, current_pipeline):
                nonlocal page_count
                page_count = 0
                markdown_pages.clear()
                markdown_list_obj.clear()
                json_list.clear()
                full_content_list.clear()

                # 使用惰性生成器，杜绝使用 list() 导致的大规模并发风暴
                generator = current_pipeline.predict(**params)
                for res in generator:
                    page_count += 1
                    
                    if res is None:
                        logger.error(f"❌ Page {page_count} returned None result")
                        continue

                    page_output_dir = output_path / f"page_{page_count}"
                    page_output_dir.mkdir(parents=True, exist_ok=True)

                    try:
                        if hasattr(res, "save_to_img"): res.save_to_img(str(page_output_dir))
                        if hasattr(res, "save_to_json"): res.save_to_json(str(page_output_dir))
                    except: pass

                    if hasattr(res, "json") and res.json:
                        json_list.append(res.json)
                        if isinstance(res.json, dict):
                            blocks = res.json.get('res') or res.json.get('parsing_res_list') or []
                            page_width = res.json.get('width', 595.28)
                            if not isinstance(blocks, list):
                                if isinstance(blocks, dict) and ('bbox' in blocks or 'layout_bbox' in blocks):
                                    blocks = [blocks]
                                else:
                                    blocks = []

                            for block in blocks:
                                if not isinstance(block, dict): continue
                                clean_block = {
                                    "id": len(full_content_list) + 1,
                                    "page_idx": page_count - 1,
                                    "type": block.get('type') or block.get('block_label') or 'text',
                                    "text": block.get('text') or block.get('block_content') or '',
                                    "bbox": block.get('layout_bbox') or block.get('block_bbox') or block.get('bbox') or [],
                                    "score": block.get('score', 0),
                                    "order": block.get('block_order') or block.get('order'),
                                    "_page_width": page_width
                                }
                                if clean_block['bbox']:
                                    full_content_list.append(clean_block)

                    if hasattr(res, "markdown") and res.markdown:
                        markdown_list_obj.append(res.markdown)

                    page_md = ""
                    try:
                        if hasattr(res, "markdown") and res.markdown:
                            if isinstance(res.markdown, dict):
                                page_md = res.markdown.get('markdown_texts', '') or res.markdown.get('text', '')
                            elif hasattr(res.markdown, 'markdown_texts'):
                                page_md = res.markdown.markdown_texts
                            else:
                                page_md = str(res.markdown)
                        elif hasattr(res, "str") and res.str:
                            page_md = str(res.str)
                    except: pass

                    if page_md:
                        markdown_pages.append(page_md)
                    else:
                        try:
                             if hasattr(res, "save_to_markdown"):
                                res.save_to_markdown(str(page_output_dir))
                                saved = list(page_output_dir.glob("*.md"))
                                if saved:
                                    markdown_pages.append(saved[0].read_text(encoding="utf-8"))
                        except: pass
                    
                    logger.info(f"✅ Processed Page {page_count}")

            # =========================================================
            # 🚨 安全执行与降级重试
            # =========================================================
            try:
                process_stream(predict_params, pipeline)
            except Exception as e:
                logger.warning(f"⚠️ Standard stream failed (Pipeline state corrupted?): {e}")
                logger.info("🔄 Re-initializing and retrying with safe fallback parameters...")
                
                self.cleanup()
                pipeline = self._load_pipeline()
                
                predict_params["use_layout_parsing"] = False
                predict_params["use_chart_recognition"] = False
                predict_params["use_seal_recognition"] = False
                
                try:
                    process_stream(predict_params, pipeline)
                except Exception as fallback_e:
                    logger.error(f"❌ Fallback prediction also failed: {fallback_e}")
                    raise RuntimeError(f"VLM Worker crashed during generation. Internal Error: {fallback_e}")

            # 合并结果
            logger.info(f"🎉 Processing complete. Total pages: {page_count}")

            markdown_text = ""
            if hasattr(pipeline, "concatenate_markdown_pages") and markdown_list_obj:
                try:
                    markdown_text = pipeline.concatenate_markdown_pages(markdown_list_obj)
                except Exception as e:
                    markdown_text = "\n\n---\n\n".join(markdown_pages)
            else:
                markdown_text = "\n\n---\n\n".join(markdown_pages)

            markdown_file = output_path / "result.md"
            markdown_file.write_text(markdown_text, encoding="utf-8")
            
            json_file = output_path / "result.json"
            final_json_data = full_content_list if full_content_list else {
                "pages": json_list, 
                "total_pages": page_count
            }
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(final_json_data, f, ensure_ascii=False, indent=2)

            return {
                "success": True,
                "output_path": str(output_path),
                "markdown": markdown_text,
                "markdown_file": str(markdown_file),
                "json_file": str(json_file),
                "json_content": full_content_list
            }

        except Exception as e:
            logger.error(f"❌ OCR Pipeline Critical Error: {e}")
            logger.error(traceback.format_exc())
            raise
        finally:
            # 强制清理！这是多任务稳定运行的核心生命线
            self.cleanup()
            logger.info("🏁 Task finished. Pipeline cleaned up securely.")

# 全局单例
_engine = None

def get_engine(vllm_api_base: str = None, model_name: str = "PaddleOCR-VL-1.5-0.9B") -> PaddleOCRVLVLLMEngine:
    global _engine
    if _engine is None:
        _engine = PaddleOCRVLVLLMEngine(vllm_api_base=vllm_api_base, model_name=model_name)
    return _engine
