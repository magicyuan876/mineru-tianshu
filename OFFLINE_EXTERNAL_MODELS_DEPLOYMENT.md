# 天枢离线镜像与外置模型目录落地方案

## 1. 目标

在完全断网的生产环境部署天枢服务，要求：

- Docker 镜像只包含系统依赖、Python 依赖、应用代码和启动脚本。
- 不把 MinerU、PaddleOCR-VL、FunASR、YOLO、LaMa 等模型打包进镜像。
- 所有模型在联网准备机提前下载到一个外部目录，部署时单独传输到离线服务器。
- 运行时只读取外部模型目录或由该目录同步出的本地缓存，禁止首跑联网下载。
- 缺少必需模型时启动失败并输出明确路径，不能静默回退到公网下载。

本方案以当前目标为准：**采用外置模型目录路线，不采用 all-in-one 含模型镜像路线**。

本文档对应当前 `feat/offline-external-models` 分支实现。构建脚本、部署脚本、compose 挂载、模型下载脚本和启动校验已按本文档落地；最终生产上线仍需在目标离线 GPU 服务器执行第 10 节验收。

## 2. 改造前问题与处理结果

原有离线部署框架方向是对的：下载模型、构建镜像、导出镜像、传输、加载、解压、启动。但改造前离线链路没有真正打通。以下问题已在当前分支处理，仍需通过第 10 节的目标服务器断网验收确认。

### 2.1 离线开关不完整

改造前 `docker-compose.offline.yml` 设置了：

```yaml
HF_OFFLINE=1
HF_ENDPOINT=https://hf-mirror.com
```

问题与处理：

- `HF_OFFLINE` 不是 HuggingFace Hub 和 Transformers 的完整离线控制。
- `HF_ENDPOINT=https://hf-mirror.com` 会让断网环境继续尝试访问公网镜像。
- 缺少 `HF_HUB_OFFLINE`、`TRANSFORMERS_OFFLINE`、`MODELSCOPE_OFFLINE` 等关键开关。
- `PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK` 目前只在部分 PaddleOCR-VL Python 模块内设置，compose 层没有全局设置；离线部署应在环境变量中显式声明，避免其他 PaddleX 入口或第三方容器绕过该设置。

### 2.2 模型产物路径与运行路径不一致

改造前 `backend/download_models.py` 主要产出：

```text
models-offline/
├── PDF-Extract-Kit-1.0/
├── MinerU2.5-2509-1.2B/
├── paddlex_cache/official_models/PaddleOCR-VL-1.5-0.9B/
├── SenseVoiceSmall/
├── Paraformer/
├── YOLO11/best.pt
└── mineru.json
```

但运行时 compose 挂载与程序实际读取路径是：

```text
/app/models
/root/.paddlex
/root/.paddleocr
/root/.cache/modelscope
/root/.cache/huggingface
/root/.cache/torch
/root/.config/Ultralytics
```

改造前 `scripts/init-models.sh` 又期望第三套旧布局：

```text
/models-external/huggingface/hub
/models-external/.paddleocr/models
/models-external/sensevoice
/models-external/paraformer
/models-external/watermark_models
```

结果是：模型已下载，但没有落到引擎实际查找的位置，断网运行仍会触发下载或失败。

当前实现中，音频代码已显式优先使用 `/app/models` 下的 FunASR 本地目录，例如 `SenseVoiceSmall`、`speech_fsmn_vad_zh-cn-16k-common-pytorch`、`Paraformer`、`punc_ct-transformer_zh-cn-common-vocab272727-pytorch`、`speech_campplus_sv_zh-cn_16k-common`。这样 `download_models.py` 产出的顶层目录可以直接被容器消费，不再依赖 ModelScope 缓存兼容布局。

当前实现中，去水印已优先使用 `/app/models/YOLO11/best.pt`，并保留 `watermark_models/yolo11x_watermark.pt` 作为兼容缓存副本。离线模式下若二者都不存在，会明确失败，不回退到 HuggingFace 下载。

### 2.3 `mineru.json` 路径失效

`download_models.py` 生成的 `mineru.json` 指向：

```json
{
  "models-dir": {
    "pipeline": "/app/models/PDF-Extract-Kit-1.0",
    "vlm": "/app/models/MinerU2.5-2509-1.2B"
  },
  "config_version": "1.3.1"
}
```

MinerU 会在 `pipeline` 根目录下继续拼接 `models/...` 子路径，所以这里必须指向 `PDF-Extract-Kit-1.0` 根目录，而不是 `PDF-Extract-Kit-1.0/models`。改造前如果离线部署只把模型挂到 `/models-external`，而没有同步或挂载到 `/app/models`，该配置会指向空目录。当前实现已统一把外置模型目录挂载到 `/app/models`，并在启动时复制 `/app/models/mineru.json` 到 `/root/mineru.json`。

### 2.4 下载清单不完整

改造前清单仍有多项 `auto_download` 或缺失项，真离线下会出问题：

- PaddleOCR-VL 需要的 `PP-DocLayoutV3`。
- 改造前本地 PaddleOCR-VL worker 传入的模型名是 `PaddleOCR-VL-1.5`，但下载脚本产出的目录是 `PaddleOCR-VL-1.5-0.9B`；若不统一命名，本地模式会查找 `/root/.paddlex/official_models/PaddleOCR-VL-1.5` 并触发下载。
- PaddleX 若触发 PP-StructureV3 相关链路，需要一批 official models。
- FunASR 基础识别和说话人分离需要 `fsmn-vad`、`ct-punc`、`campplus` 等子模型。
- 去水印功能需要 `ultralytics`、项目内置 LaMa TorchScript runner、YOLO 权重、LaMa 权重、Ultralytics 字体/配置。
- `models-offline/` 未加入 `.dockerignore`，构建上下文可能被大模型污染。

## 3. 最终架构

### 3.1 交付物

离线交付包应包含：

```text
docker-images/
├── tianshu-backend-amd64.tar.gz
├── tianshu-frontend-amd64.tar.gz
├── rustfs-amd64.tar.gz
├── redis-amd64.tar.gz                  # 可选，启用 redis profile 时必须提供
├── vllm-openai-amd64.tar.gz            # 可选，启用 vLLM 服务时必须提供
├── models-offline.tar.gz
├── docker-compose.offline.yml
├── docker-compose.yml                  # 可由 offline compose 复制生成
├── .env.example
└── deploy-offline.sh
```

说明：

- `tianshu-backend` 镜像不包含模型。
- `models-offline.tar.gz` 是唯一的模型交付物。
- Redis 和 vLLM 是否导出，取决于离线 compose 是否允许启用相关服务。

### 3.2 运行时挂载原则

推荐使用“外置目录直接挂载到真实运行路径”的方式，尽量减少启动时大规模复制。

宿主机：

```text
${OFFLINE_MODELS_PATH:-./models-offline}/
```

容器内：

```text
/app/models                         # MinerU、YOLO、LaMa、mineru.json
/root/.paddlex                      # PaddleX / PaddleOCR-VL official models
/root/.cache/modelscope             # ModelScope 兼容缓存，当前 FunASR 优先走 /app/models 顶层目录
/root/.cache/huggingface            # HuggingFace 缓存
/root/.cache/torch                  # Torch Hub / LaMa 兜底缓存
/root/.cache/watermark_models       # 当前 WatermarkRemover 默认 YOLO 缓存
/root/.config/Ultralytics           # Ultralytics 配置和字体
```

关键原则：

- 宿主机模型目录通过 `OFFLINE_MODELS_PATH` 指定，默认 `./models-offline`；容器内路径保持固定，避免各模型框架的本地路径配置发散。
- 首选模型源目录只读挂载，便于确认运行时没有新模型被写入。
- 如果某些库必须在缓存目录写 lock、索引或元数据，不要让它们联网下载；可以在部署阶段从 `models-offline/` 同步到 `runtime-model-cache/` 后以读写方式挂载运行缓存。
- 启动脚本只做检查、软链接或轻量同步，不做无条件全量复制。

## 4. 标准模型目录

`backend/download_models.py --output ./models-offline` 应产出以下标准结构：

```text
models-offline/
├── PDF-Extract-Kit-1.0/
│   └── models/
│       ├── Layout/PP-DocLayoutV2/
│       ├── MFR/unimernet_hf_small_2503/
│       ├── MFR/pp_formulanet_plus_m/
│       └── OCR/paddleocr_torch/
├── MinerU2.5-2509-1.2B/
├── YOLO11/
│   └── best.pt
├── big-lama.pt
├── mineru.json
├── manifest.json
├── paddlex_cache/
│   ├── official_models/
│   │   ├── PaddleOCR-VL-1.5-0.9B/
│   │   ├── PaddleOCR-VL-1.5 -> PaddleOCR-VL-1.5-0.9B
│   │   ├── PP-DocLayoutV3/
│   │   ├── PP-LCNet_x1_0_doc_ori/
│   │   ├── UVDoc/
│   │   └── <optional-paddlex-official-models>/
│   └── fonts/
│       └── simfang.ttf
├── paddleocr_cache/
├── SenseVoiceSmall/
├── speech_fsmn_vad_zh-cn-16k-common-pytorch/
├── Paraformer/
├── punc_ct-transformer_zh-cn-common-vocab272727-pytorch/
├── speech_campplus_sv_zh-cn_16k-common/
├── modelscope_cache/
├── huggingface_cache/
├── torch_cache/
│   └── hub/checkpoints/big-lama.pt
├── watermark_models/
│   └── yolo11x_watermark.pt
└── ultralytics_cfg/
    ├── Arial.ttf
    └── settings.json 或 settings.yaml
```

注意：

- 当前实现优先把 FunASR 模型放在 `/app/models` 顶层目录并由代码显式传本地路径；`modelscope_cache/` 只保留为兼容缓存根目录。
- `big-lama.pt` 可同时放在 `/app/models/big-lama.pt` 和 `torch_cache/hub/checkpoints/big-lama.pt`，前者配合 `LAMA_MODEL`，后者作为库默认路径兜底。
- YOLO 权重同时保留原始 `YOLO11/best.pt` 和兼容缓存名 `watermark_models/yolo11x_watermark.pt`。前者是当前默认优先路径，后者用于兼容旧缓存路径。
- PaddleOCR-VL 模型名必须统一。当前 worker 本地模式使用 `PaddleOCR-VL-1.5-0.9B`，同时在 `official_models/` 下创建 `PaddleOCR-VL-1.5` 到 `PaddleOCR-VL-1.5-0.9B` 的同目录软链接或等价副本作为兼容兜底。
- 防御性 PaddleX 模型可以先全量固化，断网验收后确认未触发再瘦身。

## 5. 必需模型清单

### 5.1 MinerU

| 模型 | 来源 | 目标路径 | 必需 |
|---|---|---|---|
| PDF-Extract-Kit-1.0 | ModelScope `OpenDataLab/PDF-Extract-Kit-1.0` | `/app/models/PDF-Extract-Kit-1.0` | 是 |
| MinerU2.5-2509-1.2B | ModelScope `opendatalab/MinerU2.5-2509-1.2B` | `/app/models/MinerU2.5-2509-1.2B` | 是 |
| mineru.json | 本地生成 | `/app/models/mineru.json` 与 `/root/mineru.json` | 是 |

`mineru.json` 必须指向容器内真实路径：

```json
{
  "models-dir": {
    "pipeline": "/app/models/PDF-Extract-Kit-1.0",
    "vlm": "/app/models/MinerU2.5-2509-1.2B"
  },
  "config_version": "1.3.1"
}
```

注意：`PDF-Extract-Kit-1.0/models` 子目录仍然必须存在；这里只是 `mineru.json` 的 `pipeline` 根路径不能多写一层 `models`。

### 5.2 PaddleOCR-VL

| 模型/资源 | 来源 | 目标路径 | 必需 |
|---|---|---|---|
| PaddleOCR-VL-1.5-0.9B | HuggingFace `PaddlePaddle/PaddleOCR-VL-1.5` | `/root/.paddlex/official_models/PaddleOCR-VL-1.5-0.9B` | 是 |
| PaddleOCR-VL-1.5 兼容名 | 本地软链接 | `/root/.paddlex/official_models/PaddleOCR-VL-1.5` | 兼容兜底 |
| PP-DocLayoutV3 | Paddle official model | `/root/.paddlex/official_models/PP-DocLayoutV3` | 是 |
| PP-LCNet_x1_0_doc_ori | Paddle official model | `/root/.paddlex/official_models/PP-LCNet_x1_0_doc_ori` | 可选 |
| UVDoc | Paddle official model | `/root/.paddlex/official_models/UVDoc` | 可选 |
| simfang.ttf | Paddle 字体资源 | `/root/.paddlex/fonts/simfang.ttf` | 可选但建议固化 |

### 5.3 FunASR / 音频

| 模型 | ModelScope id | 目标路径 | 必需 |
|---|---|---|---|
| SenseVoiceSmall | `iic/SenseVoiceSmall` | `/app/models/SenseVoiceSmall` | 是 |
| fsmn-vad | `iic/speech_fsmn_vad_zh-cn-16k-common-pytorch` | `/app/models/speech_fsmn_vad_zh-cn-16k-common-pytorch` | 是 |
| Paraformer | `iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch` | `/app/models/Paraformer` | 说话人分离必需 |
| ct-punc | `iic/punc_ct-transformer_zh-cn-common-vocab272727-pytorch` | `/app/models/punc_ct-transformer_zh-cn-common-vocab272727-pytorch` | 说话人分离必需 |
| CAM++ | `iic/speech_campplus_sv_zh-cn_16k-common` | `/app/models/speech_campplus_sv_zh-cn_16k-common` | 说话人分离必需 |

### 5.4 去水印

| 项 | 来源 | 目标路径 | 必需 |
|---|---|---|---|
| `ultralytics` | Python 依赖 | 镜像内 | 启用去水印必需 |
| LaMa TorchScript runner | 项目内置轻量 runner | 镜像内 | 启用 LaMa 必需 |
| YOLO11x `best.pt` | HuggingFace `corzent/yolo11x_watermark_detection` | `/app/models/YOLO11/best.pt`；兼容副本 `/root/.cache/watermark_models/yolo11x_watermark.pt` | 启用去水印必需 |
| LaMa `big-lama.pt` | simple-lama release 或可用镜像源 | `/app/models/big-lama.pt` | 启用 LaMa 必需 |
| Arial.ttf | Ultralytics 资源 | `/root/.config/Ultralytics/Arial.ttf` | 建议固化 |

`WatermarkRemover` 默认优先使用 `/app/models/YOLO11/best.pt`，兼容副本 `watermark_models/yolo11x_watermark.pt` 用于旧缓存路径兜底。

## 6. Compose 挂载方案

`backend` 和 `worker` 服务都应使用同一套挂载：

```yaml
volumes:
  - ${OFFLINE_MODELS_PATH:-./models-offline}:/app/models:ro
  - ${OFFLINE_MODELS_PATH:-./models-offline}/paddlex_cache:/root/.paddlex:ro
  - ${OFFLINE_MODELS_PATH:-./models-offline}/paddleocr_cache:/root/.paddleocr:ro
  - ${OFFLINE_MODELS_PATH:-./models-offline}/modelscope_cache:/root/.cache/modelscope:ro
  - ${OFFLINE_MODELS_PATH:-./models-offline}/huggingface_cache:/root/.cache/huggingface:ro
  - ${OFFLINE_MODELS_PATH:-./models-offline}/torch_cache:/root/.cache/torch:ro
  - ${OFFLINE_MODELS_PATH:-./models-offline}/watermark_models:/root/.cache/watermark_models:ro
  - ${OFFLINE_MODELS_PATH:-./models-offline}/ultralytics_cfg:/root/.config/Ultralytics:ro
```

部署时可在 `.env` 中设置：

```env
OFFLINE_MODELS_PATH=/data/tianshu/models-offline
```

也可以临时指定：

```bash
OFFLINE_MODELS_PATH=/data/tianshu/models-offline docker compose -f docker-compose.offline.yml up -d
```

如果某些库必须写入缓存，可在部署阶段从模型源同步出运行缓存，再挂载可写目录：

```yaml
  - ./runtime-model-cache/modelscope:/root/.cache/modelscope:rw
  - ./runtime-model-cache/huggingface:/root/.cache/huggingface:rw
```

这种方式仍必须配合离线环境变量和启动前校验，避免运行时把下载失败、空目录或新文件写入可写缓存后掩盖缺失问题。

## 7. 离线环境变量

`backend` 和 `worker` 必须设置：

```yaml
environment:
  - MODEL_DOWNLOAD_SOURCE=local

  # HuggingFace / Transformers
  - HF_HUB_OFFLINE=1
  - TRANSFORMERS_OFFLINE=1
  - HF_HOME=/root/.cache/huggingface
  - HF_ENDPOINT=

  # ModelScope
  - MODELSCOPE_OFFLINE=1
  - MODELSCOPE_CACHE=/root/.cache/modelscope

  # MinerU
  - MINERU_MODEL_SOURCE=local
  - MINERU_TOOLS_CONFIG_JSON=mineru.json

  # Paddle / PaddleX
  - PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True
  - PADDLEX_HOME=/root/.paddlex
  - PADDLE_HOME=/root/.paddleocr

  # Torch / LaMa
  - TORCH_HOME=/root/.cache/torch
  - LAMA_MODEL=/app/models/big-lama.pt

  # Ultralytics
  - YOLO_CONFIG_DIR=/root/.config
  - YOLO_OFFLINE=True
```

不应在离线 compose 中保留默认公网镜像地址：

```yaml
HF_ENDPOINT=${HF_ENDPOINT:-https://hf-mirror.com}
```

离线模式下要么置空，要么完全删除。

Ultralytics 会把 `YOLO_CONFIG_DIR` 当作配置父目录，并在其下使用 `Ultralytics/` 子目录；因此 `YOLO_CONFIG_DIR=/root/.config` 对应实际配置目录 `/root/.config/Ultralytics`。

`YOLO_OFFLINE` 是否被当前安装的 Ultralytics 版本识别需要实测，不能作为唯一防线。更可靠的做法是预置字体和 settings 文件，并在断网验收中确认没有外联。

## 8. 脚本改造清单

### 8.1 `.dockerignore`

补充：

```text
models-offline/
docker-images/
```

目的：

- 防止模型目录进入 Docker build context。
- 防止离线导出包被误传入构建上下文。

### 8.2 `backend/download_models.py`

改造目标：

- 产出第 4 节定义的标准 `models-offline/`。
- 所有必需模型实际下载，不再把离线必需模型标记为 `auto_download`。
- 对 FunASR 相关模型，产出 `/app/models` 顶层本地目录，并由 `SenseVoiceEngine` 显式传入本地模型路径。
- 对 YOLO 权重，同时生成 `/app/models/YOLO11/best.pt` 和兼容缓存名 `watermark_models/yolo11x_watermark.pt`。
- 生成 `manifest.json`，记录模型名、来源、目标路径、大小、校验状态。
- 生成 `mineru.json`，指向 `/app/models/...`。
- 支持 `--verify-only`，只校验目录完整性，不下载。
- 支持 `--models` 选择子集，但默认应下载完整离线清单。

至少补齐：

- PP-DocLayoutV3。
- PP-LCNet_x1_0_doc_ori、UVDoc、simfang.ttf。
- FunASR 的 fsmn-vad、ct-punc、campplus。
- LaMa `big-lama.pt`。
- Ultralytics 字体与配置。
- PaddleX 防御性 official models。

### 8.3 `scripts/init-models.sh`

建议从“复制模型”改为“校验模型”。

启动时检查：

```text
/app/models/mineru.json
/app/models/PDF-Extract-Kit-1.0/models
/app/models/MinerU2.5-2509-1.2B
/root/.paddlex/official_models/PaddleOCR-VL-1.5-0.9B
/root/.paddlex/official_models/PaddleOCR-VL-1.5
/root/.paddlex/official_models/PP-DocLayoutV3
/app/models/SenseVoiceSmall
/app/models/speech_fsmn_vad_zh-cn-16k-common-pytorch
/app/models/YOLO11/best.pt
```

行为：

- 必需路径缺失：打印明确错误并退出非 0。
- 可选路径缺失：打印 warning，不阻止启动。
- 不再提示“will be downloaded on first use”。
- 不再从旧布局 `/models-external/huggingface/hub` 等路径复制。

### 8.4 `scripts/docker-entrypoint.sh`

改造点：

- `setup_mineru_config` 从 `/app/models/mineru.json` 复制到 `/root/mineru.json`。
- `check_models` 使用真实必需路径。
- 离线模式下缺模型直接失败。
- 删除或改写“will be automatically downloaded”相关提示。

### 8.5 `docker-compose.offline.yml`

改造点：

- 通过 `OFFLINE_MODELS_PATH` 配置宿主机外置模型目录，并统一挂载到容器内真实模型路径。
- 补齐离线环境变量。
- 移除 `HF_ENDPOINT` 默认公网地址。
- 如果保留 Redis profile，构建脚本必须导出 `redis:7-alpine`。
- 当前 `docker-compose.offline.yml` 不定义 vLLM 服务，默认离线部署可不导出 vLLM 镜像。
- 如果把生产 compose 中的 vLLM 服务迁入离线 compose，或允许用户启用 vLLM profile，则必须导出 `vllm/vllm-openai` 镜像并挂载模型。

### 8.6 `scripts/build-offline.sh`

当前实现：

- 继续构建无模型 `tianshu-backend:latest`。
- 下载模型到 `${OFFLINE_MODELS_PATH:-./models-offline}`。
- 打包 `models-offline.tar.gz`。
- 导出 compose 中所有可能启用的第三方镜像。
- 支持 `PLATFORM`，镜像 tar 文件使用 `tianshu-backend-${PLATFORM}.tar.gz` 等平台后缀。

### 8.7 `scripts/deploy-offline.sh`

当前实现：

- 支持通过 `.env` 或环境变量设置 `OFFLINE_MODELS_PATH`，把 `models-offline.tar.gz` 解压到指定宿主机目录。
- 启动前运行模型完整性检查。
- 文件名按 `PLATFORM` 生成，默认 `amd64`。
- Redis 镜像 tar 存在则加载；缺失时明确提示 redis profile 不可用。
- 不在部署阶段联网拉取任何镜像。

## 9. 构建流程

### 9.1 联网准备机

```bash
# 1. 下载模型到外置目录
python3 backend/download_models.py --output ./models-offline --strict

# 也可以下载到自定义外置目录
python3 backend/download_models.py --output /data/tianshu/models-offline --strict

# 2. 校验模型完整性
python3 backend/download_models.py --output ./models-offline --verify-only --strict

# 3. 构建无模型后端镜像和前端镜像，并打包模型目录
bash scripts/build-offline.sh

# 如果模型目录不是默认值，构建时指定宿主机模型目录
OFFLINE_MODELS_PATH=/data/tianshu/models-offline bash scripts/build-offline.sh
```

构建完成后检查：

```bash
ls -lh docker-images/
tar tzf docker-images/models-offline.tar.gz | head
```

### 9.2 传输到离线服务器

```bash
rsync -avz --progress docker-images/ user@server:/opt/tianshu/
```

也可以使用现有上传脚本，但必须保证包含：

```text
models-offline.tar.gz
tianshu-backend-*.tar.gz
tianshu-frontend-*.tar.gz
rustfs-*.tar.gz
docker-compose.offline.yml
deploy-offline.sh
.env.example
```

### 9.3 离线服务器

```bash
cd /opt/tianshu
bash deploy-offline.sh

# 或指定宿主机模型目录
OFFLINE_MODELS_PATH=/data/tianshu/models-offline bash deploy-offline.sh
```

部署脚本应执行：

```bash
docker load < tianshu-backend-*.tar.gz
docker load < tianshu-frontend-*.tar.gz
docker load < rustfs-*.tar.gz
# 解压 models-offline.tar.gz 到 ${OFFLINE_MODELS_PATH:-./models-offline}，并兼容新旧 tar 结构
docker compose -f docker-compose.offline.yml up -d
```

## 10. 验收清单

必须在完全断网环境执行，且网络监控确认零外联。

基础验收：

- [ ] 后端 `/api/v1/health` 正常。
- [ ] Worker `/health` 正常。
- [ ] 日志无 `Downloading`。
- [ ] 日志无 `attempting auto-download`。
- [ ] 日志无访问 `hf-mirror.com`、`huggingface.co`、`modelscope.cn`、`paddlepaddle.org.cn`。
- [ ] 容器内关键模型路径存在。

功能验收：

- [ ] PDF pipeline 模式解析成功。
- [ ] PDF vlm-transformers 模式解析成功。
- [ ] 图片 OCR / PaddleOCR-VL 解析成功。
- [ ] 含公式 PDF 解析成功。
- [ ] 含表格 PDF 解析成功。
- [ ] DOCX / PPTX / XLSX 转换与解析成功。
- [ ] 音频基础识别成功。
- [ ] 音频说话人分离成功。
- [ ] 视频音轨转写成功。
- [ ] 视频关键帧 OCR 成功。
- [ ] 去水印功能成功，或在未启用依赖时明确提示不可用。

模型校验：

```bash
docker compose -f docker-compose.offline.yml exec worker test -f /app/models/mineru.json
docker compose -f docker-compose.offline.yml exec worker test -d /app/models/PDF-Extract-Kit-1.0/models
docker compose -f docker-compose.offline.yml exec worker test -d /app/models/MinerU2.5-2509-1.2B
docker compose -f docker-compose.offline.yml exec worker test -d /root/.paddlex/official_models/PaddleOCR-VL-1.5-0.9B
docker compose -f docker-compose.offline.yml exec worker test -d /root/.paddlex/official_models/PaddleOCR-VL-1.5
docker compose -f docker-compose.offline.yml exec worker test -d /root/.paddlex/official_models/PP-DocLayoutV3
docker compose -f docker-compose.offline.yml exec worker test -d /app/models/SenseVoiceSmall
docker compose -f docker-compose.offline.yml exec worker test -d /app/models/speech_fsmn_vad_zh-cn-16k-common-pytorch
docker compose -f docker-compose.offline.yml exec worker test -f /app/models/YOLO11/best.pt
```

出现任何下载尝试时：

1. 记录日志里的模型名、URL、调用栈。
2. 回填到模型清单。
3. 修改下载脚本补齐模型或缓存。
4. 重新打包 `models-offline.tar.gz`。
5. 回到断网环境重跑验收。

## 11. 优先级计划

### 已完成的 P0 改造

- `.dockerignore` 排除 `models-offline/`。
- `docker-compose.offline.yml` 挂载路径统一到真实运行路径。
- 补齐离线环境变量，移除 `HF_ENDPOINT` 公网默认值。
- `init-models.sh` 改为校验模型，不再使用旧布局复制。
- `download_models.py` 补齐必需模型清单。
- `mineru.json` 指向 `/app/models` 并确保 `/app/models` 挂载到 `models-offline`。
- 统一 PaddleOCR-VL 本地模式模型名：修改 worker 使用 `PaddleOCR-VL-1.5-0.9B`，或在模型目录提供 `PaddleOCR-VL-1.5` 兼容软链接/副本。
- FunASR 模型落到 `/app/models` 顶层目录，并由音频代码显式使用本地模型路径。
- YOLO 权重落到当前代码默认缓存路径，或修改去水印代码默认使用 `/app/models/YOLO11/best.pt`。

### 已完成的 P1 改造

- `download_models.py --verify-only --strict`。
- `manifest.json` 增加模型大小、来源、校验结果。
- `deploy-offline.sh` 自动校验模型目录。
- Redis 镜像随离线包导出；当前离线 compose 未定义 vLLM 服务，默认不导出 vLLM 镜像。

### P2 可后续优化

- 防御性 PaddleX 模型经断网验收后瘦身。
- CPU 离线构建与部署脚本单独补齐。
- 增加一键断网验收脚本。

## 12. 已核实的构建结果与剩余风险

### 12.1 本地构建核实

- 前端镜像构建成功：`frontend/Dockerfile`。
- 后端 `linux/amd64` 镜像构建成功：`backend/Dockerfile.offline`。
- Apple Silicon / arm64 默认构建不作为目标路径；`paddlepaddle-gpu==3.2.0` 未提供该环境可用的 arm64 GPU wheel，需使用 `--platform linux/amd64` 构建生产 GPU 镜像。

### 12.2 依赖核实

已在构建出的后端镜像内验证：

- `paddlex.create_pipeline` 可导入。
- `paddleocr.PaddleOCRVL` 可导入。
- `cv2` 使用 `4.11.0`，`numpy` 使用 `1.26.4`。
- `ultralytics` 可导入。
- `torch`、`transformers`、`funasr` 可导入。

`pip check` 仍可能报告：

```text
paddlepaddle-gpu 3.2.0 requires nvidia-nccl-cu12==2.25.1
torch 2.6.0+cu126 requires nvidia-nccl-cu12==2.21.5
```

这是 PaddlePaddle GPU 与 PyTorch CUDA wheel 对 NCCL Python 包的精确版本约束互斥。不能通过单纯 pin 一个版本同时满足两边元数据。当前镜像以实际 import 和目标 GPU 运行验收为准；生产验收必须覆盖 PaddleOCR-VL、MinerU、Torch/FunASR 和去水印路径。

## 13. 决策记录

- 采用外置模型目录，不采用含模型 all-in-one 镜像。
- 标准模型源目录默认为 `./models-offline`，可通过 `OFFLINE_MODELS_PATH` 指定宿主机外置目录。
- 容器内统一真实路径为 `/app/models`、`/root/.paddlex`、`/root/.cache/modelscope` 等。
- 离线模式禁止“首跑下载”，缺模型必须失败。
- 准备机负责下载和打包模型，离线机只负责加载镜像、解压模型、启动服务。
