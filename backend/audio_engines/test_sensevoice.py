"""
测试 SenseVoice 引擎
"""
import sys
from pathlib import Path
from loguru import logger


def test_basic():
    """基础功能测试"""
    logger.info("=" * 60)
    logger.info("🧪 Testing SenseVoice Engine")
    logger.info("=" * 60)
    
    try:
        from sensevoice_engine import SenseVoiceEngine
        
        # 初始化引擎
        logger.info("1️⃣  Initializing engine...")
        engine = SenseVoiceEngine()
        logger.info("✅ Engine initialized")
        
        # 检查是否有测试音频文件
        test_audio = Path("test_audio.mp3")
        if not test_audio.exists():
            logger.warning("⚠️  No test audio file found (test_audio.mp3)")
            logger.info("   Please provide a test audio file to continue")
            logger.info("")
            logger.info("   Usage:")
            logger.info("   1. Place an audio file as 'test_audio.mp3'")
            logger.info("   2. Run: python test_sensevoice.py")
            return False
        
        # 处理测试音频
        logger.info(f"2️⃣  Processing test audio: {test_audio}")
        result = engine.parse(
            audio_path=str(test_audio),
            output_path="./test_output",
            language="auto"
        )
        
        logger.info("=" * 60)
        logger.info("✅ Test completed successfully!")
        logger.info("=" * 60)
        
        # 显示结果摘要
        json_data = result['json_data']
        logger.info(f"📊 Results:")
        logger.info(f"   Language: {json_data['metadata']['language']}")
        logger.info(f"   Speakers: {json_data['metadata']['speaker_count']}")
        logger.info(f"   Segments: {json_data['metadata']['segment_count']}")
        logger.info(f"   Text length: {len(json_data['content']['text'])} chars")
        logger.info("")
        logger.info(f"📁 Output files:")
        logger.info(f"   Markdown: {result['markdown_file']}")
        logger.info(f"   JSON: {result['json_file']}")
        
        # 显示前100个字符
        text_preview = json_data['content']['text'][:100]
        logger.info("")
        logger.info(f"📝 Text preview:")
        logger.info(f"   {text_preview}...")
        
        return True
        
    except ImportError as e:
        logger.error(f"❌ Import failed: {e}")
        logger.error("")
        logger.error("Please install dependencies:")
        logger.error("  pip install funasr modelscope")
        return False
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return False


def test_environment_only():
    """只测试环境，不处理音频"""
    logger.info("=" * 60)
    logger.info("🔍 Testing Environment Only")
    logger.info("=" * 60)
    
    try:
        from check_environment import check_all
        success = check_all()
        
        if success:
            logger.info("")
            logger.info("✅ Environment is ready!")
            logger.info("")
            logger.info("Next steps:")
            logger.info("  1. Place a test audio file as 'test_audio.mp3'")
            logger.info("  2. Run: python test_sensevoice.py")
        
        return success
        
    except Exception as e:
        logger.error(f"❌ Environment check failed: {e}")
        return False


if __name__ == '__main__':
    # 检查是否有命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == '--env-only':
        success = test_environment_only()
    else:
        success = test_basic()
    
    sys.exit(0 if success else 1)

