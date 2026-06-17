# 天枢 (TianShu) 离线模型下载清单(手动下载 + 挂载用)

> 用途:在**有网准备机**上把下表所有模型按"容器内目标路径"下载好,打成一个 `models/` 目录树,部署时按 §3 的挂载映射挂进容器,配合 §4 离线环境变量,即可断网运行。
>
> 来源核实:已结合源码(file:line)、MinerU / PaddleOCR-VL / FunASR 官方文档与模型库核对。
> 图例:**【必需】** 缺则对应功能崩 / **【可选】** 缺则该功能降级或禁用,不影响其他 / **【防御】** 很可能用不到,为保险下载,断网验收确认后可删。
> 体积带 ~ 为估算,标「核实」者请以准备机实际下载大小为准。
>
> ⚠️ 三个已确认的"路径/命名坑",清单已按正确值给出:
> 1. 本地 PaddleOCR-VL 目录名必须是 `PaddleOCR-VL-1.5`(不是 `-0.9B`)——`litserve_worker.py:635`。
> 2. FunASR 子模型走 modelscope 缓存,不是 `models/sensevoice`——`sensevoice_engine.py:175-182` 未向 AutoModel 传 cache_dir。
> 3. `ct-punc` 实际版本是 `vocab272727`。

---

## 0. 准备机工具

```bash
pip install "huggingface_hub[cli]" modelscope
# 国内加速(准备机下载用;部署机不需要):
export HF_ENDPOINT=https://hf-mirror.com
```

约定:准备机上建一个根目录 `models/`,下面所有命令的本地目标都放在它下面;§3 给出 `models/` 内各子目录 → 容器路径的挂载映射。

---

## 1. 必需模型(缺则功能崩)

### 1.1 MinerU —— 文档解析

| 模型 | 来源 (id) | 体积 | 容器内目标路径 |
|---|---|---|---|
| **PDF-Extract-Kit-1.0**(pipeline,整仓自包含 Layout/MFR公式/OCR) | ModelScope `OpenDataLab/PDF-Extract-Kit-1.0` | ~核实(大) | `/app/models/PDF-Extract-Kit-1.0/` |
| **MinerU2.5-2509-1.2B**(VLM/hybrid) | ModelScope `opendatalab/MinerU2.5-2509-1.2B` | ~2.3GB | `/app/models/MinerU2.5-2509-1.2B/` |

```bash
modelscope download --model OpenDataLab/PDF-Extract-Kit-1.0 \
  --local_dir models/PDF-Extract-Kit-1.0
modelscope download --model opendatalab/MinerU2.5-2509-1.2B \
  --local_dir models/MinerU2.5-2509-1.2B
```

> 配套配置 `mineru.json`(指向上面两路),内容见 §5;放 `models/mineru.json`,entrypoint 会复制到 `/root/mineru.json`。
> 离线开关:`MINERU_MODEL_SOURCE=local`。

### 1.2 PaddleOCR-VL —— OCR(离线走本地模式)

| 模型 | 来源 | 体积 | 容器内目标路径 |
|---|---|---|---|
| **PaddleOCR-VL-1.5**(VLM 主模型) | HuggingFace `PaddlePaddle/PaddleOCR-VL-1.5` | ~1.8GB 核实 | `/root/.paddlex/official_models/PaddleOCR-VL-1.5/` ⚠️名字 |
| **PP-DocLayoutV3**(版面检测,必需) | Paddle BOS(见命令) | ~150-200MB 核实 | `/root/.paddlex/official_models/PP-DocLayoutV3/` |

```bash
# 主模型(注意本地目标目录名用 PaddleOCR-VL-1.5,匹配 litserve_worker.py:635)
huggingface-cli download PaddlePaddle/PaddleOCR-VL-1.5 \
  --local-dir models/paddlex_cache/official_models/PaddleOCR-VL-1.5

# 版面检测模型(BOS tar 解压到 official_models)
mkdir -p models/paddlex_cache/official_models
wget https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-DocLayoutV3_infer.tar \
  -O /tmp/PP-DocLayoutV3.tar
tar xf /tmp/PP-DocLayoutV3.tar -C models/paddlex_cache/official_models/
# 解压后确认目录名为 PP-DocLayoutV3(若带 _infer 后缀需重命名)
```

> 若也要跑 **vLLM 模式**(生产 compose),再额外复制一份名为 `PaddleOCR-VL-1.5-0.9B` 的同模型:
> `cp -r models/paddlex_cache/official_models/PaddleOCR-VL-1.5 models/paddlex_cache/official_models/PaddleOCR-VL-1.5-0.9B`
> 离线开关:`PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True`、`PADDLEX_HOME=/root/.paddlex`。

### 1.3 音频 —— FunASR / SenseVoice

缓存到 modelscope hub。`sensevoice_engine.py` 不传 cache_dir,故必须放在 modelscope 默认缓存结构里。

| 模型 | 确切 ModelScope id | 体积 | 触发 |
|---|---|---|---|
| **SenseVoiceSmall** | `iic/SenseVoiceSmall` | ~250MB | 基础识别(`:176`) |
| **fsmn-vad** | `iic/speech_fsmn_vad_zh-cn-16k-common-pytorch` | ~13MB | **基础识别即加载**(`:179`) |
| **seaco-paraformer** | `iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch` | ~220MB | 说话人分离(`:147`) |
| **ct-punc** | `iic/punc_ct-transformer_zh-cn-common-vocab272727-pytorch` | ~29MB | 说话人分离(`:150`) |
| **CAM++ 说话人** | `iic/speech_campplus_sv_zh-cn_16k-common` | ~35MB | 说话人分离(`:151`) |

```bash
# 下到 modelscope 缓存布局(hub 子路径以准备机实跑为准,见 §6 待核实)
M=models/modelscope_cache/hub/iic
modelscope download --model iic/SenseVoiceSmall --local_dir $M/SenseVoiceSmall
modelscope download --model iic/speech_fsmn_vad_zh-cn-16k-common-pytorch --local_dir $M/speech_fsmn_vad_zh-cn-16k-common-pytorch
modelscope download --model iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch --local_dir $M/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch
modelscope download --model iic/punc_ct-transformer_zh-cn-common-vocab272727-pytorch --local_dir $M/punc_ct-transformer_zh-cn-common-vocab272727-pytorch
modelscope download --model iic/speech_campplus_sv_zh-cn_16k-common --local_dir $M/speech_campplus_sv_zh-cn_16k-common
```

> 离线开关:`MODELSCOPE_CACHE=/root/.cache/modelscope` + `MODELSCOPE_OFFLINE=1`。
> 注:基础识别只需 SenseVoiceSmall + fsmn-vad;不需要说话人分离可省后三个。

### 1.4 去水印 —— YOLO + LaMa

> 前提:`requirements.txt` 须先补 `ultralytics`、`simple-lama-inpainting`(当前缺失,功能被静默禁用)。

| 模型 | 来源 | 体积 | 容器内目标路径 |
|---|---|---|---|
| **YOLO11x 水印检测** | HuggingFace `corzent/yolo11x_watermark_detection` (`best.pt`) | ~160MB | `/root/.cache/watermark_models/yolo11x_watermark.pt`(`:81`) |
| **LaMa big-lama** | GitHub release `enesmsahin/simple-lama-inpainting v0.1.0` | 206MB | `/app/models/big-lama.pt`(配 `LAMA_MODEL`) |
| **Ultralytics Arial.ttf** | `ultralytics.com/assets/Arial.ttf` | <1MB | `/root/.config/Ultralytics/Arial.ttf` |

```bash
# YOLO(直接落到代码查找的文件名)
mkdir -p models/watermark_models
huggingface-cli download corzent/yolo11x_watermark_detection best.pt \
  --local-dir /tmp/yolo_dl
cp /tmp/yolo_dl/best.pt models/watermark_models/yolo11x_watermark.pt

# LaMa(SimpleLama 优先读 LAMA_MODEL 指向的文件)
wget https://github.com/enesmsahin/simple-lama-inpainting/releases/download/v0.1.0/big-lama.pt \
  -O models/big-lama.pt

# Ultralytics 字体(避免 YOLO 初始化时联网下载 + 版本检查)
mkdir -p models/ultralytics_cfg
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/Arial.ttf \
  -O models/ultralytics_cfg/Arial.ttf
```

> 离线开关:`LAMA_MODEL=/app/models/big-lama.pt`、`YOLO_CONFIG_DIR=/root/.config/Ultralytics`、`YOLO_OFFLINE=True`(版本相关,兜底见 §6)。

---

## 2. 可选 / 防御性模型

### 2.1 可选(缺则该子功能降级,引擎会自动跳过)

| 模型 | 来源 (BOS tar) | 体积 | 路径 | 触发 |
|---|---|---|---|---|
| PP-LCNet_x1_0_doc_ori(方向分类) | `…/paddle3.0.0/PP-LCNet_x1_0_doc_ori_infer.tar` | ~7MB | `/root/.paddlex/official_models/PP-LCNet_x1_0_doc_ori/` | `use_doc_orientation_classify=True` |
| UVDoc(图像矫正) | `…/paddle3.0.0/UVDoc_infer.tar` | ~30MB | `/root/.paddlex/official_models/UVDoc/` | `use_doc_unwarping=True` |
| simfang.ttf(可视化字体) | `paddlex/PaddleX3.0/fonts/simfang.ttf` | ~10MB | `/root/.paddlex/fonts/simfang.ttf` | 画框/可视化 |

```bash
BOS=https://paddle-model-ecology.bj.bcebos.com/paddlex
for m in PP-LCNet_x1_0_doc_ori UVDoc; do
  wget $BOS/official_inference_model/paddle3.0.0/${m}_infer.tar -O /tmp/$m.tar
  tar xf /tmp/$m.tar -C models/paddlex_cache/official_models/
done
mkdir -p models/paddlex_cache/fonts
wget $BOS/PaddleX3.0/fonts/simfang.ttf -O models/paddlex_cache/fonts/simfang.ttf
```

### 2.2 防御性(经核实 PaddleOCR-VL 链 + MinerU pipeline 都不调用,属 PP-StructureV3 链;为保险可下,断网验收确认不触发后删)

路径统一 `/root/.paddlex/official_models/<ModelName>/`,源 `…/paddle3.0.0/<ModelName>_infer.tar`:

```
PP-DocLayoutV2  PP-DocLayout_plus-L  PP-DocBlockLayout
PP-LCNet_x1_0_textline_ori  PP-LCNet_x0_25_textline_ori
PP-OCRv5_mobile_det  PP-OCRv5_mobile_rec  PP-OCRv5_server_rec  PP-OCRv4_server_seal_det
eslav_PP-OCRv5_mobile_rec  korean_PP-OCRv5_mobile_rec  latin_PP-OCRv5_mobile_rec
PP-FormulaNet_plus-L  PP-LCNet_x1_0_table_cls  PP-Chart2Table
SLANeXt_wired  SLANet_plus  RT-DETR-L_wired_table_cell_det  RT-DETR-L_wireless_table_cell_det
```

```bash
BOS=https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0
for m in PP-DocLayoutV2 PP-DocLayout_plus-L PP-DocBlockLayout \
         PP-LCNet_x1_0_textline_ori PP-LCNet_x0_25_textline_ori \
         PP-OCRv5_mobile_det PP-OCRv5_mobile_rec PP-OCRv5_server_rec PP-OCRv4_server_seal_det \
         eslav_PP-OCRv5_mobile_rec korean_PP-OCRv5_mobile_rec latin_PP-OCRv5_mobile_rec \
         PP-FormulaNet_plus-L PP-LCNet_x1_0_table_cls PP-Chart2Table \
         SLANeXt_wired SLANet_plus RT-DETR-L_wired_table_cell_det RT-DETR-L_wireless_table_cell_det; do
  wget -q $BOS/${m}_infer.tar -O /tmp/$m.tar && tar xf /tmp/$m.tar -C models/paddlex_cache/official_models/ \
    && echo "OK $m" || echo "MISS $m(可能改名/不存在,验收时确认)"
done
```

> 注:个别模型在 BOS 的确切文件名可能带版本差异;`MISS` 的项不必强求,以 §7 断网验收实际触发为准补齐。

---

## 3. 准备机目录 → 容器挂载映射

最终 `models/` 树与挂载关系(部署时单独挂载):

| 准备机目录 | 容器内挂载点 | 内容 |
|---|---|---|
| `models/PDF-Extract-Kit-1.0` | `/app/models/PDF-Extract-Kit-1.0` | MinerU pipeline |
| `models/MinerU2.5-2509-1.2B` | `/app/models/MinerU2.5-2509-1.2B` | MinerU VLM |
| `models/mineru.json` | `/app/models/mineru.json` | MinerU 配置(entrypoint 再分发) |
| `models/big-lama.pt` | `/app/models/big-lama.pt` | LaMa(配 LAMA_MODEL) |
| `models/paddlex_cache` | `/root/.paddlex` | PaddleOCR-VL + PaddleX official_models + fonts |
| `models/modelscope_cache` | `/root/.cache/modelscope` | FunASR 全部 |
| `models/watermark_models` | `/root/.cache/watermark_models` | YOLO |
| `models/ultralytics_cfg` | `/root/.config/Ultralytics` | Arial.ttf |
| `models/huggingface_cache`(若有) | `/root/.cache/huggingface` | transformers 兜底 |

> ⚠️ 现有 `docker-compose.offline.yml` 的挂载与上表**不一致**(它挂 `./models-offline→/models-external` 且 `./models/*` 为空,见离线审计)。用本清单时需把 compose 的模型挂载改成上表映射(或用你定的 all-in-one 镜像直接 COPY 到这些容器路径)。

---

## 4. 部署机离线环境变量(必设)

```bash
# HuggingFace 彻底离线(删掉 HF_ENDPOINT,不要再连 hf-mirror)
HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1
HF_HOME=/root/.cache/huggingface
# ModelScope
MODELSCOPE_OFFLINE=1
MODELSCOPE_CACHE=/root/.cache/modelscope
# MinerU
MINERU_MODEL_SOURCE=local
MINERU_TOOLS_CONFIG_JSON=mineru.json
# PaddleX
PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True
PADDLEX_HOME=/root/.paddlex
# Torch / LaMa
TORCH_HOME=/root/.cache/torch
LAMA_MODEL=/app/models/big-lama.pt
# Ultralytics
YOLO_CONFIG_DIR=/root/.config/Ultralytics
YOLO_OFFLINE=True
# 业务
MODEL_DOWNLOAD_SOURCE=local
```

---

## 5. mineru.json 内容(放 `models/mineru.json`)

```json
{
    "models-dir": {
        "pipeline": "/app/models/PDF-Extract-Kit-1.0/models",
        "vlm": "/app/models/MinerU2.5-2509-1.2B"
    },
    "config_version": "1.3.1"
}
```

---

## 6. 准备机产出后必须核实/回填的项

| 项 | 怎么确认 |
|---|---|
| ModelScope hub 子路径(`hub/iic/...` vs `hub/models/iic/...`) | 准备机跑一次 funasr,看模型实际落到 `~/.cache/modelscope` 下哪个子路径,据此调整 §1.3 目标目录 |
| PaddleOCR-VL-1.5 / MinerU / PDF-Extract-Kit 确切体积 | 下载后 `du -sh` 回填 |
| BOS 各模型 tar 解压后目录名是否带 `_infer` | 解压后 `ls`,必要时重命名为表中 `<ModelName>` |
| LaMa 是否真被 LAMA_MODEL 接管 | 跑一次 `SimpleLama()`,确认未联网下载 |
| 防御批是否真触发 | §7 断网验收 |
| nltk / tiktoken 是否触发 | §7 断网验收日志 |

---

## 7. 断网验收(把模型挂上、断网逐条跑,确认零下载)

- [ ] PDF — pipeline / vlm-transformers / hybrid
- [ ] 图片 OCR(验证 PaddleOCR-VL-1.5 + PP-DocLayoutV3)
- [ ] DOCX
- [ ] 含公式 / 含表格 PDF(验证 2.2 防御批到底用不用 → 决定删留)
- [ ] 音频基础识别(SenseVoiceSmall + fsmn-vad)
- [ ] 音频说话人分离(seaco + ct-punc + CAM++)
- [ ] 视频(关键帧 OCR + 转写)
- [ ] 去水印(ultralytics + YOLO + LaMa,且无 Arial.ttf 联网)
- [ ] 全程日志无 `Downloading` / `attempting auto-download` / 无连接超时

> 出现任何下载尝试 → 记录确切 id/URL → 回填本清单 → 补下载 → 重跑。
```
