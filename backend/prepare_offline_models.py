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
ULTRA = ROOT / "ultralytics_cfg"

for p in [ROOT, PADDLEX / "official_models", PADDLEX / "fonts", MSCOPE, WMARK, ULTRA]:
    p.mkdir(parents=True, exist_ok=True)

# 国内镜像（按需改/删）
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
# 音频：funasr 只认 MODELSCOPE_CACHE —— 关键！
os.environ["MODELSCOPE_CACHE"] = str(MSCOPE)
# PaddleX：模型落到 PADDLEX_HOME/official_models
os.environ["PADDLEX_HOME"] = str(PADDLEX)
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

_ok, _fail = [], []
# 收集"墙外源、下载失败需手动放置"的文件，末尾统一给出放置指引
_manual = []


def _fetch_or_keep(dst, url, hint=""):
    """已存在则跳过；否则尝试下载；失败不抛异常，仅登记为待手动放置
    （避免一两个 HF/github 墙外文件中断整个离线准备流程）。"""
    if dst.exists() and dst.stat().st_size > 0:
        print(f"   ✓ 已就位: {dst}")
        return True
    try:
        urllib.request.urlretrieve(url, str(dst))
        print(f"   -> 下载完成: {dst}")
        return True
    except Exception as e:
        print(f"   ⚠️ 下载失败（{e.__class__.__name__}），需手动放置: {dst}")
        _manual.append((str(dst), url))
        return False


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
    # 改用 ModelScope 直接下载完整仓库（不依赖 create_pipeline，规避 "pipeline does not exist" 报错）。
    # 引擎 paddleocr_vl/engine.py 离线时读 PADDLEX_HOME/official_models/<model_name>，
    # 默认 model_name="PaddleOCR-VL-1.5-0.9B"，所以直接把仓库下到该目录，引擎 local_cache 逻辑会直接用上，
    # 运行时无需联网、无需 create_pipeline 触发下载。
    step("PaddleOCR-VL (ModelScope 完整仓库 -> official_models/PaddleOCR-VL-1.5-0.9B)")
    from modelscope import snapshot_download as ms

    target = PADDLEX / "official_models" / "PaddleOCR-VL-1.5-0.9B"
    ms("PaddlePaddle/PaddleOCR-VL", local_dir=str(target))
    print(f"   -> {target}")
    print("   ⚠️ 若运行时 paddlex 仍报缺子模型（如 PP-DocLayoutV2），说明该仓库未含全部 pipeline 子模型，")
    print("      需在能联网的机器上用 create_pipeline('PaddleOCR-VL') 触发补全 official_models 后整体拷贝。")


# ------------------------------------------------------------------------------
# 4. YOLO 水印 —— 代码认死 ~/.cache/watermark_models/yolo11x_watermark.pt
# ------------------------------------------------------------------------------
def dl_yolo():
    # YOLO 水印模型在 HuggingFace（墙外）。下载机连不上 HF 时，请在能上网的机器下好后手动放置：
    #   https://hf-mirror.com/corzent/yolo11x_watermark_detection/resolve/main/best.pt
    #   -> watermark_models/yolo11x_watermark.pt （文件名必须如此，引擎 watermark_remover.py 认死）
    step("YOLO11x watermark (-> watermark_models/yolo11x_watermark.pt)")
    _fetch_or_keep(
        WMARK / "yolo11x_watermark.pt",
        "https://hf-mirror.com/corzent/yolo11x_watermark_detection/resolve/main/best.pt",
    )


# ------------------------------------------------------------------------------
# 5. 字体 + LaMa（直链）
# ------------------------------------------------------------------------------
def dl_extras():
    step("Fonts (simfang, 百度源必下) + LaMa + Arial（github 墙外，支持手动放置）")
    # simfang：百度 bcebos 源，国内可达，正常能下成功
    _fetch_or_keep(
        PADDLEX / "fonts" / "simfang.ttf",
        "https://paddle-model-ecology.bj.bcebos.com/paddlex/PaddleX3.0/fonts/simfang.ttf",
    )
    # LaMa：github releases（墙外）。容器需设 LAMA_MODEL=/root/.cache/watermark_models/big-lama.pt
    _fetch_or_keep(
        WMARK / "big-lama.pt",
        "https://github.com/enesmsahin/simple-lama-inpainting/releases/download/v0.1.0/big-lama.pt",
    )
    # Arial.ttf：ultralytics（github，墙外）。水印 YOLO 绘制时需要，容器挂到 /root/.config/Ultralytics/
    _fetch_or_keep(
        ULTRA / "Arial.ttf",
        "https://github.com/ultralytics/assets/releases/download/v0.0.0/Arial.ttf",
    )


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

    if _manual:
        print("\n" + "!" * 70)
        print("⚠️ 以下文件下载失败（多为 HF/github 墙外源不可达），需在能上网的机器下好后手动放置：")
        for dst, url in _manual:
            print(f"   • 目标: {dst}")
            print(f"     来源: {url}")
        print("   放好后无需重跑下载，再次执行本脚本会把它们校验为 ✓ 已就位。")
        print("   ⚠️ YOLO 文件名必须是 yolo11x_watermark.pt（引擎认死）。")
        print("   ⚠️ LaMa github 直链国内可加代理前缀: https://mirror.ghproxy.com/")
        print("!" * 70)

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
      - {ROOT}/ultralytics_cfg:/root/.config/Ultralytics:rw

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
      - YOLO_CONFIG_DIR=/root/.config/Ultralytics              # ultralytics 字体 Arial.ttf 目录

验证（起容器前在宿主机确认这些文件/目录存在）：
      ls {ROOT}/PDF-Extract-Kit-1.0/models/
      ls {ROOT}/MinerU2.5-2509-1.2B/*.safetensors
      ls {ROOT}/paddlex_cache/official_models/        # 应有 PaddleOCR-VL-1.5-0.9B 及若干 PP-*
      ls {ROOT}/modelscope_cache/hub/iic/             # 应有 5 个音频模型
      ls {ROOT}/watermark_models/yolo11x_watermark.pt {ROOT}/watermark_models/big-lama.pt
      ls {ROOT}/ultralytics_cfg/Arial.ttf
      cat {ROOT}/mineru.json
"""
    )
    return 1 if _fail else 0


if __name__ == "__main__":
    sys.exit(main())
