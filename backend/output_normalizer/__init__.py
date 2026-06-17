"""
输出结果规范化模块

统一不同解析引擎的输出格式，确保：
1. Markdown 文件名统一为 result.md
2. 图片目录统一为 images/
3. 图片引用路径统一为 images/xxx.jpg
4. JSON 文件名统一为 result.json
5. 自动上传图片到 RustFS 对象存储并替换 URL

支持的引擎：
- MinerU (pipeline)
- PaddleOCR-VL
- SenseVoice
- Video Processing
- Format Engines (FASTA, GenBank, etc.)
"""

from pathlib import Path
from typing import Dict, Any, Optional
from loguru import logger

from .base_output_normalizer import BaseOutputNormalizer
from .standard_output_normalizer import StandardOutputNormalizer
from .paddleocr_output_normalizer import PaddleOCROutputNormalizer

# 全局单例实例
_standard_normalizer = StandardOutputNormalizer()
_paddleocr_normalizer = PaddleOCROutputNormalizer()


def normalize_output(output_dir: Path, handle_method="standard", use_rustfs: Optional[bool] = None) -> Dict[str, Any]:
    """
    便捷函数：规范化输出目录

    根据指定的处理方法选择合适的规范化器：
    - standard: 使用通用规范化 (StandardOutputNormalizer)
    - paddleocr-vl: 使用 PaddleOCR-VL 专用规范化 (PaddleOCROutputNormalizer)

    Args:
        output_dir: 输出目录路径
        handle_method: 处理方法，默认为 "standard"。支持 "standard" 或 "paddleocr-vl"
        use_rustfs: 任务级 RustFS 开关。None=由 RUSTFS_ENABLED 环境变量决定（向后兼容）；
                    True/False=按任务强制开启/关闭

    Returns:
        Dict[str, Any]: 规范化后的文件信息
    """
    ## 兼容handle_method未设置的老模式(基于output_dir 是否包含page_* 目录判断是否为PaddleOCR-VL输出)
    output_dir = Path(output_dir)
    is_paddle_ocr_output = list(output_dir.glob("page_*"))
    if is_paddle_ocr_output:
        logger.info("🤖 Detected PaddleOCR-VL output format")
        handle_method = "paddleocr-vl"
    ## 基于handle_method选择规范化器
    if handle_method == "standard":
        logger.info("🤖 Using standard output normalize method")
        return _standard_normalizer.normalize(output_dir, use_rustfs=use_rustfs)
    elif handle_method == "paddleocr-vl":
        logger.info("🤖 Using PaddleOCR-VL output normalize method")
        return _paddleocr_normalizer.normalize(output_dir, use_rustfs=use_rustfs)
    else:
        raise ValueError(f"Unknown output_normalize handle_method: {handle_method}")


__all__ = [
    "BaseOutputNormalizer",
    "StandardOutputNormalizer",
    "PaddleOCROutputNormalizer",
    "normalize_output",
]
