"""
Video Processing Engines
视频处理引擎

支持的格式：MP4, AVI, MKV, MOV, FLV, WebM
核心功能：
- 音频提取（使用 ffmpeg）
- 语音转写（复用 SenseVoice）
"""

from .video_engine import VideoProcessingEngine, get_engine

__all__ = ['VideoProcessingEngine', 'get_engine']

