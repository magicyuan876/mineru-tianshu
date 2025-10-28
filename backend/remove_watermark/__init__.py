"""
水印去除模块

基于 YOLO11x + LaMa 的智能水印检测与去除系统
- 图片水印去除：YOLO11x 检测 + LaMa 修复
- PDF 水印处理：自动检测可编辑/扫描件并智能处理
"""

from .watermark_remover import WatermarkRemover
from .pdf_watermark_handler import PDFWatermarkHandler

__all__ = [
    "WatermarkRemover",
    "PDFWatermarkHandler",
]

__version__ = "2.0.0"
