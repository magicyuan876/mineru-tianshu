#!/usr/bin/env python3
"""
Offline model preparation script for Tianshu.

The output directory is meant to be shipped separately from Docker images and
mounted into containers as /app/models plus the cache subdirectories declared in
docker-compose.offline.yml.
"""

import argparse
import json
import os
import shutil
import sys
import tarfile
from datetime import datetime
from pathlib import Path
from urllib.request import urlretrieve

try:
    from loguru import logger

    logger.remove()
    logger.add(
        sys.stdout, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>"
    )
except ImportError:
    import logging

    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    logger = logging.getLogger("download_models")
    logger.success = logger.info


PADDLE_MODEL_BASE = "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0"
PADDLE_FONT_URL = "https://paddle-model-ecology.bj.bcebos.com/paddlex/PaddleX3.0/fonts/simfang.ttf"
LAMA_URL = "https://github.com/enesmsahin/simple-lama-inpainting/releases/download/v0.1.0/big-lama.pt"
ULTRALYTICS_ARIAL_URL = "https://github.com/ultralytics/assets/releases/download/v0.0.0/Arial.ttf"


MODELS = {
    "mineru_pipeline": {
        "name": "MinerU Pipeline (PDF-Extract-Kit)",
        "source": "modelscope",
        "model_id": "OpenDataLab/PDF-Extract-Kit-1.0",
        "target_dir": "PDF-Extract-Kit-1.0",
        "required": True,
        "verify": ["models/Layout/PP-DocLayoutV2", "models/MFR/unimernet_hf_small_2503", "models/OCR/paddleocr_torch"],
    },
    "mineru_vlm": {
        "name": "MinerU 2.5 VLM (1.2B)",
        "source": "modelscope",
        "model_id": "opendatalab/MinerU2.5-2509-1.2B",
        "target_dir": "MinerU2.5-2509-1.2B",
        "required": True,
        "verify_glob": ["*.safetensors"],
    },
    "paddleocr_vl_1_5": {
        "name": "PaddleOCR-VL-1.5-0.9B",
        "source": "huggingface",
        "repo_id": "PaddlePaddle/PaddleOCR-VL-1.5",
        "target_dir": "paddlex_cache/official_models/PaddleOCR-VL-1.5-0.9B",
        "required": True,
        "verify_glob": ["*.safetensors"],
        "post_symlink": (
            "paddlex_cache/official_models/PaddleOCR-VL-1.5-0.9B",
            "paddlex_cache/official_models/PaddleOCR-VL-1.5",
        ),
    },
    "pp_doclayout_v3": {
        "name": "PP-DocLayoutV3",
        "source": "paddle_tar",
        "url": f"{PADDLE_MODEL_BASE}/PP-DocLayoutV3_infer.tar",
        "target_dir": "paddlex_cache/official_models/PP-DocLayoutV3",
        "required": True,
        "verify": ["inference.json", "inference.yml", "inference.pdiparams"],
    },
    "pp_lcnet_doc_ori": {
        "name": "PP-LCNet_x1_0_doc_ori",
        "source": "paddle_tar",
        "url": f"{PADDLE_MODEL_BASE}/PP-LCNet_x1_0_doc_ori_infer.tar",
        "target_dir": "paddlex_cache/official_models/PP-LCNet_x1_0_doc_ori",
        "required": False,
        "verify": ["inference.json", "inference.yml", "inference.pdiparams"],
    },
    "uvdoc": {
        "name": "UVDoc",
        "source": "paddle_tar",
        "url": f"{PADDLE_MODEL_BASE}/UVDoc_infer.tar",
        "target_dir": "paddlex_cache/official_models/UVDoc",
        "required": False,
        "verify": ["inference.json", "inference.yml", "inference.pdiparams"],
    },
    "simfang_font": {
        "name": "PaddleX simfang.ttf",
        "source": "url_file",
        "url": PADDLE_FONT_URL,
        "target_file": "paddlex_cache/fonts/simfang.ttf",
        "required": False,
    },
    "sensevoice": {
        "name": "SenseVoiceSmall",
        "source": "modelscope",
        "model_id": "iic/SenseVoiceSmall",
        "target_dir": "SenseVoiceSmall",
        "required": True,
    },
    "fsmn_vad": {
        "name": "FSMN VAD",
        "source": "modelscope",
        "model_id": "iic/speech_fsmn_vad_zh-cn-16k-common-pytorch",
        "target_dir": "speech_fsmn_vad_zh-cn-16k-common-pytorch",
        "required": True,
    },
    "paraformer": {
        "name": "Paraformer Speaker Diarization",
        "source": "modelscope",
        "model_id": "iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
        "target_dir": "Paraformer",
        "required": False,
    },
    "ct_punc": {
        "name": "CT Punctuation",
        "source": "modelscope",
        "model_id": "iic/punc_ct-transformer_zh-cn-common-vocab272727-pytorch",
        "target_dir": "punc_ct-transformer_zh-cn-common-vocab272727-pytorch",
        "required": False,
    },
    "campplus": {
        "name": "CAM++ Speaker Model",
        "source": "modelscope",
        "model_id": "iic/speech_campplus_sv_zh-cn_16k-common",
        "target_dir": "speech_campplus_sv_zh-cn_16k-common",
        "required": False,
    },
    "yolo11": {
        "name": "YOLO11x Watermark Detection",
        "source": "huggingface",
        "repo_id": "corzent/yolo11x_watermark_detection",
        "filename": "best.pt",
        "target_dir": "YOLO11",
        "required": False,
        "post_copy": ("YOLO11/best.pt", "watermark_models/yolo11x_watermark.pt"),
    },
    "lama": {
        "name": "LaMa Inpainting",
        "source": "url_file",
        "url": LAMA_URL,
        "target_file": "big-lama.pt",
        "required": False,
        "post_copy": ("big-lama.pt", "torch_cache/hub/checkpoints/big-lama.pt"),
    },
    "ultralytics_arial": {
        "name": "Ultralytics Arial.ttf",
        "source": "url_file",
        "url": ULTRALYTICS_ARIAL_URL,
        "target_file": "ultralytics_cfg/Arial.ttf",
        "required": False,
    },
}


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def directory_has_files(path: Path) -> bool:
    return path.exists() and any(path.iterdir())


def get_size_mb(path: Path) -> float:
    if not path.exists():
        return 0.0
    if path.is_file():
        return path.stat().st_size / (1024 * 1024)
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file()) / (1024 * 1024)


def download_from_huggingface(config: dict, target: Path) -> Path | None:
    from huggingface_hub import hf_hub_download, snapshot_download

    hf_endpoint = os.getenv("HF_ENDPOINT")
    if hf_endpoint:
        os.environ.setdefault("HF_ENDPOINT", hf_endpoint)

    ensure_dir(target)
    if config.get("filename"):
        hf_hub_download(
            repo_id=config["repo_id"],
            filename=config["filename"],
            local_dir=str(target),
            local_dir_use_symlinks=False,
            resume_download=True,
        )
    else:
        snapshot_download(
            repo_id=config["repo_id"],
            local_dir=str(target),
            local_dir_use_symlinks=False,
            resume_download=True,
        )
    return target


def download_from_modelscope(config: dict, target: Path) -> Path | None:
    from modelscope import snapshot_download

    ensure_dir(target)
    snapshot_download(config["model_id"], local_dir=str(target), revision="master")
    return target


def safe_extract_tar(tar_path: Path, target: Path) -> None:
    ensure_dir(target)
    with tarfile.open(tar_path) as tar:
        target_resolved = target.resolve()
        for member in tar.getmembers():
            member_path = (target / member.name).resolve()
            try:
                member_path.relative_to(target_resolved)
            except ValueError:
                raise RuntimeError(f"Unsafe tar member path: {member.name}")
            if member.issym() or member.islnk():
                link_path = (member_path.parent / member.linkname).resolve()
                try:
                    link_path.relative_to(target_resolved)
                except ValueError:
                    raise RuntimeError(f"Unsafe tar link target: {member.name} -> {member.linkname}")
        tar.extractall(target)


def flatten_single_child_dir(target: Path) -> None:
    children = [p for p in target.iterdir()]
    dirs = [p for p in children if p.is_dir()]
    files = [p for p in children if p.is_file()]
    if len(dirs) != 1 or files:
        return
    child = dirs[0]
    for item in child.iterdir():
        shutil.move(str(item), str(target / item.name))
    child.rmdir()


def download_paddle_tar(config: dict, target: Path) -> Path | None:
    ensure_dir(target)
    tmp_tar = target.with_suffix(".tar.download")
    logger.info(f"    Downloading archive: {config['url']}")
    urlretrieve(config["url"], tmp_tar)
    safe_extract_tar(tmp_tar, target)
    tmp_tar.unlink(missing_ok=True)
    flatten_single_child_dir(target)
    return target


def download_url_file(config: dict, output_path: Path) -> Path | None:
    target = output_path / config["target_file"]
    ensure_dir(target.parent)
    logger.info(f"    Downloading file: {config['url']}")
    urlretrieve(config["url"], target)
    return target


def model_target(output_path: Path, config: dict) -> Path:
    if config.get("target_file"):
        return output_path / config["target_file"]
    return output_path / config["target_dir"]


def verify_model(output_path: Path, name: str, config: dict) -> tuple[bool, str]:
    target = model_target(output_path, config)
    if not target.exists():
        return False, f"missing: {target}"

    if target.is_file():
        if target.stat().st_size <= 0:
            return False, f"empty file: {target}"
        return True, "file exists"

    if not directory_has_files(target):
        return False, f"empty directory: {target}"

    for rel_path in config.get("verify", []):
        if not (target / rel_path).exists():
            return False, f"missing required path: {target / rel_path}"

    for pattern in config.get("verify_glob", []):
        if not list(target.rglob(pattern)):
            return False, f"missing files matching {pattern} in {target}"

    if name == "yolo11" and not list(target.rglob("*.pt")):
        return False, f"missing .pt files in {target}"

    return True, "verified"


def copy_or_link(output_path: Path, src_rel: str, dst_rel: str) -> None:
    src = output_path / src_rel
    dst = output_path / dst_rel
    if not src.exists():
        logger.warning(f"    Post step skipped, source missing: {src}")
        return
    ensure_dir(dst.parent)
    if dst.exists() or dst.is_symlink():
        return
    try:
        rel_src = os.path.relpath(src, start=dst.parent)
        dst.symlink_to(rel_src, target_is_directory=src.is_dir())
    except OSError:
        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)


def run_post_steps(output_path: Path, config: dict) -> None:
    if config.get("post_symlink"):
        copy_or_link(output_path, *config["post_symlink"])
    if config.get("post_copy"):
        src = output_path / config["post_copy"][0]
        dst = output_path / config["post_copy"][1]
        if src.exists() and (not dst.exists() or (dst.is_file() and dst.stat().st_size <= 0)):
            ensure_dir(dst.parent)
            shutil.copy2(src, dst)


def verify_post_steps(output_path: Path, config: dict) -> tuple[bool, str]:
    if config.get("post_symlink"):
        dst = output_path / config["post_symlink"][1]
        if not dst.exists():
            return False, f"missing post symlink/copy target: {dst}"

    if config.get("post_copy"):
        dst = output_path / config["post_copy"][1]
        if not dst.exists():
            return False, f"missing post copy target: {dst}"
        if dst.is_file() and dst.stat().st_size <= 0:
            return False, f"empty post copy target: {dst}"

    return True, "post steps verified"


def generate_mineru_json(output_path: Path) -> None:
    config_path = output_path / "mineru.json"
    config = {
        "models-dir": {
            "pipeline": "/app/models/PDF-Extract-Kit-1.0",
            "vlm": "/app/models/MinerU2.5-2509-1.2B",
        },
        "config_version": "1.3.1",
    }
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=4), encoding="utf-8")
    logger.success(f"✅ mineru.json created at: {config_path}")


def generate_ultralytics_settings(output_path: Path) -> None:
    settings_path = output_path / "ultralytics_cfg" / "settings.json"
    if settings_path.exists() and settings_path.stat().st_size > 0:
        return

    ensure_dir(settings_path.parent)
    settings = {
        "sync": False,
        "hub": False,
        "api_key": "",
        "datasets_dir": "/app/data",
        "weights_dir": "/app/models/YOLO11",
        "runs_dir": "/app/data/output/ultralytics",
    }
    settings_path.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.success(f"✅ Ultralytics settings created at: {settings_path}")


def verify_mineru_json(output_path: Path) -> tuple[bool, str]:
    config_path = output_path / "mineru.json"
    if not config_path.exists():
        return False, f"missing: {config_path}"

    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return False, f"invalid JSON in {config_path}: {exc}"

    models_dir = config.get("models-dir", {})
    expected = {
        "pipeline": "/app/models/PDF-Extract-Kit-1.0",
        "vlm": "/app/models/MinerU2.5-2509-1.2B",
    }
    if models_dir != expected:
        return False, f"unexpected models-dir in {config_path}: {models_dir}"

    return True, "verified"


def verify_ultralytics_settings(output_path: Path) -> tuple[bool, str]:
    settings_path = output_path / "ultralytics_cfg" / "settings.json"
    if not settings_path.exists():
        return False, f"missing: {settings_path}"

    try:
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return False, f"invalid JSON in {settings_path}: {exc}"

    if settings.get("sync") is not False or settings.get("hub") is not False:
        return False, f"Ultralytics online settings are not disabled in {settings_path}"

    return True, "verified"


def selected_model_map(selected_models: str | None) -> dict:
    if not selected_models:
        return MODELS
    selected = {m.strip() for m in selected_models.split(",") if m.strip()}
    unknown = selected - set(MODELS)
    if unknown:
        raise ValueError(f"Unknown model names: {', '.join(sorted(unknown))}")
    return {k: v for k, v in MODELS.items() if k in selected}


def ensure_standard_layout(output_path: Path) -> None:
    for rel_path in [
        "paddlex_cache/official_models",
        "paddlex_cache/fonts",
        "paddleocr_cache",
        "modelscope_cache",
        "huggingface_cache",
        "torch_cache/hub/checkpoints",
        "ultralytics_cfg",
    ]:
        ensure_dir(output_path / rel_path)


def prepare_model(output_path: Path, name: str, config: dict, force: bool, verify_only: bool) -> dict:
    target = model_target(output_path, config)
    verified, reason = verify_model(output_path, name, config)

    if verify_only:
        if verified:
            verified, reason = verify_post_steps(output_path, config)
        status = "verified" if verified else "missing"
        return {"status": status, "path": str(target), "reason": reason, "size_mb": round(get_size_mb(target), 2)}

    if verified and not force:
        run_post_steps(output_path, config)
        return {"status": "exists", "path": str(target), "reason": reason, "size_mb": round(get_size_mb(target), 2)}

    source = config["source"]
    logger.info(f"    Downloading to: {target}")
    if source == "huggingface":
        download_from_huggingface(config, target)
    elif source == "modelscope":
        download_from_modelscope(config, target)
    elif source == "paddle_tar":
        download_paddle_tar(config, target)
    elif source == "url_file":
        download_url_file(config, output_path)
    else:
        raise ValueError(f"Unsupported source: {source}")

    run_post_steps(output_path, config)
    verified, reason = verify_model(output_path, name, config)
    status = "downloaded" if verified else "invalid"
    return {"status": status, "path": str(target), "reason": reason, "size_mb": round(get_size_mb(target), 2)}


def main(
    output_dir: str,
    selected_models: str | None = None,
    force: bool = False,
    verify_only: bool = False,
    strict: bool = False,
) -> int:
    logger.info("=" * 60)
    logger.info("🚀 Tianshu Offline Model Preparation")
    logger.info("=" * 60)

    models = selected_model_map(selected_models)
    output_path = Path(output_dir).resolve()
    ensure_dir(output_path)
    ensure_standard_layout(output_path)
    logger.info(f"📁 Output directory: {output_path}")
    manifest = {
        "created": datetime.now().isoformat(),
        "output_dir": str(output_path),
        "verify_only": verify_only,
        "models": {},
        "total_size_mb": 0,
    }

    total_fail = 0
    for name, config in models.items():
        logger.info(f"📦 [{name}] {config['name']}")
        try:
            result = prepare_model(output_path, name, config, force, verify_only)
            manifest["models"][name] = result | {"required": config.get("required", False)}
            if result["status"] in {"verified", "exists", "downloaded"}:
                logger.success(f"    ✅ {result['status']} ({result['size_mb']:.1f} MB)")
            else:
                logger.error(f"    ❌ {result['reason']}")
                if config.get("required", False) or strict:
                    total_fail += 1
        except Exception as e:
            logger.error(f"    ❌ Error: {e}")
            manifest["models"][name] = {
                "status": "error",
                "path": str(model_target(output_path, config)),
                "reason": str(e),
                "required": config.get("required", False),
            }
            if config.get("required", False) or strict:
                total_fail += 1
        logger.info("")

    if verify_only and selected_models is None:
        verified, reason = verify_mineru_json(output_path)
        manifest["mineru_json"] = {"status": "verified" if verified else "missing", "reason": reason}
        if verified:
            logger.success(f"✅ mineru.json {reason}")
        else:
            logger.error(f"❌ mineru.json {reason}")
            total_fail += 1

        verified, reason = verify_ultralytics_settings(output_path)
        manifest["ultralytics_settings"] = {"status": "verified" if verified else "missing", "reason": reason}
        if verified:
            logger.success(f"✅ Ultralytics settings {reason}")
        else:
            logger.error(f"❌ Ultralytics settings {reason}")
            if strict:
                total_fail += 1
    elif not verify_only:
        generate_mineru_json(output_path)

    if not verify_only:
        generate_ultralytics_settings(output_path)

    manifest["total_size_mb"] = round(get_size_mb(output_path), 2)
    (output_path / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    logger.info("=" * 60)
    logger.info(f"📊 Total size: {manifest['total_size_mb']:.1f} MB | Required failures: {total_fail}")
    return 0 if total_fail == 0 else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare Tianshu models for offline deployment")
    parser.add_argument("--output", default="./models")
    parser.add_argument("--models", help="Comma-separated model keys to download or verify")
    parser.add_argument("--force", action="store_true", help="Re-download even if files exist")
    parser.add_argument("--verify-only", action="store_true", help="Only verify the model layout")
    parser.add_argument("--strict", action="store_true", help="Fail when any selected model is missing or invalid")
    args = parser.parse_args()

    try:
        sys.exit(main(args.output, args.models, args.force, args.verify_only, args.strict))
    except KeyboardInterrupt:
        sys.exit(130)
