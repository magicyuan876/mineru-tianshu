"""
PaddleOCR-VL 环境检查脚本
检查所有依赖和配置是否正确
"""
import sys
import os
from pathlib import Path

def print_header(title):
    """打印标题"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def print_result(check_name, passed, message=""):
    """打印检查结果"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} - {check_name}")
    if message:
        print(f"     {message}")

def check_python_version():
    """检查 Python 版本"""
    print_header("1. Python 版本检查")
    version = sys.version_info
    passed = version.major == 3 and version.minor >= 8
    print_result(
        "Python 版本",
        passed,
        f"当前版本: {version.major}.{version.minor}.{version.micro}"
    )
    if not passed:
        print("     建议: Python 3.8 或更高版本")
    return passed

def check_paddlepaddle():
    """检查 PaddlePaddle 安装"""
    print_header("2. PaddlePaddle 检查")
    
    try:
        import paddle
        print_result("PaddlePaddle 已安装", True, f"版本: {paddle.__version__}")
        
        # 检查 GPU 支持
        has_gpu = paddle.device.is_compiled_with_cuda()
        print_result("CUDA 编译支持", has_gpu)
        
        if has_gpu:
            gpu_count = paddle.device.cuda.device_count()
            print_result("GPU 可用", True, f"检测到 {gpu_count} 个 GPU")
            
            # 打印 GPU 信息
            for i in range(gpu_count):
                gpu_name = paddle.device.cuda.get_device_name(i)
                print(f"     GPU {i}: {gpu_name}")
        else:
            print_result("GPU 可用", False, "PaddleOCR-VL 仅支持 GPU 模式")
            print("     ⚠️  警告: PaddleOCR-VL 不支持 CPU 推理")
            print("     安装命令: pip install paddlepaddle-gpu==3.2.0")
        
        return True
        
    except ImportError:
        print_result("PaddlePaddle 已安装", False)
        print("     安装命令:")
        print("     GPU 版本: pip install paddlepaddle-gpu==3.2.0")
        print("     注意: PaddleOCR-VL 仅支持 GPU 版本")
        return False
    except Exception as e:
        print_result("PaddlePaddle 检查", False, f"错误: {e}")
        return False

def check_paddleocr():
    """检查 PaddleOCR 安装"""
    print_header("3. PaddleOCR 检查")
    
    try:
        import paddleocr
        print_result("PaddleOCR 已安装", True, f"版本: {paddleocr.__version__}")
        
        # 尝试导入主要模块
        from paddleocr import PaddleOCR
        print_result("PaddleOCR 模块可用", True)
        
        return True
        
    except ImportError as e:
        print_result("PaddleOCR 已安装", False)
        print("     安装命令: pip install 'paddleocr[doc-parser]'")
        return False
    except Exception as e:
        print_result("PaddleOCR 检查", False, f"错误: {e}")
        return False

def check_dependencies():
    """检查其他依赖"""
    print_header("4. 依赖包检查")
    
    dependencies = [
        ("PyMuPDF", "fitz", "pip install PyMuPDF"),
        ("Pillow", "PIL", "pip install Pillow"),
        ("OpenCV", "cv2", "pip install opencv-python"),
        ("NumPy", "numpy", "pip install numpy"),
        ("ModelScope (可选)", "modelscope", "pip install modelscope"),
    ]
    
    all_passed = True
    for name, module, install_cmd in dependencies:
        try:
            __import__(module)
            print_result(name, True)
        except ImportError:
            is_optional = "(可选)" in name
            print_result(name, is_optional, f"安装: {install_cmd}")
            if not is_optional:
                all_passed = False
    
    return all_passed

def check_model_cache():
    """检查模型缓存信息"""
    print_header("5. 模型缓存检查")
    
    # PaddleOCR-VL 的默认缓存位置
    home_dir = Path.home()
    model_cache_dir = home_dir / '.paddleocr' / 'models'
    
    print(f"默认缓存目录: {model_cache_dir}")
    print("注意: 模型由 PaddleOCR 自动管理，不支持手动指定路径")
    
    if model_cache_dir.exists():
        print_result("缓存目录存在", True, "模型可能已下载")
        # 统计缓存大小
        try:
            import os
            total_size = sum(f.stat().st_size for f in model_cache_dir.rglob('*') if f.is_file())
            size_gb = total_size / (1024**3)
            if size_gb > 0.1:
                print(f"     缓存大小: {size_gb:.2f} GB")
        except:
            pass
    else:
        print_result("缓存目录存在", False, "首次使用时会自动创建并下载（约 2GB）")
    
    return True  # 这不是错误，只是提示信息

def check_disk_space():
    """检查磁盘空间"""
    print_header("6. 磁盘空间检查")
    
    try:
        import shutil
        home_dir = Path.home()
        stat = shutil.disk_usage(home_dir)
        
        free_gb = stat.free / (1024**3)
        print_result(
            "可用磁盘空间",
            free_gb > 5,
            f"{free_gb:.1f} GB 可用"
        )
        
        if free_gb < 5:
            print("     警告: PaddleOCR-VL 模型需要约 2GB 空间")
            print("     缓存位置: ~/.paddleocr/models/")
        
        return free_gb > 2
        
    except Exception as e:
        print_result("磁盘空间检查", False, f"错误: {e}")
        return False

def main():
    """主函数"""
    print("\n" + "🔍" * 35)
    print("  PaddleOCR-VL 环境检查")
    print("🔍" * 35)
    
    results = []
    
    # 执行所有检查
    results.append(("Python 版本", check_python_version()))
    results.append(("PaddlePaddle", check_paddlepaddle()))
    results.append(("PaddleOCR", check_paddleocr()))
    results.append(("依赖包", check_dependencies()))
    results.append(("模型缓存", check_model_cache()))
    results.append(("磁盘空间", check_disk_space()))
    
    # 打印总结
    print_header("检查总结")
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    for name, passed in results:
        status = "✅" if passed else "❌"
        print(f"{status} {name}")
    
    print("\n" + "-" * 70)
    print(f"通过: {passed_count}/{total_count}")
    print("-" * 70)
    
    if passed_count == total_count:
        print("\n🎉 所有检查通过！PaddleOCR-VL 环境配置完成。")
        print("\n下一步:")
        print("  1. 启动服务: python backend/start_all.py")
        print("  2. 提交任务时指定: backend=paddleocr-vl")
        return 0
    else:
        print("\n⚠️  部分检查未通过，请根据上述提示解决问题。")
        print("\n常见问题:")
        print("  1. 安装 PaddlePaddle GPU: pip install paddlepaddle-gpu==3.2.0")
        print("  2. 安装 PaddleOCR: pip install 'paddleocr[doc-parser]'")
        print("  3. 确保有 NVIDIA GPU 且 CUDA 12.6 可用")
        print("  4. 模型会在首次使用时自动下载（约 2GB）")
        return 1

if __name__ == '__main__':
    sys.exit(main())

