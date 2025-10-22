# DeepSeek OCR GPU 要求说明

## ⚠️ 重要提示

**DeepSeek OCR 模型必须在 GPU 环境下运行,不支持 CPU。**

## 问题说明

如果您遇到以下错误:
```
❌ DeepSeek OCR failed: Torch not compiled with CUDA enabled
```

这说明您的环境不满足 GPU 要求。

## 环境要求

### 硬件要求
- **必须有 NVIDIA 显卡** (支持 CUDA)
- 显存建议: ≥ 8GB

### 软件要求
- CUDA Toolkit (11.8 或 12.1)
- GPU 版本的 PyTorch

## 解决方案

### 1. 检查您的显卡

在命令行运行:
```bash
nvidia-smi
```

如果显示显卡信息,说明您有 NVIDIA 显卡。如果提示找不到命令或没有显卡,说明您的电脑不支持 CUDA。

### 2. 检查 PyTorch CUDA 支持

```bash
# 激活 conda 环境
conda activate MinerU

# 检查 CUDA 是否可用
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

如果输出 `CUDA available: False`,说明需要安装 GPU 版本的 PyTorch。

### 3. 安装 GPU 版本的 PyTorch

#### 方案 A: CUDA 11.8 (推荐)

```bash
# 1. 卸载当前版本
pip uninstall torch torchvision torchaudio -y

# 2. 安装 CUDA 11.8 版本
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# 3. 验证安装
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'CUDA version: {torch.version.cuda}')"
```

#### 方案 B: CUDA 12.1

```bash
# 1. 卸载当前版本
pip uninstall torch torchvision torchaudio -y

# 2. 安装 CUDA 12.1 版本
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# 3. 验证安装
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'CUDA version: {torch.version.cuda}')"
```

### 4. 验证安装成功

运行测试脚本:
```bash
cd backend/deepseek_ocr
python test_basic.py
```

如果成功,应该看到模型加载信息:
```
✅ DeepSeek OCR Model loaded successfully!
   Device: cuda
```

## 常见问题

### Q: 我的电脑没有 NVIDIA 显卡怎么办?

A: 抱歉,DeepSeek OCR 模型不支持 CPU 运行。您需要:
- 使用有 NVIDIA 显卡的电脑
- 使用云服务器 (如 AWS/阿里云/腾讯云的 GPU 实例)

### Q: 安装 CUDA 版本的 PyTorch 后还是不行?

A: 请检查:
1. CUDA 驱动是否正确安装 (`nvidia-smi` 命令)
2. PyTorch CUDA 版本与系统 CUDA 版本是否兼容
3. 是否在正确的 conda 环境中

### Q: 我的显卡是 AMD 的可以吗?

A: 不可以。DeepSeek OCR 需要 NVIDIA 显卡和 CUDA 支持,不支持 AMD 的 ROCm。

## 技术原因

DeepSeek OCR 模型的推理代码中使用了:
- `torch.autocast("cuda")` - 强制使用 CUDA
- `.cuda()` - 将数据移动到 GPU

这些操作无法在 CPU 上执行,因此模型必须在 GPU 环境下运行。

## 参考资源

- [PyTorch 官方安装指南](https://pytorch.org/get-started/locally/)
- [CUDA 工具包下载](https://developer.nvidia.com/cuda-downloads)
- [DeepSeek OCR 官方仓库](https://huggingface.co/deepseek-ai/DeepSeek-OCR)

