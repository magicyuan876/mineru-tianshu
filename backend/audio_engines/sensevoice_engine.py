"""
SenseVoice 语音识别引擎
基于阿里达摩院的 SenseVoiceSmall 模型
支持：
- 多语言识别（中文、英文、日文、韩文等）
- 说话人识别（Speaker Diarization）
- 情感识别
- 时间戳对齐
"""
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from threading import Lock
from loguru import logger


class SenseVoiceEngine:
    """
    SenseVoice 语音识别引擎（单例模式）
    
    特性：
    - 基于 FunASR 框架
    - 支持多语言自动识别
    - 支持说话人分离
    - GPU 加速
    """
    
    _instance: Optional['SenseVoiceEngine'] = None
    _lock = Lock()
    _model = None
    _initialized = False
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, model_dir: str = "iic/SenseVoiceSmall", cache_dir: Optional[str] = None):
        """
        初始化 SenseVoice 引擎（只执行一次）
        
        Args:
            model_dir: 模型路径或ModelScope模型ID
            cache_dir: 模型缓存目录
        """
        if self._initialized:
            return
        
        with self._lock:
            if self._initialized:
                return
            
            self.model_dir = model_dir
            
            # 默认缓存目录：项目根目录/models/sensevoice
            if cache_dir is None:
                project_root = Path(__file__).parent.parent.parent
                self.cache_dir = str(project_root / 'models' / 'sensevoice')
            else:
                self.cache_dir = cache_dir
            
            # 确保缓存目录存在
            Path(self.cache_dir).mkdir(parents=True, exist_ok=True)
            
            self._initialized = True
            
            logger.info(f"🔧 SenseVoice Engine initialized")
            logger.info(f"   Model: {self.model_dir}")
            logger.info(f"   Cache: {self.cache_dir}")
    
    def _load_model(self):
        """延迟加载模型"""
        if self._model is not None:
            return self._model
        
        with self._lock:
            if self._model is not None:
                return self._model
            
            logger.info("=" * 60)
            logger.info("📥 Loading SenseVoice Model...")
            logger.info("=" * 60)
            
            try:
                from funasr import AutoModel
                
                logger.info(f"🤖 Loading model from: {self.model_dir}")
                
                # 加载 SenseVoice 模型
                self._model = AutoModel(
                    model=self.model_dir,
                    trust_remote_code=True,
                    remote_code="./model.py",
                    vad_model="fsmn-vad",  # 语音活动检测
                    vad_kwargs={"max_single_segment_time": 30000},  # 最大单段时长30秒
                    device="cuda:0",  # 使用GPU
                )
                
                logger.info("=" * 60)
                logger.info("✅ SenseVoice Model loaded successfully!")
                logger.info("   Features:")
                logger.info("   - Multi-language ASR (zh/en/ja/ko/yue)")
                logger.info("   - Emotion Recognition")
                logger.info("   - Speaker Diarization")
                logger.info("   - Timestamp Alignment")
                logger.info("=" * 60)
                
                return self._model
                
            except Exception as e:
                logger.error("=" * 80)
                logger.error(f"❌ 模型加载失败:")
                logger.error(f"   错误类型: {type(e).__name__}")
                logger.error(f"   错误信息: {e}")
                logger.error("")
                logger.error("💡 排查建议:")
                logger.error("   1. 安装 FunASR:")
                logger.error("      pip install funasr")
                logger.error("   2. 检查网络连接（首次使用需要下载模型）")
                logger.error("   3. 检查 GPU 可用性")
                logger.error("   4. 模型会自动从 ModelScope 下载")
                logger.error("=" * 80)
                
                import traceback
                logger.debug("完整堆栈跟踪:")
                logger.debug(traceback.format_exc())
                
                raise
    
    def parse(
        self,
        audio_path: str,
        output_path: str,
        language: str = "auto",
        use_itn: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        语音识别
        
        Args:
            audio_path: 音频文件路径
            output_path: 输出目录
            language: 语言代码 (auto/zh/en/ja/ko/yue)
            use_itn: 是否使用逆文本归一化（数字、日期等）
            **kwargs: 其他参数
            
        Returns:
            解析结果（JSON格式，包含说话人信息）
        """
        audio_path = Path(audio_path)
        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"🎙️  SenseVoice processing: {audio_path.name}")
        logger.info(f"   Language: {language}")
        
        # 加载模型
        model = self._load_model()
        
        # 执行推理
        try:
            logger.info(f"🚀 开始语音识别...")
            
            # FunASR 推理
            # language参数映射: auto, zh, en, ja, ko, yue, nospeech
            result = model.generate(
                input=str(audio_path),
                cache={},
                language=language,
                use_itn=use_itn,
                batch_size=60,
                merge_vad=True,  # 合并VAD结果
                merge_length_s=15,  # 合并长度
            )
            
            logger.info(f"✅ SenseVoice completed")
            
            # 解析结果
            parsed_result = self._parse_result(result, audio_path)
            
            # 生成 Markdown
            markdown_content = self._generate_markdown(parsed_result)
            
            # 保存为统一的 content.md（主结果）
            content_md_file = output_path / "content.md"
            content_md_file.write_text(markdown_content, encoding='utf-8')
            logger.info(f"📄 Main result saved: content.md")
            
            # 同时保留原始命名的文件（用于调试/备份）
            original_md_file = output_path / f"{audio_path.stem}.md"
            original_md_file.write_text(markdown_content, encoding='utf-8')
            logger.info(f"📄 Backup saved: {original_md_file.name}")
            
            # 保存为统一的 content.json（主结果）
            content_json_file = output_path / "content.json"
            with open(content_json_file, 'w', encoding='utf-8') as f:
                json.dump(parsed_result, f, ensure_ascii=False, indent=2)
            logger.info(f"📄 Main JSON saved: content.json")
            
            # 同时保留原始命名的文件（用于调试/备份）
            original_json_file = output_path / f"{audio_path.stem}.json"
            with open(original_json_file, 'w', encoding='utf-8') as f:
                json.dump(parsed_result, f, ensure_ascii=False, indent=2)
            logger.info(f"📄 Backup JSON saved: {original_json_file.name}")
            
            return {
                'success': True,
                'output_path': str(output_path),
                'markdown': markdown_content,
                'markdown_file': str(content_md_file),
                'json_file': str(content_json_file),
                'json_data': parsed_result,
                'result': result  # 原始结果
            }
            
        except Exception as e:
            logger.error("=" * 80)
            logger.error(f"❌ 语音识别失败:")
            logger.error(f"   错误类型: {type(e).__name__}")
            logger.error(f"   错误信息: {e}")
            logger.error("=" * 80)
            
            import traceback
            logger.debug("完整堆栈跟踪:")
            logger.debug(traceback.format_exc())
            
            raise
    
    def _parse_result(self, result: List[Dict], audio_path: Path) -> Dict[str, Any]:
        """
        解析 FunASR 返回的结果为标准格式
        
        Args:
            result: FunASR 返回的结果列表
            audio_path: 音频文件路径
            
        Returns:
            标准化的 JSON 结果
        """
        if not result or len(result) == 0:
            logger.warning("⚠️  识别结果为空")
            return {
                "version": "1.0",
                "type": "audio",
                "source": {
                    "filename": audio_path.name,
                    "file_type": "audio"
                },
                "content": {
                    "text": "",
                    "segments": []
                }
            }
        
        # FunASR 返回的是列表，通常只有一个元素
        res = result[0]
        
        # 提取文本（使用后处理的文本）
        full_text = res.get("text", "")
        
        # 提取分段信息
        segments = []
        
        # 从 text 字段解析（SenseVoice 输出格式）
        # 格式示例：<|zh|><|NEUTRAL|><|Speech|><|woitn|>实际文本内容
        raw_segments = res.get("text_segments", [])
        
        if raw_segments:
            # 有详细的分段信息
            for idx, seg in enumerate(raw_segments):
                segment = {
                    "id": idx,
                    "text": seg.get("text", ""),
                    "start": seg.get("start", 0.0) / 1000,  # 转为秒
                    "end": seg.get("end", 0.0) / 1000,
                    "speaker": seg.get("speaker", "SPEAKER_00"),  # 说话人
                    "emotion": seg.get("emotion", "NEUTRAL"),  # 情感
                    "language": seg.get("language", "zh"),  # 语言
                }
                segments.append(segment)
        else:
            # 简单模式：只有完整文本
            # 尝试解析标签
            language, emotion, event = self._parse_tags(full_text)
            
            segments.append({
                "id": 0,
                "text": full_text,
                "start": 0.0,
                "end": 0.0,
                "speaker": "SPEAKER_00",
                "emotion": emotion,
                "language": language,
                "event": event
            })
        
        # 检测语言
        detected_language = self._detect_language(full_text)
        
        # 统计信息
        total_duration = segments[-1]["end"] if segments and segments[-1]["end"] > 0 else 0
        speakers = list(set(seg["speaker"] for seg in segments))
        
        return {
            "version": "1.0",
            "type": "audio",
            "source": {
                "filename": audio_path.name,
                "file_type": audio_path.suffix[1:],
                "duration": total_duration,
            },
            "metadata": {
                "language": detected_language,
                "speakers": speakers,
                "speaker_count": len(speakers),
                "segment_count": len(segments)
            },
            "content": {
                "text": full_text,
                "segments": segments
            }
        }
    
    def _parse_tags(self, text: str) -> tuple:
        """
        解析 SenseVoice 输出的标签
        格式：<|zh|><|NEUTRAL|><|Speech|>实际内容
        
        Returns:
            (language, emotion, event)
        """
        import re
        
        language = "zh"
        emotion = "NEUTRAL"
        event = "Speech"
        
        # 匹配语言标签
        lang_match = re.search(r'<\|(zh|en|ja|ko|yue|nospeech)\|>', text)
        if lang_match:
            language = lang_match.group(1)
        
        # 匹配情感标签
        emotion_match = re.search(r'<\|(NEUTRAL|HAPPY|ANGRY|SAD)\|>', text)
        if emotion_match:
            emotion = emotion_match.group(1)
        
        # 匹配事件标签
        event_match = re.search(r'<\|(Speech|Applause|BGM|Laugh)\|>', text)
        if event_match:
            event = event_match.group(1)
        
        return language, emotion, event
    
    def _detect_language(self, text: str) -> str:
        """智能语言检测"""
        import re
        
        # 1. 首先尝试从标签中提取语言信息
        lang_match = re.search(r'<\|(zh|en|ja|ko|yue)\|>', text)
        if lang_match:
            return lang_match.group(1)
        
        # 2. 移除所有标签后进行内容检测
        clean_text = re.sub(r'<\|[^|]+\|>', '', text).strip()
        
        if not clean_text:
            return "unknown"
        
        # 3. 统计各种字符
        total_chars = len(clean_text)
        chinese_chars = sum(1 for c in clean_text if '\u4e00' <= c <= '\u9fff')
        japanese_chars = sum(1 for c in clean_text if '\u3040' <= c <= '\u309f' or '\u30a0' <= c <= '\u30ff')
        korean_chars = sum(1 for c in clean_text if '\uac00' <= c <= '\ud7af')
        
        # 4. 根据字符比例判断
        if chinese_chars / total_chars > 0.2:
            return "zh"
        elif japanese_chars / total_chars > 0.1:
            return "ja"
        elif korean_chars / total_chars > 0.1:
            return "ko"
        elif all(ord(c) < 128 or c.isspace() for c in clean_text if c.isalnum() or c.isspace()):
            # 全是ASCII字符
            return "en"
        
        return "auto"
    
    def _emotion_to_emoji(self, emotion: str) -> str:
        """
        将情感标签转换为 emoji
        
        Args:
            emotion: 情感标签 (NEUTRAL/HAPPY/ANGRY/SAD)
            
        Returns:
            对应的 emoji 字符
        """
        emotion_map = {
            'NEUTRAL': '😐',
            'HAPPY': '😊',
            'ANGRY': '😠',
            'SAD': '😢',
        }
        return emotion_map.get(emotion.upper(), '')
    
    def _event_to_emoji(self, event: str) -> str:
        """
        将事件标签转换为 emoji
        
        Args:
            event: 事件标签 (Speech/Applause/BGM/Laugh)
            
        Returns:
            对应的 emoji 字符
        """
        event_map = {
            'Speech': '💬',
            'Applause': '👏',
            'BGM': '🎵',
            'Laugh': '😄',
        }
        return event_map.get(event, '💬')
    
    def _clean_text_tags(self, text: str) -> str:
        """
        清理文本中的标签，替换为 emoji
        
        Args:
            text: 原始文本（包含标签）
            
        Returns:
            清理后的文本（标签替换为 emoji）
        """
        import re
        
        # 语言标签 - 直接移除（已在元数据中显示）
        text = re.sub(r'<\|(zh|en|ja|ko|yue|nospeech)\|>', '', text)
        
        # 情感标签 - 替换为 emoji
        def replace_emotion(match):
            emotion = match.group(1)
            emoji = self._emotion_to_emoji(emotion)
            return emoji if emoji else ''
        text = re.sub(r'<\|(NEUTRAL|HAPPY|ANGRY|SAD)\|>', replace_emotion, text)
        
        # 事件标签 - 替换为 emoji
        def replace_event(match):
            event = match.group(1)
            emoji = self._event_to_emoji(event)
            return emoji if emoji else ''
        text = re.sub(r'<\|(Speech|Applause|BGM|Laugh)\|>', replace_event, text)
        
        # 其他标签 - 直接移除
        text = re.sub(r'<\|[^|]+\|>', '', text)
        
        # 清理多余空格
        text = ' '.join(text.split())
        
        return text.strip()
    
    def _generate_markdown(self, parsed_result: Dict[str, Any]) -> str:
        """
        生成 Markdown 格式的转写文本
        
        Args:
            parsed_result: 解析后的结果
            
        Returns:
            Markdown 格式的文本
        """
        lines = []
        
        # 标题
        lines.append(f"# 语音转写：{parsed_result['source']['filename']}\n")
        
        # 元信息
        metadata = parsed_result['metadata']
        lang_map = {'zh': '🇨🇳 中文', 'en': '🇺🇸 英文', 'ja': '🇯🇵 日文', 'ko': '🇰🇷 韩文', 'yue': '🇭🇰 粤语'}
        lang_display = lang_map.get(metadata['language'], metadata['language'])
        
        lines.append(f"**语言**: {lang_display}")
        lines.append(f"**说话人数**: {metadata['speaker_count']}")
        if metadata.get('speakers'):
            lines.append(f"**说话人**: {', '.join(metadata['speakers'])}")
        lines.append("")
        
        # 完整文本（清理标签）
        lines.append("## 完整文本\n")
        clean_text = self._clean_text_tags(parsed_result['content']['text'])
        lines.append(clean_text)
        lines.append("")
        
        # 分段文本（始终显示，因为包含情感和事件信息）
        segments = parsed_result['content']['segments']
        if segments:
            lines.append("## 分段转写\n")
            
            current_speaker = None
            for seg in segments:
                speaker = seg.get('speaker', 'SPEAKER_00')
                start_time = seg.get('start', 0)
                text = seg.get('text', '')
                emotion = seg.get('emotion', '')
                event = seg.get('event', '')
                
                # 清理文本标签
                clean_seg_text = self._clean_text_tags(text)
                
                # 如果说话人变化，添加分隔
                if speaker != current_speaker:
                    current_speaker = speaker
                    lines.append(f"\n**{speaker}**:\n")
                
                # 时间戳格式化
                timestamp = self._format_timestamp(start_time)
                
                # 添加情感 emoji（如果不是 NEUTRAL）
                emotion_emoji = self._emotion_to_emoji(emotion) if emotion and emotion != "NEUTRAL" else ""
                emotion_tag = f" {emotion_emoji}" if emotion_emoji else ""
                
                # 添加事件 emoji
                event_emoji = self._event_to_emoji(event) if event else ""
                event_tag = f" {event_emoji}" if event_emoji and event != "Speech" else ""
                
                lines.append(f"[{timestamp}]{emotion_tag}{event_tag} {clean_seg_text}")
        
        return '\n'.join(lines)
    
    def _format_timestamp(self, seconds: float) -> str:
        """
        格式化时间戳
        
        Args:
            seconds: 秒数
            
        Returns:
            格式化的时间字符串 (HH:MM:SS)
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"


# 全局单例
_engine = None

def get_engine() -> SenseVoiceEngine:
    """获取全局引擎实例"""
    global _engine
    if _engine is None:
        _engine = SenseVoiceEngine()
    return _engine

