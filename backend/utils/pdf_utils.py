"""
PDF 处理工具函数
"""

from pathlib import Path
from typing import List, Optional
from loguru import logger


def convert_pdf_to_images(pdf_path: Path, output_dir: Path, zoom: float = 2.0, dpi: Optional[int] = None) -> List[Path]:
    """
    将 PDF 所有页转换为图片

    这是一个公用的工具函数，被 PaddleOCR-VL 等引擎共同使用。

    Args:
        pdf_path: PDF 文件路径
        output_dir: 输出目录
        zoom: 缩放比例（默认 2.0，即 2 倍）
        dpi: DPI 设置（可选，如果设置则会覆盖 zoom）

    Returns:
        转换后的图片路径列表

    Raises:
        RuntimeError: 如果 PyMuPDF 未安装或转换失败

    Example:
        >>> # 转换所有页
        >>> images = convert_pdf_to_images(
        ...     Path('document.pdf'),
        ...     Path('output/')
        ... )

        >>> # 自定义 DPI
        >>> images = convert_pdf_to_images(
        ...     Path('document.pdf'),
        ...     Path('output/'),
        ...     dpi=300
        ... )
    """
    try:
        import fitz  # PyMuPDF

        # 打开 PDF
        doc = fitz.open(str(pdf_path))

        # 获取页数
        page_count = len(doc)

        logger.info(f"📄 PDF has {page_count} pages")

        image_paths = []

        # 处理所有页面
        for page_num in range(page_count):
            page = doc[page_num]

            # 设置缩放/DPI
            if dpi:
                # 如果指定了 DPI，计算对应的缩放比例
                # 默认 PDF DPI 是 72
                zoom = dpi / 72.0

            mat = fitz.Matrix(zoom, zoom)

            # 渲染为图片
            pix = page.get_pixmap(matrix=mat)

            # 保存为 PNG（统一命名格式）
            image_path = output_dir / f"{pdf_path.stem}_page{page_num + 1}.png"

            pix.save(str(image_path))
            image_paths.append(image_path)

            logger.debug(f"   Converted page {page_num + 1}/{page_count} to PNG")

        # 关闭文档
        doc.close()

        logger.info(f"   Converted all {page_count} pages to PNG")

        return image_paths

    except ImportError:
        logger.error("❌ PyMuPDF not installed. Install with: pip install PyMuPDF")
        raise RuntimeError("PyMuPDF is required for PDF processing")
    except Exception as e:
        logger.error(f"❌ Failed to convert PDF to images: {e}")
        raise
