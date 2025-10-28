"""
水印去除引擎

使用 YOLO11x 检测水印位置，LaMa 模型修复图像
"""

import cv2
import numpy as np
from PIL import Image
from pathlib import Path
from typing import List, Tuple, Optional, Union
from loguru import logger

try:
    from ultralytics import YOLO

    ULTRALYTICS_AVAILABLE = True
except ImportError:
    ULTRALYTICS_AVAILABLE = False

try:
    from simple_lama_inpainting import SimpleLama

    LAMA_AVAILABLE = True
except ImportError:
    LAMA_AVAILABLE = False


class WatermarkRemover:
    """
    水印去除器

    工作流程:
    1. YOLO11x 检测水印位置
    2. 生成掩码
    3. LaMa 修复图像

    如果未检测到水印，则返回原图
    """

    # 默认使用 HuggingFace 上的 YOLO11x 水印检测模型
    DEFAULT_MODEL_ID = "corzent/yolo11x_watermark_detection"

    def __init__(self, model_path: Optional[str] = None, device: str = "cuda", use_lama: bool = True):
        """
        初始化水印去除器

        Args:
            model_path: YOLO 模型路径
                - None: 使用默认模型 (corzent/yolo11x_watermark_detection)
                - HuggingFace ID: "username/model-name"
                - 本地路径: "/path/to/model.pt"
            device: 设备 ("cuda" 或 "cpu")
            use_lama: 是否使用 LaMa 修复 (否则使用 OpenCV)
        """
        if not ULTRALYTICS_AVAILABLE:
            raise ImportError("ultralytics not installed. Install: pip install ultralytics")

        self.model_path = model_path or self.DEFAULT_MODEL_ID
        self.device = device
        self.use_lama = use_lama and LAMA_AVAILABLE

        self.yolo = None
        self.lama = None

        logger.info("🎨 Watermark Remover Initialized")
        logger.info(f"   Model: {self.model_path}")
        logger.info(f"   Device: {self.device}")
        logger.info(f"   Inpainter: {'LaMa' if self.use_lama else 'OpenCV'}")

    def _download_model_from_hf(self) -> str:
        """从 HuggingFace 下载模型"""
        try:
            from huggingface_hub import hf_hub_download
        except ImportError:
            raise ImportError("huggingface_hub not installed. Install: pip install huggingface-hub")

        cache_dir = Path.home() / ".cache" / "watermark_models"
        cache_dir.mkdir(parents=True, exist_ok=True)

        model_file = cache_dir / "yolo11x_watermark.pt"

        if model_file.exists():
            return str(model_file)

        logger.info("📥 Downloading model from HuggingFace...")
        logger.info(f"   Repository: {self.model_path}")

        try:
            downloaded_path = hf_hub_download(repo_id=self.model_path, filename="best.pt", cache_dir=str(cache_dir))

            import shutil

            shutil.copy(downloaded_path, model_file)

            logger.info(f"✅ Model downloaded: {model_file}")
            return str(model_file)

        except Exception as e:
            logger.error(f"❌ Failed to download model: {e}")
            raise

    def _load_yolo(self):
        """加载 YOLO 模型"""
        if self.yolo is not None:
            return self.yolo

        logger.info("📥 Loading YOLO model...")

        # 判断是本地文件还是 HuggingFace ID
        model_path = Path(self.model_path)
        if model_path.exists():
            # 本地文件
            model_file = str(model_path)
        elif "/" in self.model_path:
            # HuggingFace ID
            model_file = self._download_model_from_hf()
        else:
            raise ValueError(f"Invalid model path: {self.model_path}")

        self.yolo = YOLO(model_file)
        logger.info("✅ YOLO loaded")
        return self.yolo

    def _load_lama(self):
        """加载 LaMa 模型"""
        if not self.use_lama or self.lama is not None:
            return self.lama

        logger.info("📥 Loading LaMa...")

        try:
            self.lama = SimpleLama()
            logger.info("✅ LaMa loaded")
        except Exception as e:
            logger.warning(f"Failed to load LaMa: {e}")
            logger.warning("Falling back to OpenCV")
            self.use_lama = False

        return self.lama

    def detect_watermark(
        self, image_path: Union[str, Path], conf_threshold: float = 0.35, save_detection_viz: Optional[Path] = None
    ) -> List[Tuple[int, int, int, int, float]]:
        """
        检测水印位置

        Args:
            image_path: 输入图像路径
            conf_threshold: 置信度阈值 (推荐 0.3-0.4)
            save_detection_viz: 保存检测可视化结果的路径（可选）

        Returns:
            [(x1, y1, x2, y2, confidence), ...]
        """
        yolo = self._load_yolo()

        results = yolo(str(image_path), conf=conf_threshold, device=self.device, verbose=False)

        boxes = []
        if len(results) > 0 and results[0].boxes is not None:
            for box in results[0].boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                conf = box.conf[0].cpu().numpy()
                boxes.append((int(x1), int(y1), int(x2), int(y2), float(conf)))

            # 保存检测可视化结果
            if save_detection_viz and boxes:
                import cv2

                # 读取图像
                img = cv2.imread(str(image_path))
                img_viz = img.copy()

                # 绘制检测框
                for x1, y1, x2, y2, conf in boxes:
                    # 绘制矩形框（绿色）
                    cv2.rectangle(img_viz, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    # 添加置信度标签
                    label = f"Watermark {conf:.2f}"
                    cv2.putText(img_viz, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                # 保存
                cv2.imwrite(str(save_detection_viz), img_viz)
                logger.info(f"🔍 Detection visualization saved: {save_detection_viz}")

        return boxes

    def create_mask(
        self, image_shape: Tuple[int, int], boxes: List[Tuple[int, int, int, int, float]], dilation: int = 10
    ) -> np.ndarray:
        """
        从边界框创建掩码

        Args:
            image_shape: (height, width)
            boxes: 边界框列表
            dilation: 膨胀大小

        Returns:
            掩码 (0=保留, 255=移除)
        """
        height, width = image_shape[:2]
        mask = np.zeros((height, width), dtype=np.uint8)

        for box in boxes:
            x1, y1, x2, y2 = box[:4]
            mask[y1:y2, x1:x2] = 255

        if dilation > 0:
            kernel = np.ones((dilation, dilation), np.uint8)
            mask = cv2.dilate(mask, kernel, iterations=1)

        return mask

    def inpaint(self, image: Image.Image, mask: np.ndarray) -> Image.Image:
        """
        修复图像

        Args:
            image: PIL Image
            mask: 掩码

        Returns:
            修复后的图像
        """
        if self.use_lama:
            lama = self._load_lama()
            if lama:
                mask_pil = Image.fromarray(mask)
                return lama(image, mask_pil)

        # 使用 OpenCV
        image_array = np.array(image)
        result_array = cv2.inpaint(image_array, mask, inpaintRadius=3, flags=cv2.INPAINT_TELEA)
        return Image.fromarray(result_array)

    def remove_watermark(
        self,
        image_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        conf_threshold: float = 0.35,
        dilation: int = 10,
        save_debug_images: bool = True,
    ) -> Path:
        """
        去除水印

        Args:
            image_path: 输入图像路径
            output_path: 输出路径 (可选)
            conf_threshold: YOLO 置信度阈值
            dilation: 掩码膨胀大小
            save_debug_images: 是否保存调试图片（检测可视化、掩码等）

        Returns:
            输出文件路径
        """
        image_path = Path(image_path)

        if output_path is None:
            output_path = image_path.parent / f"{image_path.stem}_clean{image_path.suffix}"
        else:
            output_path = Path(output_path)

        output_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Processing: {image_path.name}")

        # 加载图像
        image = Image.open(image_path).convert("RGB")

        # 检测水印（保存检测可视化）
        detection_viz_path = None
        if save_debug_images:
            detection_viz_path = output_path.parent / f"detection_{output_path.name}"

        boxes = self.detect_watermark(image_path, conf_threshold, detection_viz_path)

        if not boxes:
            logger.info("  No watermark detected, copying original")
            # 复制而不是移动
            import shutil

            shutil.copy2(image_path, output_path)
            return output_path

        logger.info(f"  Detected {len(boxes)} watermark(s)")

        # 创建掩码
        mask = self.create_mask((image.size[1], image.size[0]), boxes, dilation)

        # 保存掩码（调试用）
        if save_debug_images:
            mask_path = output_path.parent / f"mask_{output_path.name}"
            Image.fromarray(mask).save(mask_path)
            logger.info(f"🎭 Mask saved: {mask_path}")

        # 修复
        result = self.inpaint(image, mask)

        # 保存最终结果
        result.save(output_path)
        logger.info("💾 Saving cleaned image...")
        logger.info(f"   📁 Path: {output_path}")
        logger.info(f"   📊 Size: {result.size[0]}x{result.size[1]} pixels")

        return output_path

    def cleanup(self):
        """清理资源"""
        if self.yolo is not None:
            del self.yolo
            self.yolo = None

        if self.lama is not None:
            del self.lama
            self.lama = None

        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
