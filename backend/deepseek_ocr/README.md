# DeepSeek OCR 解析引擎

作为可选的 backend 解析引擎，支持 PDF 和图片的高精度文档解析。

## ⚠️ GPU 要求

**DeepSeek OCR 模型必须在 GPU 环境下运行，不支持 CPU。**

### 硬件要求

- ✅ **必须有 NVIDIA 显卡** (支持 CUDA)
- 显存建议: ≥ 8GB

### 软件要求

- CUDA Toolkit (11.8 或 12.1)
- GPU 版本的 PyTorch

如果您遇到 `Torch not compiled with CUDA enabled` 错误，请查看
[GPU_REQUIREMENT.md](./GPU_REQUIREMENT.md) 获取详细解决方案。

## 安装

### 1. 安装统一的后端依赖

```bash
# 安装所有后端依赖（包括 DeepSeek OCR）
cd backend
pip install -r requirements.txt
```

或使用清华源加速：

```bash
cd backend
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 2. 验证 CUDA 可用

```bash
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

应该输出: `CUDA available: True`

### 4. 运行环境检查 (推荐)

运行环境检查脚本,自动诊断所有配置:

```bash
cd backend/deepseek_ocr
python check_environment.py
```

这个脚本会检查:

- ✅ Python 版本
- ✅ PyTorch 安装和 CUDA 支持
- ✅ GPU 信息和显存
- ✅ 依赖包安装情况
- ✅ 模型文件完整性

如果检查失败,会给出详细的解决方案。

**特性：**

- **跨平台支持**: Linux 自动安装 flash-attn，Windows/macOS 使用默认实现
- **自动下载模型**: 首次使用时自动从 ModelScope/HuggingFace 下载
- **指定缓存目录**: 可通过参数指定模型下载位置
- **延迟加载**: 启动时只下载模型，首次解析时才加载到内存

## 使用

### API 调用

提交任务时指定 `backend` 参数为 `deepseek-ocr`:

```bash
curl -X POST http://localhost:8000/api/v1/tasks/submit \
  -F "file=@document.pdf" \
  -F "backend=deepseek-ocr"
```

### 可选参数

在提交任务时可以通过表单字段传递额外参数：

```bash
curl -X POST http://localhost:8000/api/v1/tasks/submit \
  -F "file=@document.pdf" \
  -F "backend=deepseek-ocr" \
  -F "deepseek_resolution=base" \
  -F "deepseek_prompt_type=document"
```

### 参数说明

| 参数 | 说明 | 可选值 | 默认值 |
|------|------|--------|--------|
| `backend` | 解析引擎 | `pipeline` / `deepseek-ocr` | `pipeline` |
| `deepseek_resolution` | 分辨率 | `tiny`/`small`/`base`/`large`/`dynamic` | `base` |
| `deepseek_prompt_type` | 提示词 | `document`/`image`/`free`/`figure` | `document` |
| `deepseek_cache_dir` | 缓存目录 | 任意路径 | 根目录 `/models/deepseek_ocr` |

**模型下载说明：**

- **默认位置**: 项目根目录下的 `models/deepseek_ocr/` 文件夹
- **首次使用**: 自动下载（约 5-10GB）
- **下载源**: 优先从 ModelScope 下载（国内更快）
- **加载时机**: 启动时下载，首次解析时加载到内存

**自定义下载位置示例：**

```bash
# 使用默认位置（项目目录/models/deepseek_ocr）
curl -X POST http://localhost:8000/api/v1/tasks/submit \
  -F "file=@document.pdf" \
  -F "backend=deepseek-ocr"

# 自定义下载位置
curl -X POST http://localhost:8000/api/v1/tasks/submit \
  -F "file=@document.pdf" \
  -F "backend=deepseek-ocr" \
  -F "deepseek_cache_dir=/data/models/deepseek_ocr"
```

## 输出格式

DeepSeek OCR 解析完成后会生成以下文件:

```
output/
├── filename.md                   # 标准 Markdown 文件 (主要输出)
├── result.mmd                    # MMD 格式原始文件 (备份)
├── result_with_boxes.jpg         # 带边界框标注的原图
└── images/                       # 提取的图像目录
    ├── 0.jpg
    ├── 1.jpg
    └── ...
```

### 主要输出文件

- **`filename.md`**: 标准 Markdown 文件,与 MinerU 和 MarkItDown 输出格式统一
  - ✅ 可以直接用任何 Markdown 工具打开
  - ✅ 包含完整的文档内容(文本、图像、表格、公式)
  - ✅ 图像引用相对路径 `![](images/0.jpg)`

- **`result.mmd`**: MMD (Multimodal Markdown) 原始文件
  - 包含额外的坐标标记 `<|ref|>` 和 `<|det|>`
  - 可用于精确定位和版面分析
  - 详细说明: [MMD_FORMAT.md](./MMD_FORMAT.md)

### 与其他 Backend 的统一性

所有 Backend 现在都输出标准 `.md` 文件:

| Backend | 输出文件 | 格式 |
|---------|---------|------|
| MinerU | `filename.md` | 标准 Markdown |
| DeepSeek OCR | `filename.md` | 标准 Markdown |
| MarkItDown | `filename.md` | 标准 Markdown |

### 分辨率说明

| 分辨率 | 尺寸 | Tokens | 适用场景 | 显存需求 |
|--------|------|--------|----------|----------|
| tiny | 512×512 | 64 | 快速预览 | ~3-4GB |
| small | 640×640 | 100 | 简单文档 | ~4-5GB |
| base | 1024×1024 | 256 | 标准文档（推荐）| ~6-8GB |
| large | 1280×1280 | 400 | 复杂文档 | ~8-10GB |
| dynamic | 动态 | 动态 | 长文档 | 动态 |

**显存建议**:

- 6GB 显存: 推荐使用 `small`
- 8GB 显存: 可以使用 `base`
- 12GB+ 显存: 可以使用 `large`

## Backend 对比

| Backend | 引擎 | 特点 | 适用场景 |
|---------|------|------|----------|
| `pipeline` | MinerU | 完整文档解析，支持表格、公式 | 通用文档 |
| `deepseek-ocr` | DeepSeek OCR | 高精度 OCR，单例加载 | 需要高精度 OCR |

## 特性

- ✅ 单例模式（每个进程只加载一次模型）
- ✅ 优先从 ModelScope 下载
- ✅ 自动设备选择（CUDA/CPU/MPS）
- ✅ 线程安全
- ✅ 与 MinerU 无缝切换

## 示例

### Python 客户端

```python
import aiohttp

async with aiohttp.ClientSession() as session:
    data = aiohttp.FormData()
    data.add_field('file', open('document.pdf', 'rb'))
    data.add_field('backend', 'deepseek-ocr')
    data.add_field('deepseek_resolution', 'base')

    async with session.post(
        'http://localhost:8000/api/v1/tasks/submit',
        data=data
    ) as resp:
        result = await resp.json()
        print(result)
```

### cURL

```bash
# 使用 DeepSeek OCR
curl -X POST http://localhost:8000/api/v1/tasks/submit \
  -F "file=@test.pdf" \
  -F "backend=deepseek-ocr" \
  -F "deepseek_resolution=large"

# 使用 MinerU (默认)
curl -X POST http://localhost:8000/api/v1/tasks/submit \
  -F "file=@test.pdf" \
  -F "backend=pipeline"
```
