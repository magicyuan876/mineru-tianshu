"""
关键帧提取引擎
场景检测 → 质量过滤 → 图像去重 → OCR
"""
import cv2
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from loguru import logger
import imagehash
from PIL import Image
import tempfile
import shutil


class KeyFrame:
    """关键帧数据结构"""
    def __init__(self, timestamp: float, frame_number: int, image_path: str):
        self.timestamp = timestamp
        self.frame_number = frame_number
        self.image_path = image_path
        self.quality_score = 0.0
        self.phash = None
        self.ocr_result = None


class KeyframeExtractor:
    """关键帧提取器"""
    
    def __init__(
        self,
        scene_threshold: float = 30.0,
        min_scene_length: float = 1.0,
        quality_threshold: float = 100.0,
        phash_threshold: int = 5,
        brightness_range: Tuple[int, int] = (30, 225)
    ):
        self.scene_threshold = scene_threshold
        self.min_scene_length = min_scene_length
        self.quality_threshold = quality_threshold
        self.phash_threshold = phash_threshold
        self.brightness_range = brightness_range
    
    def extract(self, video_path: str, output_dir: str) -> List[KeyFrame]:
        """
        提取关键帧主流程
        """
        video_path = Path(video_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"🎬 开始提取关键帧: {video_path.name}")
        
        # Stage 1: 场景检测
        logger.info("📍 Stage 1: 场景检测...")
        scene_frames = self._detect_scenes(str(video_path))
        logger.info(f"   检测到 {len(scene_frames)} 个场景变化点")
        
        # Stage 2: 提取关键帧图像
        logger.info("🖼️  Stage 2: 提取关键帧...")
        keyframes = self._extract_frames(str(video_path), scene_frames, output_dir)
        logger.info(f"   提取了 {len(keyframes)} 帧")
        
        # Stage 3: 图像质量过滤
        logger.info("✨ Stage 3: 质量过滤...")
        quality_frames = self._filter_quality(keyframes)
        logger.info(f"   保留 {len(quality_frames)} 个高质量帧")
        
        # Stage 4: 图像去重
        logger.info("🔄 Stage 4: 图像去重...")
        unique_frames = self._deduplicate_images(quality_frames)
        logger.info(f"   去重后剩余 {len(unique_frames)} 帧")
        
        logger.info(f"✅ 关键帧提取完成: {len(unique_frames)} 帧")
        return unique_frames
    
    def _detect_scenes(self, video_path: str) -> List[Tuple[float, int]]:
        """
        场景检测：基于帧差异检测场景变化
        返回: [(timestamp, frame_number), ...]
        """
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        scene_frames = []
        prev_frame = None
        frame_count = 0
        last_scene_frame = 0
        
        min_frames = int(self.min_scene_length * fps)
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # 转换为灰度并缩小以加快计算
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            small = cv2.resize(gray, (160, 90))
            
            if prev_frame is not None:
                # 计算帧差异
                diff = cv2.absdiff(small, prev_frame)
                diff_score = np.mean(diff)
                
                # 检测场景变化
                if diff_score > self.scene_threshold:
                    # 确保最小场景长度
                    if frame_count - last_scene_frame >= min_frames:
                        timestamp = frame_count / fps
                        scene_frames.append((timestamp, frame_count))
                        last_scene_frame = frame_count
            
            prev_frame = small
            frame_count += 1
            
            # 每处理 1000 帧输出一次进度
            if frame_count % 1000 == 0:
                progress = (frame_count / total_frames) * 100
                logger.debug(f"   场景检测进度: {progress:.1f}%")
        
        cap.release()
        
        # 如果没检测到场景变化，使用固定间隔
        if len(scene_frames) == 0:
            logger.warning("   未检测到场景变化，使用固定间隔采样")
            interval = 10  # 每 10 秒
            for i in range(0, int(total_frames / fps), interval):
                scene_frames.append((float(i), int(i * fps)))
        
        return scene_frames
    
    def _extract_frames(
        self, 
        video_path: str, 
        scene_frames: List[Tuple[float, int]], 
        output_dir: Path
    ) -> List[KeyFrame]:
        """提取指定帧的图像"""
        cap = cv2.VideoCapture(video_path)
        keyframes = []
        
        for idx, (timestamp, frame_number) in enumerate(scene_frames):
            # 定位到指定帧
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ret, frame = cap.read()
            
            if not ret:
                continue
            
            # 保存图像
            image_path = output_dir / f"frame_{idx:04d}_{frame_number:06d}.jpg"
            cv2.imwrite(str(image_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
            
            keyframe = KeyFrame(timestamp, frame_number, str(image_path))
            keyframes.append(keyframe)
        
        cap.release()
        return keyframes
    
    def _filter_quality(self, keyframes: List[KeyFrame]) -> List[KeyFrame]:
        """图像质量过滤"""
        quality_frames = []
        
        for kf in keyframes:
            # 读取图像
            img = cv2.imread(kf.image_path)
            if img is None:
                continue
            
            # 评估清晰度（拉普拉斯方差）
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            # 评估亮度
            brightness = np.mean(gray)
            
            # 质量评分
            is_sharp = sharpness >= self.quality_threshold
            is_bright = self.brightness_range[0] <= brightness <= self.brightness_range[1]
            
            if is_sharp and is_bright:
                kf.quality_score = sharpness
                quality_frames.append(kf)
            else:
                # 删除低质量图像
                try:
                    Path(kf.image_path).unlink()
                except:
                    pass
        
        return quality_frames
    
    def _deduplicate_images(self, keyframes: List[KeyFrame]) -> List[KeyFrame]:
        """使用感知哈希去重"""
        if len(keyframes) == 0:
            return []
        
        unique_frames = []
        prev_hash = None
        
        for kf in keyframes:
            try:
                # 计算 pHash
                img = Image.open(kf.image_path)
                curr_hash = imagehash.phash(img)
                kf.phash = curr_hash
                
                # 与前一帧对比
                if prev_hash is None:
                    # 第一帧，保留
                    unique_frames.append(kf)
                    prev_hash = curr_hash
                else:
                    # 计算汉明距离
                    hamming_dist = curr_hash - prev_hash
                    
                    if hamming_dist > self.phash_threshold:
                        # 差异大，保留
                        unique_frames.append(kf)
                        prev_hash = curr_hash
                    else:
                        # 相似，删除
                        try:
                            Path(kf.image_path).unlink()
                        except:
                            pass
            except Exception as e:
                logger.debug(f"处理帧 {kf.image_path} 时出错: {e}")
                continue
        
        return unique_frames
    
    def cleanup(self, keyframes: List[KeyFrame]):
        """清理临时图像文件"""
        for kf in keyframes:
            try:
                if Path(kf.image_path).exists():
                    Path(kf.image_path).unlink()
            except:
                pass


class VideoOCREngine:
    """视频 OCR 引擎：关键帧提取 + OCR 识别"""
    
    def __init__(
        self,
        ocr_backend: str = "paddleocr-vl",
        keep_keyframes: bool = False
    ):
        self.ocr_backend = ocr_backend
        self.keep_keyframes = keep_keyframes
        self.keyframe_extractor = KeyframeExtractor()
        self._ocr_engine = None
    
    def _load_ocr_engine(self):
        """加载 OCR 引擎"""
        if self._ocr_engine is not None:
            return self._ocr_engine
        
        if self.ocr_backend == "paddleocr-vl":
            from paddleocr_vl import PaddleOCRVLEngine
            self._ocr_engine = PaddleOCRVLEngine()
        elif self.ocr_backend == "deepseek-ocr":
            from deepseek_ocr import DeepSeekOCREngine
            self._ocr_engine = DeepSeekOCREngine()
        else:
            raise ValueError(f"不支持的 OCR 引擎: {self.ocr_backend}")
        
        return self._ocr_engine
    
    def process(
        self, 
        video_path: str, 
        output_path: str
    ) -> Dict[str, Any]:
        """
        处理视频：提取关键帧并进行 OCR
        """
        video_path = Path(video_path)
        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 创建临时目录存放关键帧
        temp_dir = output_path / "keyframes_temp"
        temp_dir.mkdir(exist_ok=True)
        
        try:
            # Stage 1-4: 提取关键帧
            keyframes = self.keyframe_extractor.extract(str(video_path), str(temp_dir))
            
            if len(keyframes) == 0:
                logger.warning("未提取到任何关键帧")
                return {
                    'success': False,
                    'message': '未提取到关键帧',
                    'keyframes': []
                }
            
            # Stage 5: OCR 处理
            logger.info(f"📝 Stage 5: OCR 识别 ({len(keyframes)} 帧)...")
            ocr_engine = self._load_ocr_engine()
            
            results = []
            for idx, kf in enumerate(keyframes):
                logger.info(f"   处理 {idx+1}/{len(keyframes)}: {Path(kf.image_path).name}")
                
                try:
                    # 调用 OCR 引擎
                    ocr_result = ocr_engine.parse(
                        file_path=kf.image_path,
                        output_path=str(temp_dir)
                    )
                    
                    # 提取文字内容
                    ocr_text = ""
                    if ocr_result.get('markdown'):
                        ocr_text = ocr_result['markdown']
                    elif ocr_result.get('json_data'):
                        # 从 JSON 提取文字
                        json_data = ocr_result['json_data']
                        if 'content' in json_data and 'text' in json_data['content']:
                            ocr_text = json_data['content']['text']
                    
                    kf.ocr_result = ocr_text
                    
                    results.append({
                        'timestamp': kf.timestamp,
                        'frame_number': kf.frame_number,
                        'image_path': kf.image_path,
                        'ocr_text': ocr_text
                    })
                    
                except Exception as e:
                    logger.warning(f"   OCR 失败: {e}")
                    results.append({
                        'timestamp': kf.timestamp,
                        'frame_number': kf.frame_number,
                        'image_path': kf.image_path,
                        'ocr_text': '',
                        'error': str(e)
                    })
            
            # Stage 6: 文本去重
            logger.info("🔄 Stage 6: 文本去重...")
            unique_results = self._deduplicate_text(results)
            logger.info(f"   去重后剩余 {len(unique_results)} 个结果")
            
            # 生成输出
            markdown_content = self._generate_markdown(unique_results, video_path.name)
            markdown_file = output_path / f"{video_path.stem}_keyframes.md"
            markdown_file.write_text(markdown_content, encoding='utf-8')
            
            # 保存 JSON
            import json
            json_file = output_path / f"{video_path.stem}_keyframes.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'video': video_path.name,
                    'total_keyframes': len(unique_results),
                    'keyframes': unique_results
                }, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ 视频 OCR 完成")
            logger.info(f"   Markdown: {markdown_file}")
            logger.info(f"   JSON: {json_file}")
            
            return {
                'success': True,
                'output_path': str(output_path),
                'markdown_file': str(markdown_file),
                'json_file': str(json_file),
                'markdown': markdown_content,
                'keyframes': unique_results,
                'total_keyframes': len(unique_results)
            }
            
        finally:
            # 清理临时文件
            if not self.keep_keyframes:
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass
    
    def _deduplicate_text(self, results: List[Dict]) -> List[Dict]:
        """文本去重：使用编辑距离"""
        if len(results) <= 1:
            return results
        
        from difflib import SequenceMatcher
        
        unique_results = [results[0]]
        
        for result in results[1:]:
            current_text = result['ocr_text'].strip()
            if not current_text:
                continue
            
            # 与最后一个结果对比
            last_text = unique_results[-1]['ocr_text'].strip()
            
            if not last_text:
                unique_results.append(result)
                continue
            
            # 计算相似度
            similarity = SequenceMatcher(None, current_text, last_text).ratio()
            
            if similarity < 0.9:  # 相似度低于 90%，认为不同
                unique_results.append(result)
        
        return unique_results
    
    def _generate_markdown(self, results: List[Dict], video_name: str) -> str:
        """生成 Markdown 输出"""
        lines = []
        lines.append(f"# 视频关键帧 OCR 结果: {video_name}\n")
        lines.append(f"**总帧数**: {len(results)}\n")
        lines.append("---\n")
        
        for idx, result in enumerate(results, 1):
            timestamp = result['timestamp']
            minutes = int(timestamp // 60)
            seconds = int(timestamp % 60)
            
            lines.append(f"## 关键帧 {idx} - [{minutes:02d}:{seconds:02d}]\n")
            lines.append(f"**时间戳**: {timestamp:.2f}s\n")
            
            ocr_text = result.get('ocr_text', '').strip()
            if ocr_text:
                lines.append(f"**内容**:\n\n{ocr_text}\n")
            else:
                lines.append("_未检测到文字内容_\n")
            
            lines.append("---\n")
        
        return '\n'.join(lines)

