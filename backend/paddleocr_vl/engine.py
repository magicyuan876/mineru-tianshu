"""
PaddleOCR-VL 解析引擎
单例模式，每个进程只加载一次模型
使用最新的 PaddleOCR-VL API（自动多语言识别）

参考文档：http://www.paddleocr.ai/main/version3.x/pipeline_usage/PaddleOCR-VL.html

重要提示：
- PaddleOCR-VL 仅支持 GPU 推理，不支持 CPU 及 Arm 架构
- GPU 要求：Compute Capability ≥ 8.5 (RTX 3090, A10, A100, H100 等)
- 模型会自动下载到 ~/.paddleocr/models/ 目录（PaddleOCR 自动管理）
- 不支持手动指定本地模型路径，模型由 PaddleOCR 自动管理
"""
from pathlib import Path
from typing import Optional, Dict, Any
from threading import Lock
from loguru import logger


class PaddleOCRVLEngine:
    """
    PaddleOCR-VL 解析引擎（新版本）
    
    特性：
    - 单例模式（每个进程只加载一次模型）
    - 自动多语言识别（无需指定语言，支持 109+ 语言）
    - 线程安全
    - 仅支持 GPU 推理（不支持 CPU）
    - 原生支持 PDF 多页文档
    - 结构化输出（Markdown/JSON）
    - 模型自动下载和缓存（由 PaddleOCR 管理，无需手动下载）
    
    GPU 要求：
    - NVIDIA GPU with Compute Capability ≥ 8.5
    - 推荐：RTX 3090, RTX 4090, A10, A100, H100
    
    模型管理：
    - 模型由 PaddleOCR 自动下载和管理
    - 默认缓存位置：~/.paddleocr/models/
    - 不支持手动指定本地模型路径
    """
    
    _instance: Optional['PaddleOCRVLEngine'] = None
    _lock = Lock()
    _pipeline = None
    _initialized = False
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """
        初始化引擎（只执行一次）
        
        注意：
        - PaddleOCR-VL 会自动管理模型的下载和缓存
        - 模型默认缓存在 ~/.paddleocr/models/
        """
        if self._initialized:
            return
        
        with self._lock:
            if self._initialized:
                return
            
            # 检查 GPU 可用性（PaddleOCR-VL 仅支持 GPU）
            self._check_gpu_availability()
            
            self._initialized = True
            
            logger.info(f"🔧 PaddleOCR-VL Engine initialized")
            logger.info(f"   Model: PaddlePaddle/PaddleOCR-VL (auto-managed)")
            logger.info(f"   Auto Multi-Language: Enabled (109+ languages)")
            logger.info(f"   GPU Only: CPU not supported")
            logger.info(f"   Model Cache: ~/.paddleocr/models/ (auto-managed)")
    
    def _check_gpu_availability(self):
        """
        检查 GPU 信息并输出日志
        PaddleOCR-VL 仅支持 GPU 推理，但不阻止低版本 GPU 运行
        """
        try:
            import paddle
            
            # 检查是否编译了 CUDA 支持
            if not paddle.is_compiled_with_cuda():
                logger.warning("⚠️  PaddlePaddle is not compiled with CUDA")
                logger.warning("   PaddleOCR-VL requires GPU support")
                logger.warning("   Install: pip install paddlepaddle-gpu==3.2.0")
                return
            
            # 检查是否有可用的 GPU
            gpu_count = paddle.device.cuda.device_count()
            if gpu_count == 0:
                logger.warning("⚠️  No CUDA devices found")
                logger.warning("   PaddleOCR-VL requires GPU for inference")
                return
            
            # 获取 GPU 信息
            try:
                gpu_name = paddle.device.cuda.get_device_name(0)
                compute_capability = paddle.device.cuda.get_device_capability(0)
                
                logger.info(f"✅ GPU detected: {gpu_name}")
                logger.info(f"   Compute Capability: {compute_capability[0]}.{compute_capability[1]}")
                logger.info(f"   GPU Count: {gpu_count}")
                
                # 仅输出建议，不阻止运行
                cc_major = compute_capability[0]
                cc_minor = compute_capability[1]
                if cc_major < 8 or (cc_major == 8 and cc_minor < 5):
                    logger.info("ℹ️  GPU Compute Capability < 8.5")
                    logger.info("   Official recommendation: CC ≥ 8.5 for best performance")
                    logger.info("   Your GPU may still work, but performance might vary")
            except Exception as e:
                logger.debug(f"Could not get detailed GPU info: {e}")
            
        except ImportError:
            logger.warning("⚠️  PaddlePaddle not installed")
            logger.warning("   Install: pip install paddlepaddle-gpu==3.2.0")
        except Exception as e:
            logger.debug(f"GPU check warning: {e}")
    
    
    def _load_pipeline(self):
        """延迟加载 PaddleOCR-VL 管道"""
        if self._pipeline is not None:
            return self._pipeline
        
        with self._lock:
            if self._pipeline is not None:
                return self._pipeline
            
            logger.info("=" * 60)
            logger.info("📥 Loading PaddleOCR-VL Pipeline into memory...")
            logger.info("=" * 60)
            
            try:
                from paddleocr import PaddleOCRVL
                
                # 初始化 PaddleOCR-VL（新版本 API）
                # 为了最佳识别效果，启用所有增强功能
                logger.info(f"🤖 Initializing PaddleOCR-VL with enhanced features...")
                logger.info(f"   ✅ Document Orientation Classification: Enabled")
                logger.info(f"   ✅ Document Unwarping (Text Correction): Enabled")
                logger.info(f"   ✅ Layout Detection & Sorting: Enabled")
                logger.info(f"   ✅ Auto Multi-Language Recognition: Enabled (109+ languages)")
                logger.info(f"   🌐 Model will be auto-downloaded on first use if not cached")
                
                # 创建 PaddleOCRVL 实例（按照官方文档最佳实践）
                # 参考: http://www.paddleocr.ai/main/version3.x/pipeline_usage/PaddleOCR-VL.html
                self._pipeline = PaddleOCRVL(
                    use_doc_orientation_classify=True,  # 文档方向分类，自动旋转文档
                    use_doc_unwarping=True,             # 文本图像矫正，修正扭曲变形
                    use_layout_detection=True           # 版面区域检测排序，智能排版
                )
                
                logger.info("=" * 60)
                logger.info("✅ PaddleOCR-VL Pipeline loaded successfully!")
                logger.info("   Features: Orientation correction, Text unwarping, Layout detection")
                logger.info("=" * 60)
                
                return self._pipeline
                
            except Exception as e:
                logger.error("=" * 80)
                logger.error(f"❌ 管道加载失败:")
                logger.error(f"   错误类型: {type(e).__name__}")
                logger.error(f"   错误信息: {e}")
                logger.error("")
                logger.error("💡 排查建议:")
                logger.error("   1. 确保已安装正确版本:")
                logger.error("      pip install paddlepaddle-gpu==3.2.0")
                logger.error("      pip install 'paddleocr[doc-parser]'")
                logger.error("   2. 安装 SafeTensors:")
                logger.error("      pip install https://paddle-whl.bj.bcebos.com/nightly/cu126/safetensors/safetensors-0.6.2.dev0-cp38-abi3-linux_x86_64.whl")
                logger.error("   3. 检查 GPU 可用性:")
                logger.error("      python -c 'import paddle; print(paddle.device.is_compiled_with_cuda())'")
                logger.error("   4. 检查磁盘空间是否充足")
                logger.error("   5. 检查网络连接（首次使用需要下载模型）")
                logger.error("")
                logger.error("参考文档: http://www.paddleocr.ai/main/version3.x/pipeline_usage/PaddleOCR-VL.html")
                logger.error("=" * 80)
                
                import traceback
                logger.debug("完整堆栈跟踪:")
                logger.debug(traceback.format_exc())
                
                raise
    
    def cleanup(self):
        """
        清理推理产生的显存（不卸载模型）
        
        注意：
        - 只清理推理过程中产生的中间张量
        - 不会卸载已加载的模型（模型保持在显存中，下次推理更快）
        - 适合在每次推理完成后调用
        """
        try:
            import paddle
            import gc
            
            # 清理 PaddlePaddle 显存
            if paddle.device.is_compiled_with_cuda():
                paddle.device.cuda.empty_cache()
                logger.debug("🧹 PaddleOCR-VL: CUDA cache cleared")
            
            # 清理 Python 对象
            gc.collect()
            
            logger.debug("🧹 PaddleOCR-VL: Memory cleanup completed")
        except Exception as e:
            logger.debug(f"Memory cleanup warning: {e}")
    
    def parse(
        self,
        file_path: str,
        output_path: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        解析文档或图片
        
        Args:
            file_path: 输入文件路径
            output_path: 输出目录
            **kwargs: 其他参数（PaddleOCR-VL 会自动识别语言）
            
        Returns:
            解析结果（同时保存 Markdown 和 JSON 两种格式）
        """
        file_path = Path(file_path)
        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"🤖 PaddleOCR-VL parsing: {file_path.name}")
        logger.info(f"   Auto language detection enabled")
        
        # 加载管道
        pipeline = self._load_pipeline()
        
        # 执行推理
        try:
            logger.info(f"🚀 开始使用 PaddleOCR-VL 识别...")
            logger.info(f"   输入文件: {file_path}")
            logger.info(f"   自动语言检测: 支持 109+ 语言")
            
            # PaddleOCR-VL 的 predict 方法可以直接处理 PDF 或图片
            # 它会自动处理多页文档和语言检测
            result = pipeline.predict(str(file_path))
            
            logger.info(f"✅ PaddleOCR-VL completed")
            logger.info(f"   识别了 {len(result)} 页/张")
            
            # 按照官方示例处理结果
            markdown_list = []
            json_list = []
            
            for idx, res in enumerate(result, 1):
                logger.info(f"📝 处理结果 {idx}/{len(result)}")
                
                try:
                    # 为每页创建子目录并保存完整结果（便于调试）
                    page_output_dir = output_path / f"page_{idx}"
                    page_output_dir.mkdir(parents=True, exist_ok=True)
                    
                    # 保存 JSON（结构化数据）
                    if hasattr(res, 'save_to_json'):
                        res.save_to_json(save_path=str(page_output_dir))
                    
                    # 保存 Markdown 文件（便于调试）
                    if hasattr(res, 'save_to_markdown'):
                        res.save_to_markdown(save_path=str(page_output_dir))
                    
                    # 按照官方示例：收集每页的 markdown 对象
                    if hasattr(res, 'markdown'):
                        md_info = res.markdown
                        markdown_list.append(md_info)
                        logger.info(f"   ✅ 提取成功")
                    else:
                        logger.warning(f"   ⚠️  无法提取内容")
                    
                    # 收集 JSON 数据
                    if hasattr(res, 'json'):
                        json_data = res.json
                        json_list.append(json_data)
                    
                except Exception as e:
                    logger.warning(f"   处理出错: {e}")
                    import traceback
                    logger.debug(traceback.format_exc())
            
            # 使用官方方法合并所有页的 Markdown
            if hasattr(pipeline, 'concatenate_markdown_pages'):
                markdown_text = pipeline.concatenate_markdown_pages(markdown_list)
                logger.info(f"   使用官方 concatenate_markdown_pages() 方法合并")
            else:
                # 降级方案：手动合并
                logger.warning(f"   未找到 concatenate_markdown_pages() 方法，使用降级方案")
                markdown_text = '\n\n---\n\n'.join([
                    str(md) if isinstance(md, str) else str(md.get('text', '')) 
                    for md in markdown_list
                ])
            
            # 保存合并后的 Markdown 文件
            markdown_file = output_path / 'result.md'
            markdown_file.write_text(markdown_text, encoding='utf-8')
            logger.info(f"📄 Markdown 已保存: {markdown_file}")
            logger.info(f"   {len(result)} 页 | {len(markdown_text):,} 字符")
            
            # 始终保存 JSON 文件（方便用户后续选择）
            json_file = None
            if json_list:
                import json as json_lib
                json_file = output_path / 'result.json'
                # 合并所有页的 JSON
                combined_json = {
                    'pages': json_list,
                    'total_pages': len(result)
                }
                with open(json_file, 'w', encoding='utf-8') as f:
                    json_lib.dump(combined_json, f, ensure_ascii=False, indent=2)
                logger.info(f"📄 JSON 已保存: {json_file}")
            else:
                logger.warning(f"⚠️  无法提取 JSON 数据")
            
            return {
                'success': True,
                'output_path': str(output_path),
                'markdown': markdown_text,
                'markdown_file': str(markdown_file),
                'json_file': str(json_file) if json_file else None,
                'result': result
            }
            
        except Exception as e:
            logger.error("=" * 80)
            logger.error(f"❌ OCR 解析失败:")
            logger.error(f"   错误类型: {type(e).__name__}")
            logger.error(f"   错误信息: {e}")
            logger.error("=" * 80)
            
            import traceback
            logger.debug("完整堆栈跟踪:")
            logger.debug(traceback.format_exc())
            
            raise
        
        finally:
            # 清理显存（无论成功或失败都执行）
            self.cleanup()


# 全局单例
_engine = None

def get_engine() -> PaddleOCRVLEngine:
    """获取全局引擎实例"""
    global _engine
    if _engine is None:
        _engine = PaddleOCRVLEngine()
    return _engine

