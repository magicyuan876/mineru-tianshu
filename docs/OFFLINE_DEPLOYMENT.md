# 天枢 (TianShu) 完全离线部署方案

> 目标:整套服务在**完全断网(air-gapped)** 环境运行,所有模型与资源全部固化,运行时**零下载**。
> 本文档为方案设计稿(暂不改代码),经评审后实施。
>
> 交付形态(已定):**双镜像**
> - `tianshu-backend:base`(仅代码 + 依赖,不含模型)
> - `tianshu-backend:offline-allinone`(代码 + 依赖 + 全部模型,单镜像离线运行)
>
> 完整性策略(已定):**静态清单先行**——先按本清单一次性下载固化,再断网复跑补漏。
>
> 图例:✅ 已预下载 / 🔴 已确认遗漏(离线必崩) / ⚠️ 防御性固化(很可能用不到,断网复跑确认) / 🆕 本轮权威查证新发现
> 体积标「待实测」者需在准备机实际下载后回填。

---

## 1. 为什么现在不是"真离线"

现有 `docker-compose.offline.yml` + `scripts/init-models.sh` 实为 **"首次联网下载 + 缓存持久化"**,断网会失败。已确认硬伤:

| 问题 | 证据 | 后果 |
|---|---|---|
| 仍依赖公网镜像 | `docker-compose.offline.yml:176` `HF_ENDPOINT=https://hf-mirror.com` | 断网拉取失败 |
| 离线开关不全 | 只有 `HF_OFFLINE=1`(`:175`);无 `HF_HUB_OFFLINE`/`TRANSFORMERS_OFFLINE`/`MODELSCOPE_OFFLINE`/Paddle 离线 | modelscope、paddle、transformers 仍联网 |
| 目录布局对不上 | `init-models.sh:69-101` 期望 `/models-external/{huggingface/hub,.paddleocr/models,sensevoice,paraformer,watermark_models}`,而 `download_models.py` 产出 `PDF-Extract-Kit-1.0/`、`paddlex_cache/`、`MinerU2.5-2509-1.2B/` 等 | 复制基本空操作,模型没就位 |
| 一批模型从未预下载 | `download_models.py:72-112` 全标 `auto_download`(脚本直接 `continue` 跳过) | 运行时联网,断网崩 |
| FunASR 子模型未覆盖 | 见 §2.4 | 语音断网崩 |
| 去水印依赖与模型双缺失 | 见 §2.5 | 去水印当前其实静默禁用 |

---

## 2. 完整依赖清单(按子系统,权威核实)

### 2.1 MinerU 引擎(文档解析)

代码:`mineru_pipeline/engine.py:122` 调 `mineru.cli.common.do_parse`;backend 参数决定 pipeline / vlm / hybrid。

| 状态 | 模型/资源 | 来源 (repo id) | 体积 | 容器内路径 | 用于 | 触发 |
|---|---|---|---|---|---|---|
| ✅ | **PDF-Extract-Kit-1.0**(整仓,自包含下列子模型) | ModelScope `OpenDataLab/PDF-Extract-Kit-1.0` | ~待实测(整仓大) | `/app/models/PDF-Extract-Kit-1.0/` | pipeline | pipeline 模式 |
| ✅ | └ Layout/PP-DocLayoutV2 | (随上) | — | `…/models/Layout/PP-DocLayoutV2` | 版面分析 | — |
| ✅ | └ MFR/unimernet_hf_small_2503 | (随上) | ~770MB | `…/models/MFR/unimernet_hf_small_2503` | 公式识别 | — |
| ✅ | └ MFR/pp_formulanet_plus_m | (随上) | — | `…/models/MFR/pp_formulanet_plus_m` | 公式识别(备) | — |
| ✅ | └ OCR/paddleocr_torch | (随上) | — | `…/models/OCR/paddleocr_torch` | OCR | — |
| ✅ | **MinerU2.5-2509-1.2B**(VLM) | ModelScope `opendatalab/MinerU2.5-2509-1.2B` | ~2.32GB | `/app/models/MinerU2.5-2509-1.2B/` | vlm/hybrid | vlm-* / hybrid 模式 |
| — | mineru.json(配置) | `download_models.py` 生成 | <1MB | `/app/models/mineru.json` → 启动复制到 `/root/mineru.json` | 指向上面两组路径 | 启动 |

- 校验子路径以 `download_models.py:211-216` 为准(MinerU 3.0 实际结构)。
- 离线开关:`MINERU_MODEL_SOURCE=local`、`MINERU_TOOLS_CONFIG_JSON=mineru.json`。
- 权威:`OpenDataLab/PDF-Extract-Kit-1.0`、`opendatalab/MinerU2.5-2509-1.2B`(HF/ModelScope 同名)。PDF-Extract-Kit **自包含**,pipeline 不另外拉 PaddleX(但运行时 PaddleX 源检查仍需 `PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK` 兜底,见 2.3)。

### 2.2 PaddleOCR-VL 引擎(OCR,本地 + vLLM 两路)

代码:`paddleocr_vl/engine.py:171` `create_pipeline(...)`;`paddleocr_vl_vllm/engine.py`。权威 pipeline 配置(PaddleOCR `deploy/paddleocr_vl_docker/pipeline_config_*.yaml`)确认此链只用下列模型。

| 状态 | 模型/资源 | 来源 | 体积 | 容器内路径 | 必需性 | 触发 |
|---|---|---|---|---|---|---|
| ✅ | **PaddleOCR-VL-1.5-0.9B**(VLM 主模型) | HuggingFace `PaddlePaddle/PaddleOCR-VL-1.5` | ~1.8GB(BF16, 0.9B;待实测) | `/app/models/paddlex_cache/official_models/PaddleOCR-VL-1.5-0.9B/` | **必需** | 每次 OCR |
| 🔴🆕 | **PP-DocLayoutV3**(版面检测,RT-DETR) | Paddle BOS `paddlex/official_inference_model/paddle3.0.0/PP-DocLayoutV3_infer.tar` | ~150-200MB(待实测) | `/root/.paddlex/official_models/PP-DocLayoutV3/` | **必需**(VLM 不自带版面) | 每次 OCR |
| ⚠️🆕 | PP-LCNet_x1_0_doc_ori(方向分类) | Paddle BOS `…/PP-LCNet_x1_0_doc_ori_infer.tar` | ~7MB | `/root/.paddlex/official_models/PP-LCNet_x1_0_doc_ori/` | 可选(DocPreprocessor) | `use_doc_orientation_classify=True` |
| ⚠️🆕 | UVDoc(图像矫正) | Paddle BOS `…/UVDoc_infer.tar` | ~30MB | `/root/.paddlex/official_models/UVDoc/` | 可选(DocPreprocessor) | `use_doc_unwarping=True` |
| ⚠️🆕 | simfang.ttf(字体) | Paddle BOS `paddlex/PaddleX3.0/fonts/simfang.ttf` | ~10MB | `/root/.paddlex/fonts/simfang.ttf` | 可选(可视化输出) | 画框/可视化 |

- 本地模式与 vLLM 模式**需要相同的模型文件**;vLLM 容器(`vllm-paddleocr`)以 `--model /root/.paddlex/official_models/PaddleOCR-VL-1.5-0.9B`(`docker-compose.yml:179`)挂载只读读取。
- 代码已做本地优先:`paddleocr_vl/engine.py:156-168` 命中本地缓存则不下载;`:257-263` 方向/矫正模型缺失会自动禁用(故 2.2 两个可选项不固化也不崩,只是失能)。
- 离线开关:`PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True`(已用,`paddleocr_vl/engine.py:30`)、`PADDLE_PDX_CACHE_HOME`/`PADDLEX_HOME=/root/.paddlex`。
- 权威:PaddleOCR `docs/version3.x/pipeline_usage/PaddleOCR-VL.*.md`、`deploy/paddleocr_vl_docker/pipeline_config_vllm.yaml`。

### 2.3 PaddleX 其余 official models(`download_models.py:72-112` 的 auto_download 批)

权威结论:这批属于 **PP-StructureV3** 分步链。MinerU pipeline 用 PDF-Extract-Kit(2.1 自包含)、PaddleOCR-VL 用统一 VLM + PP-DocLayoutV3(2.2),**两条链都不调用下列模型**。

| 状态 | 模型(`<ModelName>`,Paddle BOS `…/paddle3.0.0/<Name>_infer.tar`) |
|---|---|
| ⚠️ | PP-DocLayoutV2、PP-DocLayout_plus-L、PP-DocBlockLayout |
| ⚠️ | PP-LCNet_x1_0_textline_ori、PP-LCNet_x0_25_textline_ori |
| ⚠️ | PP-OCRv5_mobile_det、PP-OCRv5_mobile_rec、PP-OCRv5_server_rec、PP-OCRv4_server_seal_det |
| ⚠️ | eslav_PP-OCRv5_mobile_rec、korean_PP-OCRv5_mobile_rec、latin_PP-OCRv5_mobile_rec |
| ⚠️ | PP-FormulaNet_plus-L、PP-LCNet_x1_0_table_cls、PP-Chart2Table、SLANeXt_wired、SLANet_plus、RT-DETR-L_wired_table_cell_det、RT-DETR-L_wireless_table_cell_det |

- 处置:**静态清单策略下防御性全量固化**到 `/root/.paddlex/official_models/`(宁多勿缺,合计估 ~2.5-3.5GB)。断网复跑(§8)确认确实不触发后,可从 all-in-one 镜像中移除以瘦身。

### 2.4 音频引擎(FunASR / SenseVoice)

代码:`sensevoice_engine.py:175-182`(基础)与 `:146-153`(说话人分离)。FunASR `AutoModel` 会把别名解析为下列确切 ModelScope id 并自动下载。缓存路径 `~/.cache/modelscope/hub/<owner>/<model>/`(modelscope≥1.34)。

| 状态 | 模型 | 确切 ModelScope id | 体积 | 用于 | 触发(代码) |
|---|---|---|---|---|---|
| ✅ | SenseVoiceSmall | `iic/SenseVoiceSmall` | ~250MB | 基础识别 | `:176` `model=` |
| 🔴 | fsmn-vad | `iic/speech_fsmn_vad_zh-cn-16k-common-pytorch` | ~13MB | **基础识别即加载** | `:179` `vad_model="fsmn-vad"` |
| ✅ | seaco-paraformer | `iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch` | ~220MB | 说话人分离 | `:147` `model=` |
| 🔴🆕 | ct-punc | `iic/punc_ct-transformer_zh-cn-common-vocab272727-pytorch` | ~29MB | 说话人分离 | `:150` `punc_model="ct-punc"` |
| 🔴 | CAM++ 说话人 | `iic/speech_campplus_sv_zh-cn_16k-common` | ~35MB | 说话人分离 | `:151` `spk_model=` |

- 注意 `ct-punc` 实际解析为 **vocab272727** 版本(此前文档写的 `punc_ct-transformer-zh-cn-common-pytorch` 有误,已更正)。
- 离线开关:预置 `MODELSCOPE_CACHE` + 设 `MODELSCOPE_OFFLINE=1`(版本相关,部分版本需配合代码 `local_files_only=True`)。**必须保证上述 5 个缓存就位**。
- 权威:FunASR `funasr/auto/auto_model.py` 别名解析。

### 2.5 去水印引擎(YOLO + LaMa)

代码:`remove_watermark/watermark_remover.py`。当前两处依赖包**缺失**,功能实为静默禁用(`:15,22` 的 `*_AVAILABLE` 守卫)。

| 状态 | 项 | 来源 | 体积 | 缓存/路径 | 触发 | 离线开关 |
|---|---|---|---|---|---|---|
| 🔴 | `ultralytics`(包) | requirements 缺失 | — | — | `import` | 加入 requirements |
| 🔴 | `simple-lama-inpainting`(包) | requirements 缺失 | — | — | `import` | 加入 requirements |
| ✅(路径错) | YOLO11x `best.pt` | HuggingFace `corzent/yolo11x_watermark_detection` | ~160MB | 代码找 `~/.cache/watermark_models/yolo11x_watermark.pt`(`:78,81`);预下却落 `/app/models/YOLO11`(`download_models.py`) | 检测水印 | 统一路径 / 改默认 `model_path` 指本地文件 |
| 🔴 | LaMa `big-lama.pt` | GitHub release `enesmsahin/simple-lama-inpainting v0.1.0/big-lama.pt`(或 HF 镜像) | 206MB | `$TORCH_HOME/hub/checkpoints/big-lama.pt`,或 `LAMA_MODEL` 指定 | `SimpleLama()`(`:133`) | **设 `LAMA_MODEL=/app/models/big-lama.pt`** |
| 🔴🆕 | Ultralytics `Arial.ttf` + 版本检查 | `ultralytics.com/assets/Arial.ttf` | <1MB | `~/.config/Ultralytics/`(`YOLO_CONFIG_DIR` 可改) | `YOLO()` 初始化 | 预置字体 + `settings offline=True` / 断网静默降级 |

- 权威:`simple_lama_inpainting` 源码(`LAMA_MODEL` 优先 + 默认 URL);Ultralytics 文档(settings/offline、`YOLO_CONFIG_DIR`)。

### 2.6 视频引擎

`video_engines/`:关键帧用 OpenCV/scenedetect/imagehash(**无模型**);关键帧 OCR 复用 2.2 PaddleOCR-VL;音轨转写复用 2.4。ffmpeg 为系统包(镜像已装)。**无独立模型下载。**

### 2.7 Python 库运行时下载风险

| 状态 | 库 | 风险 | 缓存路径 | 离线开关 |
|---|---|---|---|---|
| — | transformers / huggingface_hub | from_pretrained / hf_hub_download | `~/.cache/huggingface/hub/` | `HF_HUB_OFFLINE=1`、`TRANSFORMERS_OFFLINE=1`、`HF_HOME` |
| ⚠️ | nltk | 若用到则下数据包 | `~/nltk_data/` 或 `NLTK_DATA` | 预下 + 设 `NLTK_DATA`(断网复跑确认是否触发) |
| ⚠️ | tiktoken | 下编码文件 | `TIKTOKEN_CACHE_DIR` | 预置缓存 + 设 `TIKTOKEN_CACHE_DIR`(断网复跑确认) |
| — | markitdown | 仅处理网络 URI 时 | — | 业务上不传外链即可 |

### 2.8 系统级资源(镜像构建时已含,无需运行时下载)

ffmpeg、antiword、pandoc、poppler-utils、LibreOffice、中文字体(`fonts-noto-cjk` 等)——见 `Dockerfile.offline:30-71`。✅ 无运行时联网。

### 2.9 第三方镜像(需 `docker save` 一并交付)

| 镜像 | 用途 | 备注 |
|---|---|---|
| `vllm/vllm-openai:nightly` | PaddleOCR-VL / MinerU vLLM 推理 | 模型走只读挂载,镜像本身需离线交付 |
| `redis:7-alpine` | 可选队列 | profile redis |
| `rustfs/rustfs:latest` | 对象存储 | 存图片 |
| `tianshu-frontend:latest` | 前端 | 自建 |

---

## 3. 必须先修的代码 / 配置硬伤

实施阶段改动清单(本节先列,评审后执行):

1. **`backend/requirements.txt`**:补 `ultralytics`、`simple-lama-inpainting`(否则去水印永远禁用)。
2. **`backend/download_models.py`**:
   - 新增 2.4 的 🔴:`fsmn-vad`、`ct-punc`(vocab272727)、`campplus` → 固化到 modelscope 缓存。
   - 新增 2.2 的 🔴 `PP-DocLayoutV3`(及可选 doc_ori / UVDoc / simfang.ttf)→ `/root/.paddlex/official_models/`。
   - 新增 2.5 的 LaMa `big-lama.pt` 预下载;Paraformer 改 `required: True`(若需说话人分离)。
   - 2.3 防御性批:从"标记跳过"改为"实际下载"(静态策略),并加注释标明可能未用。
3. **YOLO 路径统一**(`watermark_remover.py`):默认 `model_path` 指 `/app/models/YOLO11/best.pt`,或预下落到 `~/.cache/watermark_models/yolo11x_watermark.pt`。
4. **`scripts/init-models.sh`**:重写复制逻辑对齐 §4(base 路线);all-in-one 镜像直接 `COPY`,跳过此脚本。
5. **离线开关补全**:见 §6。

---

## 4. 统一模型目录布局规范(单一事实来源)

准备机产出标准 `models/`,base 与 all-in-one 共用:

```
models/
├── PDF-Extract-Kit-1.0/                       # MinerU pipeline(自包含)
├── MinerU2.5-2509-1.2B/                        # MinerU VLM
├── SenseVoiceSmall/                           # (也可只放 modelscope_cache,二选一)
├── Paraformer/
├── YOLO11/best.pt                             # 水印检测
├── big-lama.pt                                # LaMa(配合 LAMA_MODEL)
├── mineru.json                                # download_models.py 生成
├── paddlex_cache/                             # → /root/.paddlex
│   ├── official_models/
│   │   ├── PaddleOCR-VL-1.5-0.9B/
│   │   ├── PP-DocLayoutV3/                    # 🔴 必需
│   │   ├── PP-LCNet_x1_0_doc_ori/            # 可选
│   │   ├── UVDoc/                             # 可选
│   │   └── <2.3 防御性批…>                    # ⚠️ 断网复跑后可删
│   └── fonts/simfang.ttf
├── modelscope_cache/                          # → /root/.cache/modelscope
│   └── hub/iic/
│       ├── SenseVoiceSmall/
│       ├── speech_fsmn_vad_zh-cn-16k-common-pytorch/        # 🔴
│       ├── speech_seaco_paraformer_large_..._vocab8404-pytorch/
│       ├── punc_ct-transformer_zh-cn-common-vocab272727-pytorch/   # 🔴
│       └── speech_campplus_sv_zh-cn_16k-common/             # 🔴
├── huggingface_cache/                         # → /root/.cache/huggingface
├── torch_cache/hub/checkpoints/big-lama.pt    # → /root/.cache/torch(若不用 LAMA_MODEL)
└── ultralytics_cfg/Arial.ttf                  # → /root/.config/Ultralytics
```

> ModelScope 实际子路径(`hub/iic/...` vs `hub/models/iic/...`)随版本不同,以准备机实跑产出为准回填。

---

## 5. 固化策略:双镜像

### 5.1 `tianshu-backend:base`(无模型)
系统依赖(CUDA runtime、ffmpeg、LibreOffice、字体)+ Python 依赖(含新增 `ultralytics`、`simple-lama-inpainting`)+ 后端代码。沿用 `Dockerfile.offline` 依赖层。配合**外部模型卷**(`./models-offline`)部署。

### 5.2 `tianshu-backend:offline-allinone`(含模型)
在 `base` 上 `COPY` 整个标准 `models/` 进镜像,写好离线 ENV。单镜像 `docker load` 即可断网运行。代价:镜像 ~20-30GB(待实测)。草案 `backend/Dockerfile.offline.allinone`:

```dockerfile
FROM tianshu-backend:base AS allinone
COPY models/PDF-Extract-Kit-1.0   /app/models/PDF-Extract-Kit-1.0
COPY models/MinerU2.5-2509-1.2B   /app/models/MinerU2.5-2509-1.2B
COPY models/YOLO11                /app/models/YOLO11
COPY models/big-lama.pt           /app/models/big-lama.pt
COPY models/mineru.json           /app/models/mineru.json
COPY models/paddlex_cache         /root/.paddlex
COPY models/modelscope_cache      /root/.cache/modelscope
COPY models/huggingface_cache     /root/.cache/huggingface
COPY models/ultralytics_cfg       /root/.config/Ultralytics
# YOLO 按最终方案:或 COPY 到 ~/.cache/watermark_models,或依赖 /app/models/YOLO11/best.pt
```

> vLLM 容器是第三方镜像,模型走只读挂载、镜像本身 `docker save` 交付(见 2.9)。

---

## 6. 全套离线环境变量(写入 Dockerfile.offline 的 ENV + compose)

```bash
# HuggingFace —— 彻底离线(不要再指向 hf-mirror)
HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1
HF_HOME=/root/.cache/huggingface
# HF_ENDPOINT 置空,避免误连公网

# ModelScope —— 离线
MODELSCOPE_OFFLINE=1
MODELSCOPE_CACHE=/root/.cache/modelscope

# MinerU —— 本地模型 + 本地配置
MINERU_MODEL_SOURCE=local
MINERU_TOOLS_CONFIG_JSON=mineru.json

# PaddleX / PaddleOCR —— 跳过源检查 + 预置 official_models
PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True
PADDLEX_HOME=/root/.paddlex
PADDLE_HOME=/root/.paddleocr

# Torch Hub + LaMa
TORCH_HOME=/root/.cache/torch
LAMA_MODEL=/app/models/big-lama.pt          # 🆕 simple_lama 优先用此路径

# Ultralytics —— 禁联网检查
YOLO_CONFIG_DIR=/root/.config/Ultralytics   # 🆕 预置 Arial.ttf 于此
YOLO_OFFLINE=True                            # 🆕(版本相关,配合 settings offline=True)

# 业务侧
MODEL_DOWNLOAD_SOURCE=local
```

> 待实测:`MODELSCOPE_OFFLINE` / `YOLO_OFFLINE` 在当前版本是否生效;若不生效,改走"预置缓存 + `local_files_only` / settings.yaml"。

---

## 7. 构建与交付流程(三阶段)

### 阶段一:准备机(有网 + GPU)产出标准模型目录
1. 构建 `base` 镜像。
2. 运行改造后的 `download_models.py`(覆盖 2.1-2.5 全部 + 2.3 防御批),产出 §4 标准 `models/`。
3. 单独预取易漏项:LaMa(跑一次 `SimpleLama()` 确认 `big-lama.pt` 落点)、Ultralytics `Arial.ttf`、必要时 nltk/tiktoken。
4. `docker pull` 第三方镜像(2.9)。
5. **回填本文档所有「待实测」体积/路径**。

### 阶段二:固化与打包
1. 构建 `tianshu-backend:offline-allinone`。
2. `docker save` 导出:base、allinone、frontend、vllm、redis、rustfs。
3. base 路线另打包 `models/` 为 tar。

### 阶段三:离线机部署
1. `docker load` 全部镜像。
2. all-in-one:直接 `up`,无需模型卷。
3. base:解压模型 tar 到 `./models-offline`,按 compose 挂载。
4. 设全套离线 ENV(§6),`HF_ENDPOINT` 置空。

---

## 8. 断网验收清单(交付前必过)

在**完全断网**环境逐项跑通,网络监控确认**零外联**:

- [ ] PDF — pipeline 模式(验证 PDF-Extract-Kit 自包含)
- [ ] PDF — vlm-transformers 模式
- [ ] PDF — hybrid / vlm-vllm(若启用 vLLM)
- [ ] 图片(png/jpg)OCR(验证 PaddleOCR-VL + PP-DocLayoutV3)
- [ ] DOCX 原生解析
- [ ] 含公式 / 含表格 PDF(关键:验证 2.3 防御批到底用不用)
- [ ] 音频(基础识别,验证 SenseVoice + fsmn-vad)
- [ ] 音频(说话人分离,验证 seaco + ct-punc + CAM++)
- [ ] 视频(关键帧 OCR + 音频转写)
- [ ] 去水印(验证 ultralytics + YOLO + LaMa + 无 Arial.ttf 联网)
- [ ] 全程日志无 "Downloading" / "attempting auto-download" / 无连接超时

> 出现任何下载尝试 → 记录确切模型/URL → 回填 §2 → 补固化 → 重跑。这是静态清单策略的兜底闭环。

---

## 9. 待确认项(准备机实测回填)

| 项 | 说明 |
|---|---|
| 2.3 防御批是否真触发 | 静态全量固化,断网复跑确认;不触发则删以瘦身 |
| 各模型确切体积 | PDF-Extract-Kit 整仓、PaddleOCR-VL-1.5、MinerU VLM、PaddleX 各项 |
| ModelScope 缓存子路径结构 | `hub/iic/...` vs `hub/models/iic/...`,以实跑为准 |
| LaMa 实际落点 | `SimpleLama()` 跑一次抓取,确认 `LAMA_MODEL` 是否被尊重 |
| PaddleX / FunASR / Ultralytics 离线开关有效性 | `PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK`、`MODELSCOPE_OFFLINE`、`YOLO_OFFLINE` |
| nltk / tiktoken 是否触发 | 断网复跑观察 |
| all-in-one 镜像体积 | 预估 20-30GB |

---

## 10. 实施任务清单(评审通过后执行)

1. [ ] `requirements.txt` 补 `ultralytics`、`simple-lama-inpainting`
2. [ ] `download_models.py` 扩展:2.4 🔴 + 2.2 🔴(PP-DocLayoutV3 等)+ LaMa + Paraformer 强制 + 2.3 防御批实下
3. [ ] 统一 YOLO 路径(改代码或改下载落点)
4. [ ] 新增 `backend/Dockerfile.offline.allinone`
5. [ ] `Dockerfile.offline` / compose 写入全套离线 ENV(§6)
6. [ ] 重写 `scripts/init-models.sh` 对齐 §4(base 路线)
7. [ ] 准备机产出标准 `models/`,回填本文档待实测项(§9)
8. [ ] 断网验收(§8),闭环补漏
```
