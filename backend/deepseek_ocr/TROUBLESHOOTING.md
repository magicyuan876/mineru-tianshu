# DeepSeek OCR 故障排除指南

## 常见错误及解决方案

### 错误 1: `Torch not compiled with CUDA enabled`

**完整错误信息:**
```
❌ DeepSeek OCR failed: Torch not compiled with CUDA enabled
```

**原因:**
您安装的是 CPU 版本的 PyTorch,但 DeepSeek OCR 模型需要 GPU 支持。

**解决方案:**

1. **确认您有 NVIDIA 显卡**
   ```bash
   nvidia-smi
   ```
   如果能看到显卡信息,说明硬件支持 CUDA。

2. **重新安装 GPU 版本的 PyTorch**
   ```bash
   # 在 MinerU 环境中
   conda activate MinerU
   
   # 卸载当前版本
   pip uninstall torch torchvision torchaudio -y
   
   # 安装 CUDA 11.8 版本 (推荐)
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
   ```

3. **验证安装**
   ```bash
   python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
   ```
   应该输出: `CUDA available: True`

4. **运行环境检查**
   ```bash
   cd backend/deepseek_ocr
   python check_environment.py
   ```

详细说明: [GPU_REQUIREMENT.md](./GPU_REQUIREMENT.md)

---

### 错误 2: `CUDA out of memory`

**错误信息:**
```
RuntimeError: CUDA out of memory
```

**原因:**
GPU 显存不足。

**解决方案:**

1. **降低分辨率**
   ```python
   # 使用更小的分辨率
   deepseek_resolution='small'  # 或 'tiny'
   ```

2. **关闭其他占用 GPU 的程序**
   ```bash
   # 查看 GPU 使用情况
   nvidia-smi
   ```

3. **清理 GPU 缓存**
   ```python
   import torch
   torch.cuda.empty_cache()
   ```

4. **建议配置:**
   - 显存 < 8GB: 使用 `tiny` 或 `small` 分辨率
   - 显存 8-12GB: 使用 `base` 分辨率
   - 显存 > 12GB: 可以使用 `large` 分辨率

---

### 错误 3: 模型下载失败

**错误信息:**
```
Cannot download model from HuggingFace
```

**原因:**
网络问题或 HuggingFace 访问受限。

**解决方案:**

1. **使用 ModelScope (国内推荐)**
   
   引擎会自动尝试从 ModelScope 下载,如果还是失败:
   
   ```bash
   # 设置 ModelScope 镜像
   export MODELSCOPE_CACHE=~/modelscope
   ```

2. **手动下载模型**
   
   从 [DeepSeek OCR](https://huggingface.co/deepseek-ai/DeepSeek-OCR) 手动下载,放到:
   ```
   models/deepseek_ocr/deepseek-ai/DeepSeek-OCR/
   ```

3. **配置代理**
   ```bash
   export HTTP_PROXY=http://your-proxy:port
   export HTTPS_PROXY=http://your-proxy:port
   ```

---

### 错误 4: `ImportError: cannot import name 'flash_attn'`

**错误信息:**
```
ImportError: cannot import name 'flash_attn'
```

**原因:**
flash-attn 包未安装 (这是可选的优化包)。

**解决方案:**

**这不是严重错误!** 系统会自动回退到默认实现。

如果想安装 flash-attn (仅 Linux):
```bash
pip install flash-attn --no-build-isolation
```

注意: Windows 和 macOS 不支持 flash-attn,会自动使用默认实现。

---

### 错误 5: 模型加载慢

**现象:**
首次加载模型需要很长时间。

**原因:**
1. 模型文件约 10GB,首次下载需要时间
2. 模型加载到 GPU 需要时间

**解决方案:**

1. **预下载模型**
   ```bash
   cd backend/deepseek_ocr
   python -c "from engine import get_engine; get_engine()"
   ```

2. **使用本地模型路径**
   
   下载好模型后,引擎会自动检测本地路径,避免重复下载。

3. **等待时间参考:**
   - 首次下载: 5-20 分钟 (取决于网速)
   - 模型加载: 1-3 分钟 (取决于 GPU)
   - 后续使用: 秒级响应 (模型已缓存在内存)

---

## 环境检查清单

在使用 DeepSeek OCR 前,请确认:

- [ ] ✅ 有 NVIDIA 显卡 (`nvidia-smi` 可用)
- [ ] ✅ 显存 ≥ 8GB
- [ ] ✅ 安装了 GPU 版本的 PyTorch
- [ ] ✅ `torch.cuda.is_available()` 返回 `True`
- [ ] ✅ 所有依赖包已安装 (`pip install -r requirements.txt`)
- [ ] ✅ 模型文件完整 (首次会自动下载)

**快速检查:**
```bash
cd backend/deepseek_ocr
python check_environment.py
```

---

## 性能优化建议

### 1. 选择合适的分辨率

| 分辨率 | 速度 | 精度 | 显存占用 | 适用场景 |
|--------|------|------|----------|----------|
| `tiny` | 最快 | 低 | 最小 | 快速预览 |
| `small` | 快 | 中 | 小 | 一般文档 |
| `base` | 中 | 高 | 中 | 标准文档 (推荐) |
| `large` | 慢 | 最高 | 大 | 高精度需求 |
| `dynamic` | 中 | 高 | 中 | 自适应 |

### 2. 批量处理

如果需要处理多个文件,考虑:
- 使用任务队列避免并发加载多个模型实例
- 复用已加载的模型实例

### 3. Linux 优化

在 Linux 上安装 flash-attn 可以提升 20-30% 性能:
```bash
pip install flash-attn --no-build-isolation
```

---

## 获取帮助

如果上述方案都无法解决您的问题:

1. **查看日志**
   
   完整的错误信息在日志中,帮助定位问题:
   ```bash
   # 查看 API server 日志
   tail -f logs/api_server.log
   
   # 查看 worker 日志  
   tail -f logs/worker.log
   ```

2. **提交 Issue**
   
   包含以下信息:
   - 完整的错误日志
   - 环境检查结果 (`python check_environment.py`)
   - 操作系统和 Python 版本
   - GPU 型号和显存大小

3. **参考文档**
   
   - [README.md](./README.md) - 安装和使用指南
   - [GPU_REQUIREMENT.md](./GPU_REQUIREMENT.md) - GPU 要求详解
   - [QUICKSTART.md](./QUICKSTART.md) - 快速入门

---

## 相关资源

- [PyTorch 官方文档](https://pytorch.org/docs/stable/index.html)
- [CUDA 工具包](https://developer.nvidia.com/cuda-downloads)
- [DeepSeek OCR 官方仓库](https://huggingface.co/deepseek-ai/DeepSeek-OCR)
- [ModelScope](https://modelscope.cn/)

