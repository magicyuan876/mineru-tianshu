"""
视频处理环境检查脚本
检查 FFmpeg 和相关依赖是否正确安装
"""
import sys
import subprocess
from pathlib import Path
from loguru import logger

# 添加 backend 目录到路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


def check_ffmpeg():
    """检查 FFmpeg 是否安装"""
    logger.info("=" * 60)
    logger.info("🔍 检查 FFmpeg...")
    logger.info("=" * 60)
    
    try:
        result = subprocess.run(
            ['ffmpeg', '-version'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            # 提取版本信息
            version_line = result.stdout.split('\n')[0]
            logger.info(f"✅ FFmpeg 已安装: {version_line}")
            return True
        else:
            logger.error("❌ FFmpeg 命令执行失败")
            return False
            
    except FileNotFoundError:
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
        return False
    except Exception as e:
        logger.error(f"❌ 检查 FFmpeg 时出错: {e}")
        return False


def check_ffprobe():
    """检查 FFprobe 是否安装"""
    logger.info("")
    logger.info("=" * 60)
    logger.info("🔍 检查 FFprobe...")
    logger.info("=" * 60)
    
    try:
        result = subprocess.run(
            ['ffprobe', '-version'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            logger.info(f"✅ FFprobe 已安装: {version_line}")
            return True
        else:
            logger.error("❌ FFprobe 命令执行失败")
            return False
            
    except FileNotFoundError:
        logger.error("❌ FFprobe 未安装（通常随 FFmpeg 一起安装）")
        return False
    except Exception as e:
        logger.error(f"❌ 检查 FFprobe 时出错: {e}")
        return False


def check_audio_engine():
    """检查音频处理引擎是否可用"""
    logger.info("")
    logger.info("=" * 60)
    logger.info("🔍 检查音频处理引擎 (SenseVoice)...")
    logger.info("=" * 60)
    
    try:
        # 尝试导入 SenseVoice 引擎
        from audio_engines.sensevoice_engine import SenseVoiceEngine
        
        logger.info("✅ SenseVoice 引擎模块导入成功")
        
        # 检查 FunASR
        try:
            import funasr
            logger.info(f"✅ FunASR 已安装: {funasr.__version__}")
        except ImportError:
            logger.error("❌ FunASR 未安装")
            logger.error("   安装命令: pip install funasr")
            return False
        
        return True
        
    except ImportError as e:
        logger.error(f"❌ 音频处理引擎导入失败: {e}")
        logger.error("   请确保已正确安装音频处理依赖")
        return False
    except Exception as e:
        logger.error(f"❌ 检查音频引擎时出错: {e}")
        return False


def check_video_engine():
    """检查视频处理引擎是否可用"""
    logger.info("")
    logger.info("=" * 60)
    logger.info("🔍 检查视频处理引擎...")
    logger.info("=" * 60)
    
    try:
        from backend.video_engines.video_engine import VideoProcessingEngine
        
        engine = VideoProcessingEngine()
        logger.info("✅ 视频处理引擎初始化成功")
        logger.info(f"   支持的格式: {', '.join(engine.SUPPORTED_FORMATS)}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 视频处理引擎初始化失败: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return False


def main():
    """运行所有检查"""
    logger.info("")
    logger.info("🚀 视频处理环境检查")
    logger.info("=" * 60)
    
    results = {
        'ffmpeg': check_ffmpeg(),
        'ffprobe': check_ffprobe(),
        'audio_engine': check_audio_engine(),
        'video_engine': check_video_engine(),
    }
    
    logger.info("")
    logger.info("=" * 60)
    logger.info("📊 检查结果汇总")
    logger.info("=" * 60)
    
    all_passed = True
    for component, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        logger.info(f"   {component:20s}: {status}")
        if not passed:
            all_passed = False
    
    logger.info("=" * 60)
    
    if all_passed:
        logger.info("")
        logger.info("✅ 所有检查通过！视频处理环境已就绪")
        logger.info("")
        logger.info("💡 使用方法:")
        logger.info("   from backend.video_engines import get_engine")
        logger.info("   engine = get_engine()")
        logger.info("   result = engine.parse('video.mp4', 'output_dir')")
        logger.info("")
        return 0
    else:
        logger.error("")
        logger.error("❌ 部分检查未通过，请根据上述提示修复")
        logger.error("")
        return 1


if __name__ == '__main__':
    sys.exit(main())

