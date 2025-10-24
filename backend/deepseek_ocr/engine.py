"""
DeepSeek OCR 解析引擎
单例模式，每个进程只加载一次模型
"""
import os
import torch
from pathlib import Path
from typing import Optional, Dict, Any
from threading import Lock
from loguru import logger


class DeepSeekOCREngine:
    """
    DeepSeek OCR 解析引擎
    
    特性：
    - 单例模式（每个进程只加载一次模型）
    - 优先从 ModelScope 下载
    - 线程安全
    """
    
    _instance: Optional['DeepSeekOCREngine'] = None
    _lock = Lock()
    _model = None
    _tokenizer = None
    _initialized = False
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, cache_dir: Optional[str] = None, auto_download: bool = True):
        """
        初始化引擎（只执行一次）
        
        Args:
            cache_dir: 模型缓存目录，默认为项目目录下的 models/deepseek_ocr
            auto_download: 是否在初始化时自动下载模型（不加载到内存）
        """
        if self._initialized:
            return
        
        with self._lock:
            if self._initialized:
                return
            
            self.model_name = 'deepseek-ai/DeepSeek-OCR'
            
            # 默认缓存目录：项目根目录/models/deepseek_ocr
            if cache_dir is None:
                # 获取项目根目录（backend 的父目录）
                project_root = Path(__file__).parent.parent.parent
                self.cache_dir = str(project_root / 'models' / 'deepseek_ocr')
            else:
                self.cache_dir = cache_dir
            
            # 确保缓存目录存在
            Path(self.cache_dir).mkdir(parents=True, exist_ok=True)
            
            self.device = self._auto_select_device()
            self._initialized = True
            
            logger.info(f"🔧 DeepSeek OCR Engine initialized")
            logger.info(f"   Model: {self.model_name}")
            logger.info(f"   Device: {self.device}")
            logger.info(f"   Cache: {self.cache_dir}")
            
            # 总是检查本地模型
            # auto_download=False 时只检查不下载
            self._check_local_model()
            
            # 如果需要下载且本地不存在，才下载
            if auto_download and self.model_name == 'deepseek-ai/DeepSeek-OCR':
                self._ensure_model_downloaded()
    
    def _auto_select_device(self) -> str:
        """自动选择设备"""
        if torch.cuda.is_available():
            return 'cuda'
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            return 'mps'
        else:
            logger.error("=" * 80)
            logger.error("❌ CUDA 不可用! DeepSeek OCR 模型需要 GPU 支持")
            logger.error("")
            logger.error("📋 可能的原因:")
            logger.error("   1. 您的电脑没有 NVIDIA 显卡")
            logger.error("   2. 没有安装 CUDA 驱动")
            logger.error("   3. 安装的是 CPU 版本的 PyTorch")
            logger.error("")
            logger.error("🔧 解决方案:")
            logger.error("   如果您有 NVIDIA 显卡,请安装 GPU 版本的 PyTorch:")
            logger.error("   ")
            logger.error("   # 卸载当前版本")
            logger.error("   pip uninstall torch torchvision torchaudio")
            logger.error("   ")
            logger.error("   # 安装 CUDA 11.8 版本")
            logger.error("   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118")
            logger.error("   ")
            logger.error("   # 或者安装 CUDA 12.1 版本")
            logger.error("   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121")
            logger.error("")
            logger.error("=" * 80)
            
            raise RuntimeError(
                "DeepSeek OCR 需要 GPU 支持。请安装 GPU 版本的 PyTorch 或使用带有 NVIDIA 显卡的电脑。\n"
                "详细说明请查看上方错误信息。"
            )
    
    def _check_local_model(self):
        """检查本地模型是否存在（不下载）"""
        local_model_path = Path(self.cache_dir) / 'deepseek-ai' / 'DeepSeek-OCR'
        
        if local_model_path.exists():
            # 检查必需的模型文件
            required_files = ['config.json', 'tokenizer.json', 'modeling_deepseekocr.py', 'model-00001-of-000001.safetensors']
            missing_files = [f for f in required_files if not (local_model_path / f).exists()]
            
            if not missing_files:
                # 本地模型完整，更新 model_name 为本地路径
                self.model_name = str(local_model_path)
                logger.info(f"✅ Found complete local model at: {local_model_path}")
            else:
                logger.debug(f"   Local model incomplete, missing: {missing_files}")
        else:
            logger.debug(f"   Local model directory not found: {local_model_path}")
    
    def _ensure_model_downloaded(self):
        """确保模型已下载（不加载到内存）"""
        try:
            logger.info("🔍 Checking if model is downloaded...")
            
            # 首先检查本地是否已经有完整的模型文件
            local_model_path = Path(self.cache_dir) / 'deepseek-ai' / 'DeepSeek-OCR'
            logger.debug(f"   Checking local path: {local_model_path}")
            
            # 检查必需的模型文件是否存在
            required_files = ['config.json', 'tokenizer.json', 'modeling_deepseekocr.py', 'model-00001-of-000001.safetensors']
            
            if local_model_path.exists():
                missing_files = [f for f in required_files if not (local_model_path / f).exists()]
                
                if not missing_files:
                    # 本地模型完整，直接使用
                    self.model_name = str(local_model_path)
                    logger.info(f"✅ Local model is complete at: {local_model_path}")
                    logger.info("   Skipping download, will use local files")
                    return
                else:
                    logger.warning(f"⚠️  Local model incomplete, missing files: {missing_files}")
            else:
                logger.info(f"   Local model directory not found")
            
            # 只有在本地模型不完整时才下载
            logger.info("📥 Local model not found or incomplete, starting download...")
            
            # 配置下载源
            os.environ.setdefault('HF_ENDPOINT', 'https://hf-mirror.com')
            
            try:
                # 优先使用 ModelScope
                from modelscope import snapshot_download
                
                logger.info(f"📦 Using ModelScope to download model")
                
                # 下载模型（如果已存在则跳过）
                model_dir = snapshot_download(
                    'deepseek-ai/DeepSeek-OCR',
                    cache_dir=self.cache_dir
                )
                
                self.model_name = model_dir  # 使用本地路径
                logger.info(f"✅ Model downloaded at: {model_dir}")
                
            except ImportError:
                # ModelScope 不可用，使用 HuggingFace
                logger.info("📦 Using HuggingFace Hub to download")
                
                # 只下载模型配置，不加载模型
                # 这会触发模型文件下载但不占用 GPU/内存
                try:
                    from transformers import AutoConfig
                    AutoConfig.from_pretrained(
                        self.model_name,
                        trust_remote_code=True,
                        cache_dir=self.cache_dir
                    )
                    logger.info(f"✅ Model ready (will load on first use)")
                except Exception as e:
                    logger.warning(f"⚠️  Could not verify model: {e}")
                    logger.info("   Model will be downloaded on first use")
                    
        except Exception as e:
            logger.warning(f"⚠️  Model check/download failed: {e}")
            logger.info("   Model will be downloaded on first use")
    
    def _load_model(self):
        """延迟加载模型"""
        if self._model is not None and self._tokenizer is not None:
            return self._model, self._tokenizer
        
        with self._lock:
            if self._model is not None and self._tokenizer is not None:
                return self._model, self._tokenizer
            
            logger.info("=" * 60)
            logger.info("📥 Loading DeepSeek OCR Model into memory...")
            logger.info("=" * 60)
            
            try:
                from transformers import AutoTokenizer, AutoModel
                
                # 判断是否使用本地模型（路径而非模型ID）
                is_local = Path(self.model_name).exists()
                
                if is_local:
                    logger.info(f"📁 Loading from local path: {self.model_name}")
                else:
                    logger.info(f"🌐 Loading from HuggingFace: {self.model_name}")
                
                # 加载 tokenizer
                logger.info(f"📝 Loading tokenizer...")
                self._tokenizer = AutoTokenizer.from_pretrained(
                    self.model_name,
                    trust_remote_code=True,
                    local_files_only=is_local,
                    cache_dir=None if is_local else self.cache_dir
                )
                
                # 加载模型
                logger.info(f"🤖 Loading model...")
                
                try:
                    # 尝试使用 flash attention 2（需要 flash-attn 包）
                    self._model = AutoModel.from_pretrained(
                        self.model_name,
                        _attn_implementation='flash_attention_2',
                        trust_remote_code=True,
                        use_safetensors=True,
                        local_files_only=is_local,
                        cache_dir=None if is_local else self.cache_dir
                    )
                    logger.info("✅ Using flash_attention_2")
                except Exception as e:
                    # Flash attention 不可用时回退到默认实现
                    logger.warning(f"⚠️  Flash attention not available, using default attention")
                    logger.debug(f"   Reason: {e}")
                    
                    self._model = AutoModel.from_pretrained(
                        self.model_name,
                        trust_remote_code=True,
                        use_safetensors=True,
                        local_files_only=is_local,
                        cache_dir=None if is_local else self.cache_dir
                    )
                    logger.info("✅ Using default attention implementation")
                
                # 设置为评估模式并移到设备
                self._model = self._model.eval()
                
                logger.info(f"📤 Moving model to device: {self.device}")
                
                if self.device == 'cuda':
                    # 记录移动前的 GPU 状态
                    gpu_memory_before = torch.cuda.memory_allocated(0) / 1024**3
                    logger.info(f"   GPU 显存 (移动前): {gpu_memory_before:.2f}GB")
                    
                    self._model = self._model.cuda().to(torch.bfloat16)
                    
                    # 记录移动后的 GPU 状态
                    gpu_memory_after = torch.cuda.memory_allocated(0) / 1024**3
                    gpu_memory_total = torch.cuda.get_device_properties(0).total_memory / 1024**3
                    logger.info(f"   GPU 显存 (移动后): {gpu_memory_after:.2f}GB / {gpu_memory_total:.2f}GB")
                    logger.info(f"   模型占用显存: {gpu_memory_after - gpu_memory_before:.2f}GB")
                    
                elif self.device == 'mps':
                    self._model = self._model.to('mps')
                
                logger.info("=" * 60)
                logger.info("✅ DeepSeek OCR Model loaded successfully!")
                logger.info(f"   Device: {self.device}")
                if self.device == 'cuda':
                    logger.info(f"   GPU: {torch.cuda.get_device_name(0)}")
                    logger.info(f"   总显存: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f}GB")
                    logger.info(f"   已用显存: {torch.cuda.memory_allocated(0) / 1024**3:.2f}GB")
                logger.info("=" * 60)
                
                return self._model, self._tokenizer
                
            except Exception as e:
                logger.error("=" * 80)
                logger.error(f"❌ 模型加载失败:")
                logger.error(f"   错误类型: {type(e).__name__}")
                logger.error(f"   错误信息: {e}")
                logger.error("")
                logger.error("💡 排查建议:")
                logger.error("   1. 检查模型文件是否完整")
                logger.error("   2. 检查磁盘空间是否充足")
                logger.error("   3. 检查显存是否足够加载模型")
                if self.device == 'cuda':
                    try:
                        gpu_memory_total = torch.cuda.get_device_properties(0).total_memory / 1024**3
                        logger.error(f"   4. 当前 GPU 显存: {gpu_memory_total:.2f}GB")
                    except:
                        pass
                logger.error("=" * 80)
                
                import traceback
                logger.debug("完整堆栈跟踪:")
                logger.debug(traceback.format_exc())
                
                raise
    
    def _convert_pdf_to_images(self, pdf_path: Path, output_dir: Path) -> list:
        """
        将 PDF 所有页转换为图片
        
        Args:
            pdf_path: PDF 文件路径
            output_dir: 输出目录
            
        Returns:
            转换后的图片路径列表
        """
        # 使用公共工具函数转换所有页
        from utils.pdf_utils import convert_pdf_to_images
        return convert_pdf_to_images(pdf_path, output_dir)
    
    def cleanup(self):
        """
        清理推理产生的显存（不卸载模型）
        
        注意：
        - 只清理推理过程中产生的中间张量
        - 不会卸载已加载的模型（模型保持在显存中，下次推理更快）
        - 适合在每次推理完成后调用
        """
        try:
            import gc
            
            # 清理 PyTorch 显存缓存
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()  # 确保所有操作完成
                logger.debug("🧹 DeepSeek OCR: CUDA cache cleared")
            
            # 清理 Python 对象
            gc.collect()
            
            logger.debug("🧹 DeepSeek OCR: Memory cleanup completed")
        except Exception as e:
            logger.debug(f"Memory cleanup warning: {e}")
    
    def parse(
        self,
        file_path: str,
        output_path: str,
        resolution: str = 'base',
        prompt_type: str = 'document',
        **kwargs
    ) -> Dict[str, Any]:
        """
        解析文档或图片
        
        Args:
            file_path: 输入文件路径
            output_path: 输出目录
            resolution: 分辨率 (tiny/small/base/large/dynamic)
            prompt_type: 提示词类型 (document/image/free/figure)
            **kwargs: 其他参数
            
        Returns:
            解析结果
        """
        file_path = Path(file_path)
        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"🤖 DeepSeek OCR parsing: {file_path.name}")
        logger.info(f"   Resolution: {resolution}")
        
        # 检查文件类型，如果是 PDF 需要先转换为图片
        image_paths = []
        if file_path.suffix.lower() == '.pdf':
            logger.info("📄 PDF detected, converting all pages to images...")
            image_paths = self._convert_pdf_to_images(file_path, output_path)
            logger.info(f"✅ PDF converted: {len(image_paths)} pages")
        else:
            # 单张图片
            image_paths = [file_path]
        
        # 加载模型
        model, tokenizer = self._load_model()
        
        # 提示词模板
        prompts = {
            'document': '<image>\n<|grounding|>Convert the document to markdown.',
            'image': '<image>\n<|grounding|>OCR this image.',
            'free': '<image>\nFree OCR.',
            'figure': '<image>\nParse the figure.',
        }
        prompt = prompts.get(prompt_type, prompts['document'])
        
        # 分辨率配置
        resolutions = {
            'tiny': {'base_size': 512, 'image_size': 512},
            'small': {'base_size': 640, 'image_size': 640},
            'base': {'base_size': 1024, 'image_size': 1024},
            'large': {'base_size': 1280, 'image_size': 1280},
            'dynamic': {'base_size': 1024, 'image_size': 640},
        }
        res_config = resolutions.get(resolution, resolutions['base'])
        
        # 执行推理（处理所有页）
        try:
            logger.info(f"🚀 开始推理...")
            logger.info(f"   分辨率配置: base_size={res_config['base_size']}, image_size={res_config['image_size']}")
            logger.info(f"   共 {len(image_paths)} 个图像")
            logger.info(f"   提示词类型: {prompt_type}")
            
            # 记录 GPU 状态
            if self.device == 'cuda':
                gpu_memory_allocated = torch.cuda.memory_allocated(0) / 1024**3
                gpu_memory_reserved = torch.cuda.memory_reserved(0) / 1024**3
                gpu_memory_total = torch.cuda.get_device_properties(0).total_memory / 1024**3
                logger.info(f"   GPU 显存: 已分配 {gpu_memory_allocated:.2f}GB / 已保留 {gpu_memory_reserved:.2f}GB / 总计 {gpu_memory_total:.2f}GB")
            
            all_markdown_content = []
            
            # 处理每个图像（每页）
            for idx, img_path in enumerate(image_paths, 1):
                logger.info(f"📝 处理第 {idx}/{len(image_paths)} 页: {img_path.name}")
                
                # 为每页创建子目录
                page_output_dir = output_path / f"page_{idx}"
                page_output_dir.mkdir(parents=True, exist_ok=True)
                
                result = model.infer(
                    tokenizer,
                    prompt=prompt,
                    image_file=str(img_path),
                    output_path=str(page_output_dir),
                    base_size=res_config['base_size'],
                    image_size=res_config['image_size'],
                    crop_mode=True,
                    save_results=True,
                    test_compress=True
                )
                
                # 读取这一页的 MMD 文件
                page_mmd_file = page_output_dir / 'result.mmd'
                if page_mmd_file.exists():
                    try:
                        with open(page_mmd_file, 'r', encoding='utf-8') as f:
                            page_content = f.read()
                        
                        # 添加页标记
                        all_markdown_content.append(f"\n\n## 第 {idx} 页\n\n")
                        all_markdown_content.append(page_content)
                        
                        logger.info(f"   ✅ 第 {idx} 页处理完成")
                    except Exception as e:
                        logger.warning(f"   ⚠️  读取第 {idx} 页失败: {e}")
                else:
                    logger.warning(f"   ⚠️  第 {idx} 页未生成 MMD 文件")
            
            logger.info(f"✅ DeepSeek OCR completed - 共处理 {len(image_paths)} 页")
            
            # 合并所有页的内容
            markdown_content = ''.join(all_markdown_content)
            
            # 保存合并后的结果到主目录
            merged_mmd_file = output_path / 'result.mmd'
            if markdown_content:
                try:
                    merged_mmd_file.write_text(markdown_content, encoding='utf-8')
                    logger.info(f"📄 已合并所有页: {len(markdown_content)} 字符")
                except Exception as e:
                    logger.warning(f"⚠️  保存合并文件失败: {e}")
            else:
                logger.warning(f"⚠️  没有内容可合并")
            
            mmd_file = merged_mmd_file
            
            return {
                'success': True,
                'output_path': str(output_path),
                'markdown': markdown_content,  # 返回 Markdown 内容
                'mmd_file': str(mmd_file) if mmd_file.exists() else None,
                'result': result  # 保留原始结果
            }
        
        except RuntimeError as e:
            error_msg = str(e)
            logger.error("=" * 80)
            logger.error(f"❌ RuntimeError 异常详情:")
            logger.error(f"   错误类型: {type(e).__name__}")
            logger.error(f"   错误信息: {error_msg}")
            logger.error("")
            
            # CUDA 相关错误分析
            if 'CUDA' in error_msg or 'cuda' in error_msg or 'CUBLAS' in error_msg:
                logger.error("🔍 CUDA 错误分析:")
                
                # 显存相关
                if 'out of memory' in error_msg.lower():
                    logger.error("   类型: GPU 显存不足 (OOM)")
                    if self.device == 'cuda':
                        try:
                            gpu_memory_allocated = torch.cuda.memory_allocated(0) / 1024**3
                            gpu_memory_reserved = torch.cuda.memory_reserved(0) / 1024**3
                            gpu_memory_total = torch.cuda.get_device_properties(0).total_memory / 1024**3
                            logger.error(f"   当前显存: 已分配 {gpu_memory_allocated:.2f}GB / 已保留 {gpu_memory_reserved:.2f}GB / 总计 {gpu_memory_total:.2f}GB")
                        except:
                            pass
                    logger.error("")
                    logger.error("💡 建议:")
                    logger.error("   1. 使用更小的分辨率: 'small' 或 'tiny'")
                    logger.error("   2. 重启 worker 进程释放显存")
                    logger.error("   3. 关闭其他占用 GPU 的程序")
                
                # CUBLAS 错误
                elif 'CUBLAS' in error_msg or 'cublas' in error_msg:
                    logger.error("   类型: CUBLAS 矩阵运算错误")
                    logger.error("")
                    logger.error("🔍 可能原因:")
                    logger.error("   1. 显存碎片化或分配失败")
                    logger.error("   2. 输入张量尺寸导致索引越界")
                    logger.error("   3. CUDA 驱动与 PyTorch 版本不匹配")
                    logger.error("   4. GPU 状态异常")
                    logger.error("")
                    logger.error("💡 建议:")
                    logger.error("   1. 重启 worker 进程 (最重要!)")
                    logger.error("   2. 使用更小的分辨率")
                    logger.error("   3. 检查 CUDA 驱动版本: nvidia-smi")
                    if self.device == 'cuda':
                        try:
                            logger.error(f"   4. PyTorch CUDA 版本: {torch.version.cuda}")
                            logger.error(f"   5. GPU 型号: {torch.cuda.get_device_name(0)}")
                        except:
                            pass
                
                # 断言失败
                elif 'assertion' in error_msg.lower() or 'assert' in error_msg.lower():
                    logger.error("   类型: CUDA 内核断言失败")
                    logger.error("")
                    logger.error("🔍 可能原因:")
                    logger.error("   1. 张量索引越界 (索引超出数据范围)")
                    logger.error("   2. 输入数据形状与模型期望不匹配")
                    logger.error("   3. 显存损坏或异常")
                    logger.error("")
                    logger.error("💡 建议:")
                    logger.error("   1. 重启 worker 进程")
                    logger.error("   2. 检查输入图像是否损坏")
                    logger.error("   3. 尝试使用不同的分辨率")
                    logger.error(f"   4. 当前分辨率: {resolution} (base_size={res_config['base_size']})")
                
                else:
                    logger.error("   类型: 其他 CUDA 错误")
                    logger.error("")
                    logger.error("💡 建议:")
                    logger.error("   1. 重启 worker 进程")
                    logger.error("   2. 检查 nvidia-smi 输出")
                    logger.error("   3. 尝试降低分辨率")
                
                # GPU 状态信息
                if self.device == 'cuda':
                    try:
                        logger.error("")
                        logger.error("📊 当前 GPU 状态:")
                        gpu_memory_allocated = torch.cuda.memory_allocated(0) / 1024**3
                        gpu_memory_reserved = torch.cuda.memory_reserved(0) / 1024**3
                        gpu_memory_total = torch.cuda.get_device_properties(0).total_memory / 1024**3
                        logger.error(f"   显存: {gpu_memory_allocated:.2f}GB / {gpu_memory_total:.2f}GB (已分配)")
                        logger.error(f"   显存: {gpu_memory_reserved:.2f}GB / {gpu_memory_total:.2f}GB (已保留)")
                        logger.error(f"   设备: {torch.cuda.get_device_name(0)}")
                    except Exception as gpu_err:
                        logger.error(f"   无法获取 GPU 状态: {gpu_err}")
            
            else:
                logger.error("🔍 一般 RuntimeError:")
                logger.error(f"   详细信息: {error_msg}")
            
            logger.error("=" * 80)
            
            # 保留完整的堆栈信息
            import traceback
            logger.debug("完整堆栈跟踪:")
            logger.debug(traceback.format_exc())
            
            raise
            
        except ZeroDivisionError as e:
            # 专门处理除零错误（通常是分辨率太小导致）
            logger.error("=" * 80)
            logger.error(f"❌ 分辨率配置错误:")
            logger.error(f"   错误类型: ZeroDivisionError")
            logger.error(f"   错误信息: {e}")
            logger.error("")
            logger.error("🔍 原因分析:")
            logger.error(f"   当前分辨率 '{resolution}' 对于此图像来说太小")
            logger.error("   模型内部计算的 valid_img_tokens = 0")
            logger.error("   导致在计算压缩比时除以零")
            logger.error("")
            logger.error("💡 解决方案:")
            logger.error("   1. 使用更大的分辨率:")
            logger.error("      - 如果当前是 'tiny',  改用 'small'")
            logger.error("      - 如果当前是 'small', 改用 'base'")
            logger.error("   2. 检查输入图像是否正常")
            logger.error(f"   3. 当前分辨率配置: {resolution} (base_size={res_config['base_size']})")
            logger.error("")
            logger.error("📊 建议的分辨率选择:")
            logger.error("   - 简单文档/小图: small (640x640)")
            logger.error("   - 标准文档:      base  (1024x1024)")
            logger.error("   - 复杂文档:      large (1280x1280)")
            logger.error("=" * 80)
            
            # 保留完整的堆栈信息
            import traceback
            logger.debug("完整堆栈跟踪:")
            logger.debug(traceback.format_exc())
            
            raise RuntimeError(
                f"分辨率 '{resolution}' 对于此图像来说太小。"
                f"请使用更大的分辨率 (建议: small 或 base)。"
            )
            
        except Exception as e:
            error_msg = str(e)
            logger.error("=" * 80)
            logger.error(f"❌ 未预期的异常:")
            logger.error(f"   错误类型: {type(e).__name__}")
            logger.error(f"   错误信息: {error_msg}")
            logger.error("")
            logger.error("💡 建议:")
            logger.error("   1. 查看完整堆栈跟踪定位问题")
            logger.error("   2. 检查输入文件是否正常")
            logger.error("   3. 验证模型文件完整性")
            logger.error("=" * 80)
            
            # 保留完整的堆栈信息
            import traceback
            logger.debug("完整堆栈跟踪:")
            logger.debug(traceback.format_exc())
            
            raise
        
        finally:
            # 清理显存（无论成功或失败都执行）
            self.cleanup()


# 全局单例
_engine = None

def get_engine() -> DeepSeekOCREngine:
    """获取全局引擎实例"""
    global _engine
    if _engine is None:
        _engine = DeepSeekOCREngine()
    return _engine

