#!/usr/bin/env python3
"""
模型预下载脚本 - Tianshu (Runtime Auto-Download for Paddle + Pre-download for others)

策略说明:
1. MinerU / YOLO / Audio / PaddleOCR-VL 模型: 使用此脚本预先下载到 ./models 目录。
2. 其他普通 PaddleOCR / PaddleX 模型:  设置为 auto_download。
   - 它们将在容器运行时由引擎自动下载。
   - 数据会持久化保存到宿主机的 ./models/paddlex_cache 和 ./models/paddleocr_cache 目录中。
   - (通过 docker-compose.yml 的 /root/.paddlex 和 /root/.paddleocr 挂载实现)
3. 配置文件生成:
   - 自动在模型目录生成 magic-pdf.json，供 entrypoint 脚本分发到各服务。
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from loguru import logger

# 配置日志
logger.remove()
logger.add(sys.stdout, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")

# ==============================================================================
# 模型配置清单
# ==============================================================================
MODELS = {
    # -------------------------------------------------------------------------
    # 1. MinerU 核心模型 (需要预下载)
    # -------------------------------------------------------------------------
    "mineru_pipeline": {
        "name": "MinerU Pipeline (PDF-Extract-Kit)",
        "repo_id": "OpenDataLab/PDF-Extract-Kit-1.0",
        "source": "modelscope",
        "target_dir": "PDF-Extract-Kit-1.0",
        "description": "PDF OCR, Layout Analysis models (For 'pipeline' mode)",
        "required": True
    },
    "mineru_vlm": {
        "name": "MinerU 2.5 VLM (1.2B)",
        "model_id": "opendatalab/MinerU2.5-2509-1.2B",
        "source": "modelscope",
        "target_dir": "MinerU2.5-2509-1.2B",
        "description": "Vision Language Model (For 'vlm-auto-engine' & 'hybrid-auto-engine')",
        "required": True
    },

    # -------------------------------------------------------------------------
    # 2. PaddleX / PaddleOCR 模型 
    # -------------------------------------------------------------------------
    
    # --- 多模态文档解析 (VLM) - 强制预下载供 vLLM 服务使用 ---
    "paddleocr_vl_1_5": {
        "name": "PaddleOCR-VL-1.5-0.9B",
        "repo_id": "PaddlePaddle/PaddleOCR-VL-1.5",
        "source": "huggingface",
        "target_dir": "paddlex_cache/official_models/PaddleOCR-VL-1.5-0.9B",
        "description": "Pre-downloaded for vLLM Server to avoid crash loops",
        "required": True
    },
    "paddleocr_vl_0_9": {
        "name": "PaddleOCR-VL-0.9B",
        "repo_id": "PaddlePaddle/PaddleOCR-VL",
        "source": "huggingface",
        "target_dir": "paddlex_cache/official_models/PaddleOCR-VL-0.9B",
        "description": "Pre-downloaded for vLLM Server to avoid crash loops",
        "required": False
    },

    # --- 版面分析 (Layout) - 运行时自动下载 ---
    "pp_doclayout_v3": {
        "name": "PP-DocLayoutV3",
        "auto_download": True,
        "description": "Runtime auto-download to ./models/paddlex_cache/",
        "required": False
    },
    "pp_doclayout_v2": {
        "name": "PP-DocLayoutV2",
        "auto_download": True, 
        "required": False
    },
    "pp_doclayout_plus_l": {
        "name": "PP-DocLayout_plus-L",
        "auto_download": True,
        "required": False
    },
    "pp_docblocklayout": {
        "name": "PP-DocBlockLayout",
        "auto_download": True,
        "required": False
    },

    # --- 文档矫正/方向分类 - 运行时自动下载 ---
    "pp_lcnet_doc_ori": {
        "name": "PP-LCNet_x1_0_doc_ori",
        "auto_download": True,
        "description": "Runtime auto-download to ./models/paddlex_cache/",
        "required": False
    },
    "pp_lcnet_textline_ori": {
        "name": "PP-LCNet_x1_0_textline_ori",
        "auto_download": True,
        "required": False
    },
    "pp_lcnet_x0_25_textline_ori": {
        "name": "PP-LCNet_x0_25_textline_ori",
        "auto_download": True,
        "required": False
    },
    "uvdoc": {
        "name": "UVDoc (Doc Unwarping)",
        "auto_download": True,
        "description": "Runtime auto-download to ./models/paddlex_cache/",
        "required": False
    },

    # --- 通用 OCR (PP-OCRv5) - 运行时自动下载 ---
    "pp_ocrv5_det": {
        "name": "PP-OCRv5_mobile_det",
        "auto_download": True,
        "required": False
    },
    "pp_ocrv5_rec": {
        "name": "PP-OCRv5_mobile_rec",
        "auto_download": True,
        "required": False
    },
    "pp_ocrv5_server_rec": {
        "name": "PP-OCRv5_server_rec",
        "auto_download": True,
        "required": False
    },
    "pp_ocrv4_server_seal_det": {
        "name": "PP-OCRv4_server_seal_det",
        "auto_download": True,
        "required": False
    },

    # --- 多语言 OCR - 运行时自动下载 ---
    "eslav_pp_ocrv5_mobile_rec": {
        "name": "eslav_PP-OCRv5_mobile_rec",
        "auto_download": True,
        "required": False
    },
    "korean_pp_ocrv5_mobile_rec": {
        "name": "korean_PP-OCRv5_mobile_rec",
        "auto_download": True,
        "required": False
    },
    "latin_pp_ocrv5_mobile_rec": {
        "name": "latin_PP-OCRv5_mobile_rec",
        "auto_download": True,
        "required": False
    },

    # --- 公式/表格识别 - 运行时自动下载 ---
    "pp_formulanet": {
        "name": "PP-FormulaNet_plus-L",
        "auto_download": True,
        "required": False
    },
    "pp_lcnet_table_cls": {
        "name": "PP-LCNet_x1_0_table_cls",
        "auto_download": True,
        "required": False
    },
    "pp_chart2table": {
        "name": "PP-Chart2Table",
        "auto_download": True,
        "required": False
    },
    "slanext_wired": {
        "name": "SLANeXt_wired",
        "auto_download": True,
        "required": False
    },
    "slanet_plus": {
        "name": "SLANet_plus",
        "auto_download": True,
        "required": False
    },
    "rtdetr_wired": {
        "name": "RT-DETR-L_wired_table_cell_det",
        "auto_download": True,
        "required": False
    },
    "rtdetr_wireless": {
        "name": "RT-DETR-L_wireless_table_cell_det",
        "auto_download": True,
        "required": False
    },

    # -------------------------------------------------------------------------
    # 3. 其他模型 (需要预下载)
    # -------------------------------------------------------------------------
    "sensevoice": {
        "name": "SenseVoice Audio Recognition",
        "model_id": "iic/SenseVoiceSmall",
        "source": "modelscope",
        "target_dir": "SenseVoiceSmall",
        "description": "Multi-language speech recognition model",
        "required": True
    },
    "paraformer": {
        "name": "Paraformer Speaker Diarization",
        "model_id": "iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
        "source": "modelscope",
        "target_dir": "Paraformer",
        "description": "Speaker diarization and VAD model",
        "required": False
    },
    "yolo11": {
        "name": "YOLO11x Watermark Detection",
        "repo_id": "corzent/yolo11x_watermark_detection",
        "filename": "best.pt",
        "source": "huggingface",
        "target_dir": "YOLO11",
        "description": "Watermark detection model",
        "required": False
    },
    "lama": {
        "name": "LaMa Watermark Inpainting",
        "auto_download": True,
        "description": "Will be downloaded by simple_lama_inpainting on first use",
        "required": False
    }
}

# ==============================================================================
# 下载函数
# ==============================================================================

def download_from_huggingface(repo_id, target_dir, filename=None):
    """从 HuggingFace 下载"""
    try:
        from huggingface_hub import snapshot_download, hf_hub_download
        
        # 配置国内镜像
        hf_endpoint = os.getenv("HF_ENDPOINT", "https://hf-mirror.com")
        os.environ.setdefault("HF_ENDPOINT", hf_endpoint)
        
        if filename:
            logger.info(f"    Downloading file: {filename}")
            path = hf_hub_download(
                repo_id=repo_id, 
                filename=filename, 
                local_dir=str(target_dir), 
                local_dir_use_symlinks=False, 
                resume_download=True
            )
        else:
            logger.info(f"    Downloading repository: {repo_id}")
            path = snapshot_download(
                repo_id=repo_id, 
                local_dir=str(target_dir), 
                local_dir_use_symlinks=False, 
                resume_download=True
            )
        return path
    except Exception as e:
        logger.error(f"    ❌ Download failed: {e}")
        return None

def download_from_modelscope(model_id, target_dir):
    """从 ModelScope 下载"""
    try:
        from modelscope import snapshot_download
        
        logger.info(f"    Downloading from ModelScope: {model_id}")
        path = snapshot_download(
            model_id, 
            local_dir=str(target_dir), 
            revision="master"
        )
        return path
    except Exception as e:
        logger.error(f"    ❌ Download failed: {e}")
        return None

# ==============================================================================
# 验证与辅助函数
# ==============================================================================

def verify_model_files(path, model_name):
    """验证下载是否完整"""
    path_obj = Path(path)
    if not path_obj.exists(): return False

    # 1. MinerU Pipeline
    if model_name == "mineru_pipeline":
        if not (any(path_obj.rglob("*.safetensors")) or any(path_obj.rglob("*.bin"))):
            if (path_obj / "models").exists(): return True
            logger.warning(f"    ⚠️  No model files in {path}")
            return False
            
    # 2. MinerU VLM
    elif model_name == "mineru_vlm":
        if not any(path_obj.rglob("*.safetensors")):
            logger.warning(f"    ⚠️  No safetensors found in {path}")
            return False
    
    # 3. PaddleOCR-VL VLM 模型验证
    elif model_name in ["paddleocr_vl_1_5", "paddleocr_vl_0_9"]:
        if not any(path_obj.rglob("*.safetensors")):
            logger.warning(f"    ⚠️  No safetensors found in {path}")
            return False
            
    # 4. YOLO (单文件或目录)
    elif model_name == "yolo11":
        if path_obj.is_file():
            if path_obj.suffix != ".pt":
                return False
        elif not list(path_obj.rglob("*.pt")):
            logger.warning(f"    ⚠️  No .pt files found")
            return False
            
    logger.info(f"    ✅ Model files verified")
    return True

def get_directory_size(path):
    path_obj = Path(path)
    if not path_obj.exists(): return 0
    if path_obj.is_file(): return path_obj.stat().st_size / (1024 * 1024)
    return sum(f.stat().st_size for f in path_obj.rglob("*") if f.is_file()) / (1024 * 1024)

def check_model_exists(output_path, config, name):
    target_dir = output_path / config["target_dir"]
    if config.get("filename"):
        f = target_dir / config["filename"]
        return (f.exists() and f.stat().st_size > 0), "File found"
    if not target_dir.exists(): return False, "Dir missing"
    if any(target_dir.iterdir()): return True, "Files found"
    return False, "Dir empty"

def generate_magic_pdf_json(output_dir):
    """
    生成 magic-pdf.json
    ✅ [核心修复] 将配置文件直接保存到共享的 models 目录下 (output_dir)，
    这样该文件会持久化到宿主机 ./models/magic-pdf.json，
    并由 docker-entrypoint.sh 脚本分发到其他容器。
    """
    # 务必直接使用 output_dir (即 /app/models)，不要使用 .parent
    config_path = Path(output_dir) / "magic-pdf.json"
    
    # 注意：这里的 paths 是容器内的绝对路径
    config_content = r"""{
  "models-dir": "/app/models/PDF-Extract-Kit-1.0/models",
  "vlm-models-dir": "/app/models/MinerU2.5-2509-1.2B",
  "device-mode": "cuda",
  "layout-config": {
    "model": "doclayout_yolo"
  },
  "formula-config": {
    "mfd_model": "yolo_v8_mfd",
    "mre_model": "unimernet_small"
  }
}"""
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(config_content)
        logger.success(f"✅ Configuration file created at: {config_path}")
        logger.info("    -> Confirmed support for: pipeline, vlm-auto-engine, hybrid-auto-engine")
    except Exception as e:
        logger.error(f"❌ Failed to create config: {e}")

# ==============================================================================
# 主程序
# ==============================================================================

def main(output_dir, selected_models=None, force=False):
    logger.info("=" * 60)
    logger.info("🚀 Tianshu Model Download Script (Hybrid Strategy)")
    logger.info("=" * 60)

    output_path = Path(output_dir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"📁 Output directory (Container/Host mapped): {output_path}")

    # 筛选模型
    models_to_download = MODELS
    if selected_models:
        selected_list = [m.strip() for m in selected_models.split(",")]
        models_to_download = {k: v for k, v in MODELS.items() if k in selected_list}

    manifest = {"created": datetime.now().isoformat(), "models": {}, "total_size_mb": 0}
    total_dl, total_skip, total_fail = 0, 0, 0

    for name, config in models_to_download.items():
        logger.info(f"📦 [{name.upper()}] {config['name']}")
        
        try:
            # 策略：自动下载模型（Paddle等）直接跳过
            if config.get("auto_download"):
                logger.info(f"    ℹ️  {name} will be auto-downloaded by runtime engine")
                logger.info(f"        Target: {config.get('description', 'Cache directory')}")
                manifest["models"][name] = {"status": "auto_download"}
                continue

            target = output_path / config["target_dir"]
            
            # 检查存在
            if not force:
                exists, reason = check_model_exists(output_path, config, name)
                if exists:
                    size_mb = get_directory_size(target)
                    logger.info(f"    ✅ Already exists ({size_mb:.1f} MB)")
                    logger.info(f"    📂 Path: {target}")
                    manifest["models"][name] = {"status": "exists", "path": str(target), "size_mb": round(size_mb, 2)}
                    total_skip += 1
                    logger.info("")
                    continue

            # 下载
            logger.info(f"    ⬇️  Downloading to {config['target_dir']}...")
            path = None
            src = config["source"]
            
            if src == "huggingface":
                path = download_from_huggingface(
                    config["repo_id"], 
                    str(target), 
                    config.get("filename")
                )
            elif src == "modelscope":
                # 优先使用 model_id，如果没有则用 repo_id (兼容旧配置)
                mid = config.get("model_id") or config.get("repo_id")
                path = download_from_modelscope(mid, str(target))

            # ✅ 核心优化：容错处理
            if path and verify_model_files(path, name):
                size_mb = get_directory_size(path)
                manifest["models"][name] = {"status": "downloaded", "path": str(path)}
                logger.info(f"    ✅ Success ({size_mb:.1f} MB)")
                logger.info(f"    📂 Path: {path}")
                total_dl += 1
            else:
                logger.error(f"    ❌ Validation failed for {name}")
                if config.get("required", False):
                    total_fail += 1
                else:
                    logger.warning(f"    ⚠️ [IGNORED] Optional model {name} failed, but not required. Skipping...")

        except Exception as e:
            logger.error(f"    ❌ Error: {e}")
            if config.get("required", False):
                total_fail += 1
            else:
                logger.warning(f"    ⚠️ [IGNORED] Optional model {name} failed, but not required. Skipping...")
        logger.info("")

    # 无论模型下载成功与否，都尝试生成配置文件，确保容器有配置可用
    generate_magic_pdf_json(output_path)
    
    with open(output_path / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    logger.info("=" * 60)
    logger.info(f"✅ Downloaded: {total_dl} | ⏭️  Skipped: {total_skip} | ❌ Failed: {total_fail}")
    
    # 只要必填项没有失败，脚本即以 0 状态退出，确保后续服务(如 vllm)能够启动
    return 0 if total_fail == 0 else 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="./models")
    parser.add_argument("--models")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    
    try:
        sys.exit(main(args.output, args.models, args.force))
    except KeyboardInterrupt:
        sys.exit(130)
