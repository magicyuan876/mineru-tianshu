#!/usr/bin/env python3
"""
天枢离线模型准备脚本（宿主机裸跑，不依赖 docker）
================================================================================
把所有模型下载到统一目录（默认 /data/modelfiles），**下载路径严格对齐容器内代码的实际
加载路径**，避免"下载位置 ≠ 使用位置"的坑。

经过对引擎代码逐个审计，已规避 download_models.py 的 3 个路径不一致问题：
  1. 音频(funasr) 只认 ~/.cache/modelscope，绝不是 /app/models/SenseVoiceSmall
  2. YOLO 水印认死文件名 ~/.cache/watermark_models/yolo11x_watermark.pt
  3. LaMa 走 LAMA_MODEL 环境变量

用法：
    pip install "modelscope" "huggingface_hub" "paddlepaddle==3.0.0" "paddlex>=3.4.1"
    python prepare_offline_models.py /data/modelfiles

下载完成后，按脚本末尾打印的 docker-compose volumes / environment 配置挂载即可。
================================================================================

宿主机目录          ->  容器挂载                       ->  代码查找路径
/data/modelfiles/
  PDF-Extract-Kit-1.0/   -> /app/models/PDF-Extract-Kit-1.0/   <- mineru.json pipeline
  MinerU2.5-2509-1.2B/   -> /app/models/MinerU2.5-2509-1.2B/   <- mineru.json vlm
  mineru.json            -> /app/models/mineru.json            <- entrypoint 分发到 ~/mineru.json
  paddlex_cache/         -> /root/.paddlex/                    <- PADDLEX_HOME
  modelscope_cache/      -> /root/.cache/modelscope/           <- funasr 默认缓存
  watermark_models/      -> /root/.cache/watermark_models/     <- YOLO / LaMa(LAMA_MODEL)
"""

import os
import sys
import json
import shutil
import traceback
import urllib.request
from pathlib import Path

# ------------------------------------------------------------------------------
# 0. 目录与环境
# ------------------------------------------------------------------------------
ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else "/data/modelfiles").resolve()
PADDLEX = ROOT / "paddlex_cache"
MSCOPE = ROOT / "modelscope_cache"
WMARK = ROOT / "watermark_models"

for p in [ROOT, PADDLEX / "official_models", PADDLEX / "fonts", MSCOPE, WMARK]:
    p.mkdir(parents=True, exist_ok=True)

# 国内镜像（按需改/删）
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
# 音频：funasr 只认 MODELSCOPE_CACHE —— 关键！
os.environ["MODELSCOPE_CACHE"] = str(MSCOPE)
# PaddleX：模型落到 PADDLEX_HOME/official_models
os.environ["PADDLEX_HOME"] = str(PADDLEX)
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

_ok, _fail = [], []


def step(title):
    print("\n" + "=" * 70)
    print(f"📦 {title}")
    print("=" * 70)


# ------------------------------------------------------------------------------
# 1. MinerU pipeline + VLM —— 用 local_dir 下到精确目录（mineru.json 指向）
# ------------------------------------------------------------------------------
def dl_mineru():
    step("MinerU pipeline + VLM (ModelScope)")
    from modelscope import snapshot_download as ms
    ms("OpenDataLab/PDF-Extract-Kit-1.0", local_dir=str(ROOT / "PDF-Extract-Kit-1.0"))
    ms("opendatalab/MinerU2.5-2509-1.2B", local_dir=str(ROOT / "MinerU2.5-2509-1.2B"))


# ------------------------------------------------------------------------------
# 2. 音频 5 个 —— 必须落到 MODELSCOPE_CACHE（funasr 运行时从这里读，不是 /app/models）
# ------------------------------------------------------------------------------
def dl_audio():
    step("Audio: SenseVoice / Paraformer / VAD / Punc / CAM++ (-> modelscope_cache)")
    from modelscope import snapshot_download as ms
    for m in [
        "iic/SenseVoiceSmall",
        "iic/speech_fsmn_vad_zh-cn-16k-common-pytorch",
        "iic/punc_ct-transformer_zh-cn-common-vocab272727-pytorch",
        "iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
        "iic/speech_campplus_sv_zh-cn_16k-common",
    ]:
        print(f"   -> {m}")
        ms(m)  # 不传 local_dir，落到 $MODELSCOPE_CACHE/hub/iic/...


# ------------------------------------------------------------------------------
# 3. PaddleOCR-VL + 它真正用到的全部子模型 —— paddlex 自动拉到 PADDLEX_HOME/official_models
#    （子模型清单由 PaddleX 库的 pipeline 定义，create_pipeline 触发后最权威）
# ------------------------------------------------------------------------------
def dl_paddleocr_vl():
    step("PaddleOCR-VL pipeline + sub-models (-> paddlex_cache/official_models)")
    from paddlex import create_pipeline
    # 下载机无 GPU 用 cpu；有 GPU 可改 "gpu:0"。仅为触发模型下载。
    device = os.environ.get("DL_DEVICE", "cpu")
    _p = create_pipeline("PaddleOCR-VL-1.5-0.9B", device=device)
    del _p


# ------------------------------------------------------------------------------
# 4. YOLO 水印 —— 代码认死 ~/.cache/watermark_models/yolo11x_watermark.pt
# ------------------------------------------------------------------------------
def dl_yolo():
    step("YOLO11x watermark (-> watermark_models/yolo11x_watermark.pt)")
    from huggingface_hub import hf_hub_download
    src = hf_hub_download("corzent/yolo11x_watermark_detection", "best.pt")
    dst = WMARK / "yolo11x_watermark.pt"
    shutil.copy(src, dst)
    print(f"   -> {dst}")


# ------------------------------------------------------------------------------
# 5. 字体 + LaMa（直链）
# ------------------------------------------------------------------------------
def dl_extras():
    step("Fonts (simfang) + LaMa (big-lama.pt)")
    urllib.request.urlretrieve(
        "https://paddle-model-ecology.bj.bcebos.com/paddlex/PaddleX3.0/fonts/simfang.ttf",
        str(PADDLEX / "fonts" / "simfang.ttf"),
    )
    print(f"   -> {PADDLEX / 'fonts' / 'simfang.ttf'}")
    urllib.request.urlretrieve(
        "https://github.com/enesmsahin/simple-lama-inpainting/releases/download/v0.1.0/big-lama.pt",
        str(WMARK / "big-lama.pt"),
    )
    print(f"   -> {WMARK / 'big-lama.pt'}  (容器需设 LAMA_MODEL=/root/.cache/watermark_models/big-lama.pt)")


# ------------------------------------------------------------------------------
# 6. mineru.json —— 内部写【容器内】路径（不是宿主机路径！mineru 在容器里跑）
# ------------------------------------------------------------------------------
def gen_mineru_json():
    step("Generate mineru.json (container paths)")
    cfg = {
        "models-dir": {
            "pipeline": "/app/models/PDF-Extract-Kit-1.0/models",
            "vlm": "/app/models/MinerU2.5-2509-1.2B",
        },
        "config_version": "1.3.1",
    }
    (ROOT / "mineru.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=4))
    print(f"   -> {ROOT / 'mineru.json'}")


# ------------------------------------------------------------------------------
# 主流程
# ------------------------------------------------------------------------------
TASKS = [
    ("MinerU", dl_mineru),
    ("Audio", dl_audio),
    ("PaddleOCR-VL", dl_paddleocr_vl),
    ("YOLO", dl_yolo),
    ("Fonts/LaMa", dl_extras),
    ("mineru.json", gen_mineru_json),
]


def main():
    print(f"📁 模型根目录: {ROOT}")
    print(f"   MODELSCOPE_CACHE = {MSCOPE}")
    print(f"   PADDLEX_HOME     = {PADDLEX}")
    for name, fn in TASKS:
        try:
            fn()
            _ok.append(name)
        except Exception as e:
            _fail.append(name)
            print(f"   ❌ {name} 失败: {e}")
            traceback.print_exc()

    # ---- 汇总 + 验证提示 ----
    print("\n" + "#" * 70)
    print(f"✅ 成功: {_ok}")
    if _fail:
        print(f"❌ 失败(需单独处理): {_fail}")
    print("#" * 70)

    print(
        f"""
下一步：docker-compose 按下面挂载（worker 和 backend 服务都加），保证路径一致：

    volumes:
      - {ROOT}/PDF-Extract-Kit-1.0:/app/models/PDF-Extract-Kit-1.0:ro
      - {ROOT}/MinerU2.5-2509-1.2B:/app/models/MinerU2.5-2509-1.2B:ro
      - {ROOT}/mineru.json:/app/models/mineru.json:ro
      - {ROOT}/paddlex_cache:/root/.paddlex:rw
      - {ROOT}/modelscope_cache:/root/.cache/modelscope:rw
      - {ROOT}/watermark_models:/root/.cache/watermark_models:rw

    environment:
      - MODEL_DOWNLOAD_SOURCE=local
      - MINERU_MODEL_SOURCE=local
      - HF_OFFLINE=1
      - HF_HUB_OFFLINE=1
      - TRANSFORMERS_OFFLINE=1
      - MODELSCOPE_OFFLINE=1
      - MODELSCOPE_CACHE=/root/.cache/modelscope        # 音频(sensevoice_engine 已对齐读此变量)
      - PADDLEX_HOME=/root/.paddlex
      - PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True
      - WATERMARK_MODEL_DIR=/root/.cache/watermark_models  # YOLO(watermark_remover 已对齐读此变量)
      - LAMA_MODEL=/root/.cache/watermark_models/big-lama.pt

验证（起容器前在宿主机确认这些文件/目录存在）：
      ls {ROOT}/PDF-Extract-Kit-1.0/models/
      ls {ROOT}/MinerU2.5-2509-1.2B/*.safetensors
      ls {ROOT}/paddlex_cache/official_models/        # 应有 PaddleOCR-VL-1.5-0.9B 及若干 PP-*
      ls {ROOT}/modelscope_cache/hub/iic/             # 应有 5 个音频模型
      ls {ROOT}/watermark_models/yolo11x_watermark.pt {ROOT}/watermark_models/big-lama.pt
      cat {ROOT}/mineru.json
"""
    )
    return 1 if _fail else 0


if __name__ == "__main__":
    sys.exit(main())
