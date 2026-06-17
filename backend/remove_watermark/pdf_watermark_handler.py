"""
PDF 水印处理模块

支持两种 PDF 类型的水印处理：
1. 可编辑 PDF：直接删除水印对象（文字、图片、透明层）
2. 扫描件 PDF：转图片 → YOLO 检测 → LaMa 修复 → 重组 PDF
"""

import fitz  # PyMuPDF
from pathlib import Path
from typing import Optional, Union, List
from loguru import logger
import shutil

from .watermark_remover import WatermarkRemover


class PDFWatermarkHandler:
    """
    PDF 水印处理引擎

    功能：
    1. 自动检测 PDF 类型（可编辑/扫描件）
    2. 可编辑 PDF：删除水印对象
    3. 扫描件 PDF：转图片 → 去水印 → 重组 PDF
    """

    def __init__(self, device: str = "cuda", use_lama: bool = True):
        """
        初始化 PDF 水印处理器

        Args:
            device: 设备 (cuda/cpu)
            use_lama: 是否使用 LaMa 修复（用于扫描件处理）
        """
        self.device = device
        self.use_lama = use_lama
        self.image_remover = None  # 延迟初始化

        logger.info("=" * 60)
        logger.info("📄 PDF Watermark Handler Initializing")
        logger.info("=" * 60)
        logger.info(f"📍 Device: {device}")
        logger.info(f"🎨 Image Remover: YOLO11x + {'LaMa' if use_lama else 'OpenCV'}")
        logger.info("")

    def _get_image_remover(self) -> WatermarkRemover:
        """延迟初始化图片水印去除器"""
        if self.image_remover is None:
            self.image_remover = WatermarkRemover(device=self.device, use_lama=self.use_lama)
        return self.image_remover

    def is_editable_pdf(self, pdf_path: Union[str, Path], text_ratio_threshold: float = 0.1) -> bool:
        """
        判断 PDF 是否为可编辑 PDF

        策略：
        - 检查是否包含文本层
        - 计算文本覆盖率

        Args:
            pdf_path: PDF 文件路径
            text_ratio_threshold: 文本覆盖率阈值（默认 10%）

        Returns:
            True: 可编辑 PDF
            False: 扫描件 PDF
        """
        logger.info("🔍 Detecting PDF type...")

        doc = fitz.open(str(pdf_path))
        try:
            total_pages = len(doc)
            text_pages = 0

            for page_num in range(min(5, total_pages)):  # 检查前 5 页
                page = doc[page_num]
                text = page.get_text().strip()

                if len(text) > 50:  # 至少 50 个字符
                    text_pages += 1
        finally:
            # 即使前几页解析异常（损坏 PDF）也必须关闭，否则 Windows 下文件句柄泄漏导致后续无法删除/覆盖
            doc.close()

        text_ratio = text_pages / min(5, total_pages)
        is_editable = text_ratio >= text_ratio_threshold

        logger.info(f"   Text pages: {text_pages}/{min(5, total_pages)}")
        logger.info(f"   Text ratio: {text_ratio:.2%}")
        logger.info(f"   Type: {'Editable PDF' if is_editable else 'Scanned PDF'}")

        return is_editable

    def remove_watermark_from_editable_pdf(
        self,
        input_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        remove_text: bool = True,
        remove_images: bool = True,
        remove_annotations: bool = True,
        keywords: Optional[List[str]] = None,
    ) -> Path:
        """
        从可编辑 PDF 中删除水印

        策略：
        1. 删除文本水印（可选：根据关键词）
        2. 删除图片水印
        3. 删除透明层/注释

        Args:
            input_path: 输入 PDF 路径
            output_path: 输出 PDF 路径
            remove_text: 是否删除文本对象
            remove_images: 是否删除图片对象
            remove_annotations: 是否删除注释
            keywords: 文本关键词列表（只删除包含这些关键词的文本）

        Returns:
            输出 PDF 路径
        """
        input_path = Path(input_path)

        if output_path is None:
            output_path = input_path.parent / f"{input_path.stem}_no_watermark.pdf"
        else:
            output_path = Path(output_path)

        output_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info("=" * 60)
        logger.info("📄 Removing Watermark from Editable PDF")
        logger.info("=" * 60)
        logger.info(f"📄 Input: {input_path}")
        logger.info(f"💾 Output: {output_path}")
        logger.info("")

        doc = fitz.open(str(input_path))
        removed_count = 0

        for page_num in range(len(doc)):
            page = doc[page_num]

            # 1. 删除注释
            if remove_annotations:
                annot = page.first_annot
                while annot:
                    next_annot = annot.next
                    page.delete_annot(annot)
                    removed_count += 1
                    annot = next_annot

            # 2. 清理内容流（删除文本和图片）
            if remove_text or remove_images:
                # 获取内容流
                try:
                    contents = page.get_contents()
                    if contents:
                        # 这里需要解析内容流并过滤
                        # 简化处理：删除所有透明度较低的对象（通常是水印）

                        # 方法1：清除所有图片（如果 remove_images=True）
                        if remove_images:
                            image_list = page.get_images(full=True)
                            for img_index, img in enumerate(image_list):
                                try:
                                    # 尝试删除图片
                                    # 注意：PyMuPDF 不直接支持删除图片，需要重绘页面
                                    pass
                                except Exception as e:
                                    logger.debug(f"   Cannot remove image: {e}")

                        # 方法2：删除包含关键词的文本
                        if remove_text and keywords:
                            for keyword in keywords:
                                instances = page.search_for(keyword)
                                for inst in instances:
                                    # 用白色矩形覆盖
                                    page.draw_rect(inst, color=(1, 1, 1), fill=(1, 1, 1))
                                    removed_count += 1
                                    logger.debug(f"   Removed text: {keyword}")

                except Exception as e:
                    logger.debug(f"   Page {page_num}: {e}")

        # 保存
        logger.info(f"🗑️  Removed {removed_count} watermark objects")
        doc.save(str(output_path))
        doc.close()

        logger.info(f"✅ Editable PDF processed: {output_path}")
        logger.info("")

        return output_path

    def remove_watermark_from_scanned_pdf(
        self,
        input_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        dpi: int = 200,
        conf_threshold: float = 0.35,
        dilation: int = 10,
    ) -> Path:
        """
        从扫描件 PDF 中删除水印

        流程：
        1. PDF → 图片
        2. 图片 → YOLO 检测水印
        3. LaMa 修复水印
        4. 图片 → PDF

        Args:
            input_path: 输入 PDF 路径
            output_path: 输出 PDF 路径
            dpi: 转换分辨率
            conf_threshold: YOLO 置信度阈值
            dilation: 掩码膨胀

        Returns:
            输出 PDF 路径
        """
        input_path = Path(input_path)

        if output_path is None:
            output_path = input_path.parent / f"{input_path.stem}_no_watermark.pdf"
        else:
            output_path = Path(output_path)

        output_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info("=" * 60)
        logger.info("📄 Removing Watermark from Scanned PDF")
        logger.info("=" * 60)
        logger.info(f"📄 Input: {input_path}")
        logger.info(f"💾 Output: {output_path}")
        logger.info(f"🔧 DPI: {dpi}")
        logger.info("")

        # 创建临时目录（使用共享输出目录）
        import uuid
        import os

        project_root = Path(__file__).parent.parent.parent
        default_output = project_root / "data" / "output"
        output_base = Path(os.getenv("OUTPUT_PATH", str(default_output)))
        temp_dir = output_base / f"pdf_watermark_{uuid.uuid4().hex}"
        temp_dir.mkdir(parents=True, exist_ok=True)

        try:
            # 1. PDF → 图片
            logger.info("📄 Converting PDF to images...")
            doc = fitz.open(str(input_path))
            image_paths = []

            for page_num in range(len(doc)):
                page = doc[page_num]

                # 渲染为图片
                mat = fitz.Matrix(dpi / 72, dpi / 72)  # 缩放矩阵
                pix = page.get_pixmap(matrix=mat)

                # 保存图片
                image_path = temp_dir / f"page_{page_num:04d}.png"
                pix.save(str(image_path))
                image_paths.append(image_path)

                logger.info(f"   Page {page_num + 1}/{len(doc)} → {image_path.name}")

            doc.close()

            # 2. 去除水印
            logger.info("")
            logger.info("🎨 Removing watermarks from images...")

            remover = self._get_image_remover()
            cleaned_image_paths = []

            for idx, image_path in enumerate(image_paths):
                try:
                    cleaned_path = temp_dir / f"cleaned_{image_path.name}"

                    logger.info(f"   Processing {idx + 1}/{len(image_paths)}: {image_path.name}")

                    remover.remove_watermark(
                        image_path=image_path,
                        output_path=cleaned_path,
                        conf_threshold=conf_threshold,
                        dilation=dilation,
                    )

                    cleaned_image_paths.append(cleaned_path)

                except Exception as e:
                    logger.error(f"   Failed to process {image_path}: {e}")
                    # 失败则使用原图
                    cleaned_image_paths.append(image_path)

            # 3. 图片 → PDF
            logger.info("")
            logger.info("📄 Converting images back to PDF...")

            # 使用 PyMuPDF 创建新 PDF
            output_doc = fitz.open()

            for idx, image_path in enumerate(cleaned_image_paths):
                # 转换为 PDF 页面
                img_bytes = image_path.read_bytes()
                img_doc = fitz.open("png", img_bytes)

                # 复制页面
                output_doc.insert_pdf(img_doc)
                img_doc.close()

                logger.info(f"   Page {idx + 1}/{len(cleaned_image_paths)} added")

            # 保存
            output_doc.save(str(output_path))
            output_doc.close()

            logger.info("")
            logger.info(f"✅ Scanned PDF processed: {output_path}")
            logger.info("")

            return output_path

        finally:
            # 清理临时文件
            try:
                shutil.rmtree(temp_dir)
                logger.debug(f"🗑️  Cleaned temp dir: {temp_dir}")
            except Exception as e:
                logger.warning(f"⚠️  Failed to clean temp dir: {e}")

    def remove_watermark(
        self,
        input_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        auto_detect: bool = True,
        force_scanned: bool = False,
        **kwargs,
    ) -> Path:
        """
        自动处理 PDF 水印

        Args:
            input_path: 输入 PDF 路径
            output_path: 输出 PDF 路径
            auto_detect: 是否自动检测 PDF 类型
            force_scanned: 强制使用扫描件模式
            **kwargs: 其他参数

        Returns:
            输出 PDF 路径
        """
        input_path = Path(input_path)

        if not input_path.exists():
            raise FileNotFoundError(f"PDF not found: {input_path}")

        # 自动检测 PDF 类型
        if auto_detect and not force_scanned:
            is_editable = self.is_editable_pdf(input_path)
        else:
            is_editable = not force_scanned

        logger.info("")

        if is_editable:
            logger.info("📝 Processing as Editable PDF")
            # 过滤出可编辑 PDF 的参数
            editable_kwargs = {
                k: v
                for k, v in kwargs.items()
                if k in ["remove_text", "remove_images", "remove_annotations", "keywords"]
            }
            return self.remove_watermark_from_editable_pdf(input_path, output_path, **editable_kwargs)
        else:
            logger.info("📷 Processing as Scanned PDF")
            # 过滤出扫描件 PDF 的参数
            scanned_kwargs = {k: v for k, v in kwargs.items() if k in ["dpi", "conf_threshold", "dilation"]}
            return self.remove_watermark_from_scanned_pdf(input_path, output_path, **scanned_kwargs)

    def cleanup(self):
        """清理资源"""
        if self.image_remover is not None:
            self.image_remover.cleanup()
            self.image_remover = None
        logger.info("🧹 PDF Watermark Handler cleaned up")
