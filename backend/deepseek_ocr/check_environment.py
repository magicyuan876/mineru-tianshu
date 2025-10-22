"""
环境检查脚本
用于诊断 DeepSeek OCR 运行环境是否满足要求
"""
import sys

def check_environment():
    """检查环境配置"""
    print("=" * 80)
    print("🔍 DeepSeek OCR 环境检查")
    print("=" * 80)
    print()
    
    issues = []
    warnings = []
    
    # 1. 检查 Python 版本
    print("📌 Python 版本:")
    python_version = sys.version.split()[0]
    print(f"   {python_version}")
    if sys.version_info < (3, 8):
        issues.append("Python 版本过低，建议 >= 3.8")
    print()
    
    # 2. 检查 PyTorch
    print("📌 检查 PyTorch:")
    try:
        import torch
        print(f"   ✅ PyTorch 已安装: {torch.__version__}")
    except ImportError:
        print("   ❌ PyTorch 未安装")
        issues.append("请安装 PyTorch: pip install torch")
        return
    print()
    
    # 3. 检查 CUDA
    print("📌 检查 CUDA:")
    if torch.cuda.is_available():
        print(f"   ✅ CUDA 可用")
        print(f"   版本: {torch.version.cuda}")
        print(f"   设备数量: {torch.cuda.device_count()}")
        for i in range(torch.cuda.device_count()):
            device_name = torch.cuda.get_device_name(i)
            device_memory = torch.cuda.get_device_properties(i).total_memory / 1024**3
            print(f"   GPU {i}: {device_name} ({device_memory:.1f} GB)")
            if device_memory < 8:
                warnings.append(f"GPU {i} 显存不足 8GB，可能影响性能")
    else:
        print("   ❌ CUDA 不可用")
        issues.append("CUDA 不可用 - DeepSeek OCR 需要 GPU 支持")
        
        # 提供详细诊断
        print()
        print("   📋 可能的原因:")
        print("      1. 您的电脑没有 NVIDIA 显卡")
        print("      2. 没有安装 CUDA 驱动 (运行 nvidia-smi 检查)")
        print("      3. 安装的是 CPU 版本的 PyTorch")
        print()
        print("   🔧 解决方案:")
        print("      # 卸载当前版本")
        print("      pip uninstall torch torchvision torchaudio")
        print()
        print("      # 安装 CUDA 11.8 版本")
        print("      pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118")
        print()
        print("      # 或者安装 CUDA 12.1 版本")
        print("      pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121")
    print()
    
    # 4. 检查依赖包
    print("📌 检查依赖包:")
    required_packages = {
        'transformers': 'transformers',
        'Pillow': 'PIL',
        'loguru': 'loguru',
        'addict': 'addict',
        'torchvision': 'torchvision',
        'modelscope': 'modelscope',
    }
    
    for package_name, import_name in required_packages.items():
        try:
            module = __import__(import_name)
            version = getattr(module, '__version__', 'unknown')
            print(f"   ✅ {package_name}: {version}")
        except ImportError:
            print(f"   ❌ {package_name}: 未安装")
            issues.append(f"请安装 {package_name}")
    print()
    
    # 5. 检查 flash-attn (可选)
    print("📌 检查 flash-attn (可选优化):")
    try:
        import flash_attn
        print(f"   ✅ flash-attn 已安装: {flash_attn.__version__}")
    except ImportError:
        print("   ⚠️  flash-attn 未安装 (使用默认实现)")
        warnings.append("flash-attn 未安装，将使用默认实现 (性能略低)")
    print()
    
    # 6. 检查模型文件
    print("📌 检查模型文件:")
    from pathlib import Path
    project_root = Path(__file__).parent.parent.parent
    model_path = project_root / 'models' / 'deepseek_ocr' / 'deepseek-ai' / 'DeepSeek-OCR'
    
    if model_path.exists():
        required_files = [
            'config.json',
            'tokenizer.json',
            'modeling_deepseekocr.py',
            'model-00001-of-000001.safetensors'
        ]
        
        all_exists = True
        for file_name in required_files:
            file_path = model_path / file_name
            if file_path.exists():
                print(f"   ✅ {file_name}")
            else:
                print(f"   ❌ {file_name} 缺失")
                all_exists = False
        
        if not all_exists:
            issues.append("模型文件不完整，将在首次运行时自动下载")
    else:
        print("   ⚠️  模型未下载")
        warnings.append("模型将在首次运行时自动下载 (约 10GB)")
    print()
    
    # 总结
    print("=" * 80)
    print("📊 检查结果:")
    print("=" * 80)
    
    if not issues and not warnings:
        print("✅ 环境检查通过! 所有要求都已满足。")
        print()
        print("🚀 您可以开始使用 DeepSeek OCR 了!")
        print()
        print("   测试命令:")
        print("   cd backend/deepseek_ocr")
        print("   python test_basic.py")
        return True
    
    if warnings:
        print()
        print("⚠️  警告:")
        for i, warning in enumerate(warnings, 1):
            print(f"   {i}. {warning}")
    
    if issues:
        print()
        print("❌ 发现问题:")
        for i, issue in enumerate(issues, 1):
            print(f"   {i}. {issue}")
        print()
        print("❗ 请解决上述问题后再使用 DeepSeek OCR")
        print()
        print("📖 详细说明: backend/deepseek_ocr/GPU_REQUIREMENT.md")
        return False
    
    return True

if __name__ == '__main__':
    success = check_environment()
    sys.exit(0 if success else 1)

