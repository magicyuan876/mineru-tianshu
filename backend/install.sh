#!/bin/bash

echo "📦 Installing MinerU Tianshu Backend Dependencies..."
echo ""
echo "📋 Installation Options:"
echo "  - Core Dependencies (Required)"
echo "  - PaddleOCR-VL"
echo "  - Audio Processing (SenseVoice)"
echo "  - Video Processing"
echo "  - Watermark Removal"
echo "  - Format Engines (FASTA/GenBank)"
echo ""
echo "Installation Strategy:"
echo "  1. Install PaddlePaddle first (CUDA 12.6)"
echo "  2. Install PyTorch with compatible version"
echo "  3. Install packages separately to avoid conflicts"
echo "  4. Use legacy resolver for final dependency resolution"
echo ""
echo "============================================================"

# Step 1: Check system
echo ""
echo "[Step 1/8] Checking system requirements..."
if [ "$(uname)" != "Linux" ]; then
    echo "Warning: This script is designed for Linux/WSL"
    echo "Windows users should use WSL2 or Docker"
fi

# Check GPU
if command -v nvidia-smi &> /dev/null; then
    echo "✓ GPU detected:"
    nvidia-smi --query-gpu=name --format=csv,noheader | head -1
else
    echo "⚠ Warning: nvidia-smi not found. GPU may not be available."
fi

# Step 2: Install system library
echo ""
echo "[Step 2/8] Installing system libraries..."
if command -v apt-get &> /dev/null; then
    sudo apt-get update
    sudo apt-get install -y libgomp1 ffmpeg
    echo "✓ System libraries installed (libgomp1, ffmpeg)"
else
    echo "⚠ Warning: apt-get not found. You may need to install libgomp1 and ffmpeg manually."
fi

# Step 3: Install PaddlePaddle
echo ""
echo "[Step 3/8] Installing PaddlePaddle GPU 3.2.0..."
echo "  This may take a few minutes..."
pip install paddlepaddle-gpu==3.2.0 -i https://www.paddlepaddle.org.cn/packages/stable/cu126/
echo "✓ PaddlePaddle installed"

# Step 4: Install PyTorch
echo ""
echo "[Step 4/8] Installing PyTorch 2.6.0+cu126..."
echo "  This may take a few minutes..."
pip install torch==2.6.0+cu126 torchvision==0.21.0+cu126 --index-url https://download.pytorch.org/whl/cu126
echo "✓ PyTorch installed"

# Step 5: Install core packages separately (avoid complex resolution)
echo ""
echo "[Step 5/8] Installing OCR engines..."
cd "$(dirname "$0")" || exit
pip install "mineru[core]" -i https://pypi.tuna.tsinghua.edu.cn/simple --no-deps || echo "⚠ MinerU install warning (non-critical)"
pip install "paddleocr[doc-parser]" -i https://pypi.tuna.tsinghua.edu.cn/simple --no-deps || echo "⚠ PaddleOCR install warning (non-critical)"
pip install transformers==4.46.3 tokenizers==0.20.3 -i https://pypi.tuna.tsinghua.edu.cn/simple --no-deps
echo "✓ OCR engines installed"

# Step 6: Install web framework
echo ""
echo "[Step 6/8] Installing web framework..."
pip install fastapi uvicorn litserve aiohttp -i https://pypi.tuna.tsinghua.edu.cn/simple --no-deps
echo "✓ Web framework installed"

# Step 7: Install utilities and image processing
echo ""
echo "[Step 7/8] Installing utilities..."
pip install PyMuPDF Pillow img2pdf einops easydict addict loguru modelscope -i https://pypi.tuna.tsinghua.edu.cn/simple --no-deps
pip install albumentations minio markitdown -i https://pypi.tuna.tsinghua.edu.cn/simple --no-deps || echo "⚠ Some optional packages skipped"
echo "✓ Utilities installed"

# Step 8: Resolve all remaining dependencies with legacy resolver
echo ""
echo "[Step 8/8] Resolving remaining dependencies..."
echo "  Using legacy resolver to avoid 'resolution-too-deep' errors..."
echo "  This may show some warnings, but should complete successfully..."
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --use-deprecated=legacy-resolver
echo "✓ All dependencies resolved"

# Verification
echo ""
echo "============================================================"
echo "Verifying installation..."
echo "============================================================"

python3 << 'EOF'
import sys

print("\nChecking frameworks...")
success = True

# Check PaddlePaddle
try:
    import paddle
    print(f"✓ PaddlePaddle: {paddle.__version__}")
    if paddle.device.is_compiled_with_cuda():
        print(f"  CUDA: Available ({paddle.device.cuda.device_count()} GPU)")
    else:
        print("  ⚠ CUDA: Not available")
        success = False
except Exception as e:
    print(f"✗ PaddlePaddle: {str(e)[:80]}")
    success = False

# Check PyTorch
try:
    import torch
    print(f"✓ PyTorch: {torch.__version__}")
    if torch.cuda.is_available():
        print(f"  CUDA: Available ({torch.cuda.device_count()} GPU)")
    else:
        print("  ⚠ CUDA: Not available")
        success = False
except Exception as e:
    print(f"✗ PyTorch: {str(e)[:80]}")
    success = False

# Check Transformers
try:
    from transformers import AutoModel
    print("✓ Transformers: Ready")
except Exception as e:
    print(f"✗ Transformers: {str(e)[:80]}")
    success = False

# Check PaddleOCR-VL
try:
    from paddleocr import PaddleOCRVL
    print("✓ PaddleOCR-VL: Ready")
except Exception as e:
    print(f"⚠ PaddleOCR-VL: {str(e)[:80]}")
    # Not critical if this fails

# Check FunASR (Audio Processing)
try:
    import funasr
    print("✓ FunASR: Ready (Audio Processing)")
except Exception as e:
    print(f"⚠ FunASR: {str(e)[:80]}")
    # Not critical if this fails

print("")
if success:
    print("="*60)
    print("✓ Installation successful!")
    print("="*60)
    sys.exit(0)
else:
    print("="*60)
    print("✗ Installation completed with warnings")
    print("  Please check the errors above")
    print("="*60)
    sys.exit(1)
EOF

VERIFY_EXIT=$?

echo ""
if [ $VERIFY_EXIT -eq 0 ]; then
    echo "============================================================"
    echo "Installation complete! You can now start the server."
    echo "============================================================"
else
    echo "============================================================"
    echo "Installation completed with warnings."
    echo "See INSTALL.md for troubleshooting."
    echo "============================================================"
fi
