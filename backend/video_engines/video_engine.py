"""
视频处理引擎
基于 FFmpeg + SenseVoice

支持：
- 多种视频格式（MP4, AVI, MKV, MOV, FLV, WebM）
- 音频提取
- 语音转写（多语言、说话人识别、情感识别）
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional
from threading import Lock
from loguru import logger
import subprocess
import tempfile


class VideoProcessingEngine:
    """
    视频处理引擎（单例模式）
    
    特性：
    - 基于 FFmpeg 提取音频
    - 复用 SenseVoice 进行语音识别
    - 支持多种视频格式
    """
    
    _instance: Optional['VideoProcessingEngine'] = None
    _lock = Lock()
    _audio_engine = None
    _initialized = False
    
    # 支持的视频格式
    SUPPORTED_FORMATS = ['.mp4', '.avi', '.mkv', '.mov', '.flv', '.webm', '.m4v', '.wmv', '.mpeg', '.mpg']
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """
        初始化视频处理引擎（只执行一次）
        """
        if self._initialized:
            return
        
        with self._lock:
            if self._initialized:
                return
            
            self._initialized = True
            
            logger.info(f"🔧 Video Processing Engine initialized")
            logger.info(f"   Supported formats: {', '.join(self.SUPPORTED_FORMATS)}")
    
    def _load_audio_engine(self):
        """延迟加载音频处理引擎"""
        if self._audio_engine is not None:
            return self._audio_engine
        
        with self._lock:
            if self._audio_engine is not None:
                return self._audio_engine
            
            logger.info("📥 Loading audio engine (SenseVoice)...")
            
            try:
                # 导入 SenseVoice 引擎
                # 在同一个 backend 目录下，直接导入同级模块
                from audio_engines.sensevoice_engine import get_engine
                
                self._audio_engine = get_engine()
                
                logger.info("✅ Audio engine loaded successfully")
                
                return self._audio_engine
                
            except Exception as e:
                logger.error("=" * 80)
                logger.error(f"❌ 音频引擎加载失败:")
                logger.error(f"   错误类型: {type(e).__name__}")
                logger.error(f"   错误信息: {e}")
                logger.error("")
                logger.error("💡 排查建议:")
                logger.error("   1. 确保已安装音频处理依赖:")
                logger.error("      pip install funasr ffmpeg-python")
                logger.error("   2. 检查 SenseVoice 引擎是否正常")
                logger.error("=" * 80)
                
                import traceback
                logger.debug("完整堆栈跟踪:")
                logger.debug(traceback.format_exc())
                
                raise
    
    def extract_audio(self, video_path: str, output_path: str = None, audio_format: str = 'wav') -> str:
        """
        使用 FFmpeg 从视频中提取音频
        
        Args:
            video_path: 视频文件路径
            output_path: 输出音频文件路径（可选，默认为临时文件）
            audio_format: 音频格式（wav/mp3/aac）
            
        Returns:
            提取的音频文件路径
        """
        video_path = Path(video_path)
        
        if not video_path.exists():
            raise FileNotFoundError(f"视频文件不存在: {video_path}")
        
        # 检查视频格式
        if video_path.suffix.lower() not in self.SUPPORTED_FORMATS:
            raise ValueError(f"不支持的视频格式: {video_path.suffix}")
        
        # 确定输出路径
        if output_path is None:
            # 创建临时文件
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f'.{audio_format}')
            output_path = temp_file.name
            temp_file.close()
        
        output_path = Path(output_path)
        
        logger.info(f"🎬 Extracting audio from video: {video_path.name}")
        logger.info(f"   Output format: {audio_format}")
        
        try:
            # 使用 ffmpeg 提取音频
            # -vn: 不处理视频流
            # -acodec pcm_s16le: 使用 PCM 16位编码（适合语音识别）
            # -ar 16000: 采样率 16kHz（SenseVoice 推荐）
            # -ac 1: 单声道
            
            if audio_format == 'wav':
                # WAV 格式（最适合语音识别）
                cmd = [
                    'ffmpeg',
                    '-i', str(video_path),
                    '-vn',  # 不处理视频
                    '-acodec', 'pcm_s16le',  # PCM 16位
                    '-ar', '16000',  # 采样率 16kHz
                    '-ac', '1',  # 单声道
                    '-y',  # 覆盖输出文件
                    str(output_path)
                ]
            elif audio_format == 'mp3':
                # MP3 格式
                cmd = [
                    'ffmpeg',
                    '-i', str(video_path),
                    '-vn',
                    '-acodec', 'libmp3lame',
                    '-ar', '16000',
                    '-ac', '1',
                    '-y',
                    str(output_path)
                ]
            else:
                # 默认使用原始音频编码
                cmd = [
                    'ffmpeg',
                    '-i', str(video_path),
                    '-vn',
                    '-acodec', 'copy',
                    '-y',
                    str(output_path)
                ]
            
            # 执行 ffmpeg 命令
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            if result.returncode != 0:
                logger.error(f"❌ FFmpeg 执行失败:")
                logger.error(f"   返回码: {result.returncode}")
                logger.error(f"   错误信息: {result.stderr}")
                raise RuntimeError(f"FFmpeg failed with return code {result.returncode}")
            
            # 检查输出文件
            if not output_path.exists() or output_path.stat().st_size == 0:
                raise RuntimeError("音频提取失败：输出文件为空")
            
            file_size_mb = output_path.stat().st_size / (1024 * 1024)
            logger.info(f"✅ Audio extracted successfully")
            logger.info(f"   Output: {output_path.name}")
            logger.info(f"   Size: {file_size_mb:.2f} MB")
            
            return str(output_path)
            
        except FileNotFoundError:
            logger.error("=" * 80)
            logger.error("❌ FFmpeg 未安装或未在 PATH 中")
            logger.error("")
            logger.error("💡 安装方法:")
            logger.error("   Windows:")
            logger.error("     1. 下载 FFmpeg: https://ffmpeg.org/download.html")
            logger.error("     2. 解压并添加到 PATH")
            logger.error("     或使用: choco install ffmpeg")
            logger.error("")
            logger.error("   Linux:")
            logger.error("     sudo apt-get install ffmpeg")
            logger.error("")
            logger.error("   macOS:")
            logger.error("     brew install ffmpeg")
            logger.error("=" * 80)
            raise
        except Exception as e:
            logger.error(f"❌ 音频提取失败: {e}")
            import traceback
            logger.debug("完整堆栈跟踪:")
            logger.debug(traceback.format_exc())
            raise
    
    def parse(
        self,
        video_path: str,
        output_path: str,
        language: str = "auto",
        use_itn: bool = True,
        keep_audio: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        视频处理主流程：提取音频 + 语音识别
        
        Args:
            video_path: 视频文件路径
            output_path: 输出目录
            language: 语言代码 (auto/zh/en/ja/ko/yue)
            use_itn: 是否使用逆文本归一化
            keep_audio: 是否保留提取的音频文件
            **kwargs: 其他参数
            
        Returns:
            解析结果（JSON格式）
        """
        video_path = Path(video_path)
        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"🎬 Video processing: {video_path.name}")
        logger.info(f"   Language: {language}")
        
        try:
            # 步骤 1: 提取音频
            logger.info("=" * 60)
            logger.info("📥 Step 1: Extracting audio from video...")
            logger.info("=" * 60)
            
            audio_path = self.extract_audio(
                video_path=str(video_path),
                audio_format='wav'
            )
            
            # 步骤 2: 音频转文字
            logger.info("=" * 60)
            logger.info("📝 Step 2: Transcribing audio...")
            logger.info("=" * 60)
            
            audio_engine = self._load_audio_engine()
            
            # 使用 SenseVoice 进行语音识别
            result = audio_engine.parse(
                audio_path=audio_path,
                output_path=str(output_path),
                language=language,
                use_itn=use_itn,
                **kwargs
            )
            
            # 步骤 3: 更新结果元数据
            logger.info("=" * 60)
            logger.info("📊 Step 3: Updating metadata...")
            logger.info("=" * 60)
            
            # 更新 JSON 数据，标记为视频来源
            if result.get('json_data'):
                json_data = result['json_data']
                json_data['type'] = 'video'
                json_data['source']['file_type'] = 'video'
                json_data['source']['video_format'] = video_path.suffix[1:]
                json_data['source']['original_filename'] = video_path.name
                
                # 重新保存 JSON
                json_file = output_path / f"{video_path.stem}.json"
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, ensure_ascii=False, indent=2)
                logger.info(f"📄 Updated JSON: {json_file}")
            
            # 更新 Markdown，添加视频信息
            if result.get('markdown'):
                md_content = result['markdown']
                
                # 在标题后添加视频信息
                video_info = f"\n**原始文件**: {video_path.name} (视频)\n**视频格式**: {video_path.suffix[1:].upper()}\n"
                
                # 查找第一个 \n\n 位置，插入视频信息
                first_break = md_content.find('\n\n')
                if first_break != -1:
                    md_content = md_content[:first_break] + video_info + md_content[first_break:]
                else:
                    md_content = video_info + md_content
                
                # 重新保存 Markdown
                markdown_file = output_path / f"{video_path.stem}.md"
                markdown_file.write_text(md_content, encoding='utf-8')
                logger.info(f"📄 Updated Markdown: {markdown_file}")
                
                result['markdown'] = md_content
            
            # 步骤 4: 清理临时音频文件（可选）
            if not keep_audio:
                try:
                    Path(audio_path).unlink()
                    logger.info(f"🗑️  Temporary audio file deleted: {Path(audio_path).name}")
                except:
                    pass
            else:
                logger.info(f"💾 Audio file kept: {audio_path}")
            
            logger.info("=" * 60)
            logger.info("✅ Video processing completed successfully!")
            logger.info("=" * 60)
            
            return result
            
        except Exception as e:
            logger.error("=" * 80)
            logger.error(f"❌ 视频处理失败:")
            logger.error(f"   错误类型: {type(e).__name__}")
            logger.error(f"   错误信息: {e}")
            logger.error("=" * 80)
            
            import traceback
            logger.debug("完整堆栈跟踪:")
            logger.debug(traceback.format_exc())
            
            raise
    
    @classmethod
    def check_ffmpeg(cls) -> bool:
        """
        检查 FFmpeg 是否可用
        
        Returns:
            True 如果 FFmpeg 可用，否则 False
        """
        try:
            result = subprocess.run(
                ['ffmpeg', '-version'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5
            )
            return result.returncode == 0
        except:
            return False
    
    @classmethod
    def get_video_info(cls, video_path: str) -> Dict[str, Any]:
        """
        获取视频信息（时长、分辨率、编码等）
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            视频信息字典
        """
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                str(video_path)
            ]
            
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                return {}
                
        except Exception as e:
            logger.warning(f"Failed to get video info: {e}")
            return {}


# 全局单例
_engine = None

def get_engine() -> VideoProcessingEngine:
    """获取全局引擎实例"""
    global _engine
    if _engine is None:
        _engine = VideoProcessingEngine()
    return _engine

