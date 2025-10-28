# PaddleOCR-VL 解析引擎（新版本）

基于最新的 PaddleOCR-VL API，支持 109+ 语言的自动识别，无需指定语言参数。

**参考文档**: [PaddleOCR-VL 官方文档](http://www.paddleocr.ai/main/version3.x/pipeline_usage/PaddleOCR-VL.html)

## ⚠️ 重要提示

- **仅支持 GPU**: PaddleOCR-VL 目前**不支持 CPU 及 Arm 架构**
- **GPU 要求**: NVIDIA GPU with Compute Capability ≥ 8.5
- **推荐 GPU**: RTX 3090, RTX 4090, A10, A100, H100

## ✨ 特性

### 🎯 核心功能（已启用最佳配置）

- ✅ **文档方向分类**: 自动检测并旋转文档（0°/90°/180°/270°）
- ✅ **文本图像矫正**: 修正拍照导致的变形、透视扭曲
- ✅ **版面区域检测**: 智能识别和排序，保持内容逻辑结构
- ✅ **自动语言识别**: 支持 109+ 语言，无需手动指定
- ✅ **GPU 加速**: 仅支持 GPU 推理，性能强劲
- ✅ **单例模式**: 每个进程只加载一次模型，节省资源
- ✅ **PDF 原生支持**: 无需手动转换，直接处理 PDF 多页文档
- ✅ **结构化输出**: 支持 Markdown、JSON 等多种输出格式

### 📊 识别能力

- ✅ **文本识别**: 印刷体、手写体
- ✅ **表格识别**: 复杂表格结构
- ✅ **公式识别**: 数学公式、化学式
- ✅ **图表识别**: 图片、图表说明
- ✅ **混合版面**: 多列、多语言混排

## 📦 安装

### 前置要求

1. **NVIDIA GPU**: Compute Capability ≥ 8.5 (推荐)
2. **CUDA 12.6**: 需要 CUDA 环境
3. **Linux 系统**: Windows 用户请使用 WSL 或 Docker

### 安装步骤

**方式一：一键安装（推荐）**

```bash
# 安装统一的后端依赖
cd backend
pip install -r requirements.txt
```

或使用清华源加速：

```bash
cd backend
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

**方式二：分步安装（如遇依赖冲突）**

详见 [backend/INSTALL.md](../INSTALL.md)

### 验证安装

```bash
# 检查 PaddlePaddle GPU 支持
python -c "import paddle; print('CUDA available:', paddle.device.is_compiled_with_cuda())"

# 检查 GPU 信息
python -c "import paddle; print('GPU count:', paddle.device.cuda.device_count()); print('GPU name:', paddle.device.cuda.get_device_name(0))"

# 验证 PaddleOCR-VL
python -c "from paddleocr import PaddleOCRVL; print('✅ PaddleOCR-VL 安装成功')"
```

### 运行环境检查

```bash
cd backend/paddleocr_vl
python check_environment.py
```

这个脚本会检查:

- ✅ Python 版本
- ✅ PaddlePaddle GPU 支持
- ✅ GPU 可用性和计算能力
- ✅ 依赖包安装情况
- ✅ 模型文件完整性

## 🚀 使用

### API 调用

提交任务时指定 `backend` 参数为 `paddleocr-vl`:

```bash
curl -X POST http://localhost:8000/api/v1/tasks/submit \
  -F "file=@document.pdf" \
  -F "backend=paddleocr-vl"
```

### 参数说明

| 参数 | 说明 | 可选值 | 默认值 |
|------|------|--------|--------|
| `backend` | 解析引擎 | `pipeline` / `deepseek-ocr` / `paddleocr-vl` | `pipeline` |

**注意**: PaddleOCR-VL 新版本会自动识别语言，无需指定 `paddleocr_lang` 参数。模型由 PaddleOCR 自动管理，缓存在 `~/.paddleocr/models/` 目录。

## 🌍 支持的语言

PaddleOCR-VL 新版本支持 **109+ 种语言的自动识别**，包括但不限于：

- **中文**: 简体、繁体
- **英文**: English
- **日文**: 日本語
- **韩文**: 한국어
- **欧洲语言**: 法文、德文、西班牙文、意大利文、俄文等
- **东南亚语言**: 泰文、越南文、印尼文等
- **中东语言**: 阿拉伯文、希伯来文等
- **印度语言**: 印地文、泰米尔文等

**关键优势**:

- ✅ **无需指定语言**: 模型会自动检测文档中的语言
- ✅ **混合语言支持**: 可以识别包含多种语言的文档
- ✅ **高准确率**: 基于最新的视觉-语言大模型

**模型管理说明：**

- **自动管理**: 模型由 PaddleOCR 自动下载和管理，无需手动操作
- **缓存位置**: `~/.paddleocr/models/` 目录（由 PaddleOCR 自动创建）
- **首次使用**: 自动下载模型（约 2GB）
- **下载源**: 从 Hugging Face 或 ModelScope 自动下载
- **加载时机**: 首次使用时自动下载并加载到内存

**使用示例：**

```bash
# 使用 PaddleOCR-VL（模型自动管理）
curl -X POST http://localhost:8000/api/v1/tasks/submit \
  -F "file=@document.pdf" \
  -F "backend=paddleocr-vl"
```

## 📤 输出格式

PaddleOCR-VL 解析完成后会生成以下文件:

```
output/
├── filename.md          # 标准 Markdown 文件 (主要输出)
├── result.json          # 原始 OCR 结果 (JSON 格式)
└── images/              # PDF 转换的图像（如果输入是 PDF）
    ├── filename_page1.png
    ├── filename_page2.png
    └── ...
```

### 主要输出文件

- **`filename.md`**: 标准 Markdown 文件
  - ✅ 可以直接用任何 Markdown 工具打开
  - ✅ 包含识别的文本内容，按页面组织
  - ✅ 格式统一，与其他 Backend 兼容

- **`result.json`**: 原始 OCR 结果
  - 包含文本、位置坐标、置信度等详细信息
  - 可用于精确定位和后处理

### 与其他 Backend 的统一性

所有 Backend 现在都输出标准 `.md` 文件:

| Backend | 输出文件 | 格式 | 特点 |
|---------|---------|------|------|
| MinerU | `filename.md` | 标准 Markdown | 完整文档解析 |
| DeepSeek OCR | `filename.md` | 标准 Markdown | 高精度 OCR |
| PaddleOCR-VL | `filename.md` | 标准 Markdown | 多语言支持 |

## 🆚 Backend 对比

| Backend | 引擎 | 特点 | 适用场景 | GPU 需求 |
|---------|------|------|----------|----------|
| `pipeline` | MinerU | 完整文档解析，支持表格、公式 | 通用文档 | 建议使用 |
| `deepseek-ocr` | DeepSeek OCR | 高精度 OCR，文档理解 | 复杂文档 | 必须使用 |
| `paddleocr-vl` | PaddleOCR-VL | 100+ 语言，视觉-语言大模型 | 多语言文档 | **必须使用** |

### 选择建议

- **多语言文档识别** → 选择 `paddleocr-vl`（需要 GPU）
- **中文/英文高精度** → 选择 `deepseek-ocr`（需要 GPU）
- **完整文档解析** → 选择 `pipeline`（MinerU，需要 GPU）

## 🎯 性能对比

| Backend | CPU 支持 | GPU 加速 | 多语言 | 表格识别 | 公式识别 |
|---------|---------|---------|--------|---------|---------|
| MinerU | ❌ | ✅ | ✅ | ✅ | ✅ |
| DeepSeek OCR | ❌ | ✅ | ✅ | ✅ | ✅ |
| PaddleOCR-VL | ❌ | ✅ (必需) | ✅✅ (109+) | ✅ | ✅ |

## 💡 示例

### Python 客户端

```python
import aiohttp

async with aiohttp.ClientSession() as session:
    data = aiohttp.FormData()
    data.add_field('file', open('document.pdf', 'rb'))
    data.add_field('backend', 'paddleocr-vl')
    data.add_field('paddleocr_lang', 'ch')

    async with session.post(
        'http://localhost:8000/api/v1/tasks/submit',
        data=data
    ) as resp:
        result = await resp.json()
        print(result)
```

### cURL

```bash
# 中文文档
curl -X POST http://localhost:8000/api/v1/tasks/submit \
  -F "file=@chinese_doc.pdf" \
  -F "backend=paddleocr-vl" \
  -F "paddleocr_lang=ch"

# 英文文档
curl -X POST http://localhost:8000/api/v1/tasks/submit \
  -F "file=@english_doc.pdf" \
  -F "backend=paddleocr-vl" \
  -F "paddleocr_lang=en"

# 日文文档
curl -X POST http://localhost:8000/api/v1/tasks/submit \
  -F "file=@japanese_doc.pdf" \
  -F "backend=paddleocr-vl" \
  -F "paddleocr_lang=japan"
```

## 🔧 高级配置

### GPU 配置

如果安装了 GPU 版本，PaddleOCR 会自动使用 GPU 加速。

检查 GPU 是否可用：

```bash
python -c "import paddle; print(paddle.device.is_compiled_with_cuda())"
```

### 模型缓存

PaddleOCR-VL 会自动管理模型缓存：

- **默认位置**: `~/.paddleocr/models/`
- **自动下载**: 首次使用时自动下载
- **缓存复用**: 后续使用直接从缓存加载
- **无需配置**: 不支持手动指定模型路径

## 📝 注意事项

1. **首次使用**: 首次使用时会自动下载模型文件（约 2GB），请耐心等待并确保网络畅通
2. **模型管理**: 模型由 PaddleOCR 自动管理，缓存在 `~/.paddleocr/models/`，不支持手动指定路径
3. **GPU 需求**: PaddleOCR-VL 仅支持 GPU 推理，不支持 CPU 模式
4. **显存占用**: GPU 模式需要足够的显存
5. **识别精度**: 对于复杂版面，建议使用 `deepseek-ocr` 或 `pipeline`

## 🐛 故障排查

### 问题 1: 模型下载失败

**原因**: PaddleOCR-VL 会自动从 Hugging Face 或 ModelScope 下载模型

**解决方案:**

1. 确保网络连接正常，可以访问 Hugging Face 或 ModelScope
2. 如果网络受限，可以配置代理环境变量：

```bash
export http_proxy=http://your-proxy:port
export https_proxy=http://your-proxy:port
```

3. 等待模型自动下载完成（首次使用需要一些时间，取决于网络速度）

### 问题 2: GPU 不可用

**检查:**

```bash
python -c "import paddle; print(paddle.device.is_compiled_with_cuda())"
```

**解决方案:**

- 确认安装了 GPU 版本的 PaddlePaddle: `pip install paddlepaddle-gpu==3.2.0`
- 检查 CUDA 驱动是否正确安装（需要 CUDA 12.6）
- **注意**: PaddleOCR-VL 仅支持 GPU 模式，不支持 CPU 推理

### 问题 3: 识别效果不佳

**建议:**

1. 确保图片清晰度足够（DPI ≥ 200）
2. 尝试不同的语言参数
3. 对于复杂文档，考虑使用 DeepSeek OCR

## 📚 参考资料

- [PaddleOCR 官方文档](https://github.com/PaddlePaddle/PaddleOCR)
- [PaddleOCR 语言支持列表](https://github.com/PaddlePaddle/PaddleOCR/blob/main/doc/doc_ch/multi_languages.md)
- [PaddlePaddle 安装指南](https://www.paddlepaddle.org.cn/install/quick)
- [ModelScope 平台](https://www.modelscope.cn/)
