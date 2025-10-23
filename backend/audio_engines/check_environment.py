"""
SenseVoice 环境检查工具
检查 FunASR 和相关依赖是否正确安装
"""
import sys
from loguru import logger


def check_funasr():
    """检查 FunASR 是否安装"""
    try:
        import funasr
        logger.info(f"✅ FunASR installed: {funasr.__version__}")
        return True
    except ImportError:
        logger.error("❌ FunASR not installed")
        logger.error("   Install with: pip install funasr")
        return False


def check_modelscope():
    """检查 ModelScope 是否安装（可选，用于模型下载）"""
    try:
        import modelscope
        logger.info(f"✅ ModelScope installed: {modelscope.__version__}")
        return True
    except ImportError:
        logger.warning("⚠️  ModelScope not installed (optional)")
        logger.info("   Install with: pip install modelscope")
        return True  # 可选依赖


def check_torch():
    """检查 PyTorch 是否安装且支持 CUDA"""
    try:
        import torch
        logger.info(f"✅ PyTorch installed: {torch.__version__}")
        
        if torch.cuda.is_available():
            logger.info(f"✅ CUDA available")
            logger.info(f"   GPU: {torch.cuda.get_device_name(0)}")
            logger.info(f"   CUDA Version: {torch.version.cuda}")
        else:
            logger.warning("⚠️  CUDA not available")
            logger.warning("   SenseVoice will run on CPU (slow)")
        
        return True
    except ImportError:
        logger.error("❌ PyTorch not installed")
        logger.error("   Install with: pip install torch")
        return False


def check_ffmpeg():
    """检查 ffmpeg 是否安装"""
    import subprocess
    try:
        result = subprocess.run(
            ['ffmpeg', '-version'],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            logger.info(f"✅ ffmpeg installed: {version_line}")
            return True
        else:
            logger.error("❌ ffmpeg not working properly")
            return False
    except FileNotFoundError:
        logger.error("❌ ffmpeg not found")
        logger.error("   Install:")
        logger.error("   - Ubuntu: sudo apt-get install ffmpeg")
        logger.error("   - macOS: brew install ffmpeg")
        logger.error("   - Windows: https://ffmpeg.org/download.html")
        return False


def check_all():
    """检查所有依赖"""
    logger.info("=" * 60)
    logger.info("🔍 Checking SenseVoice Environment")
    logger.info("=" * 60)
    
    results = {
        'FunASR': check_funasr(),
        'PyTorch': check_torch(),
        'ffmpeg': check_ffmpeg(),
        'ModelScope': check_modelscope(),
    }
    
    logger.info("=" * 60)
    
    # 必需依赖
    required = ['FunASR', 'PyTorch', 'ffmpeg']
    missing_required = [k for k in required if not results[k]]
    
    if missing_required:
        logger.error(f"❌ Missing required dependencies: {', '.join(missing_required)}")
        logger.error("")
        logger.error("Installation guide:")
        logger.error("  pip install funasr torch ffmpeg-python")
        logger.error("  # And install system ffmpeg")
        return False
    else:
        logger.info("✅ All required dependencies are installed!")
        logger.info("")
        logger.info("Quick start:")
        logger.info("  from audio_engines import SenseVoiceEngine")
        logger.info("  engine = SenseVoiceEngine()")
        logger.info("  result = engine.parse('audio.mp3', './output')")
        return True


if __name__ == '__main__':
    success = check_all()
    sys.exit(0 if success else 1)

