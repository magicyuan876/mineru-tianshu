"""
MinerU Tianshu - API Server
天枢 API 服务器

企业级 AI 数据预处理平台
支持文档、图片、音频、视频等多模态数据处理
提供 RESTful API 接口用于任务提交、查询和管理
企业级认证授权: JWT Token + API Key + SSO
"""

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from loguru import logger
import uvicorn
from typing import Optional
from datetime import datetime
import os
import re
import uuid
from minio import Minio

from task_db import TaskDB

# 导入认证模块
from auth import (
    User,
    Permission,
    get_current_active_user,
    require_permission,
)
from auth.routes import router as auth_router
from auth.auth_db import AuthDB

# 初始化 FastAPI 应用
app = FastAPI(
    title="MinerU Tianshu API",
    description="天枢 - 企业级 AI 数据预处理平台 | 支持文档、图片、音频、视频等多模态数据处理 | 企业级认证授权",
    version="2.0.0",
)

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化数据库
db = TaskDB()
auth_db = AuthDB()

# 注册认证路由
app.include_router(auth_router)

# 配置输出目录（使用共享目录，Docker 环境可访问）
OUTPUT_DIR = Path(os.getenv("OUTPUT_PATH", "/app/output"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# MinIO 配置
MINIO_CONFIG = {
    "endpoint": os.getenv("MINIO_ENDPOINT", ""),
    "access_key": os.getenv("MINIO_ACCESS_KEY", ""),
    "secret_key": os.getenv("MINIO_SECRET_KEY", ""),
    "secure": True,
    "bucket_name": os.getenv("MINIO_BUCKET", ""),
}


def get_minio_client():
    """获取MinIO客户端实例"""
    return Minio(
        MINIO_CONFIG["endpoint"],
        access_key=MINIO_CONFIG["access_key"],
        secret_key=MINIO_CONFIG["secret_key"],
        secure=MINIO_CONFIG["secure"],
    )


def process_markdown_images(md_content: str, image_dir: Path, upload_images: bool = False):
    """
    处理 Markdown 中的图片引用

    Args:
        md_content: Markdown 内容
        image_dir: 图片所在目录
        upload_images: 是否上传图片到 MinIO 并替换链接

    Returns:
        处理后的 Markdown 内容
    """
    if not upload_images:
        return md_content

    try:
        minio_client = get_minio_client()
        bucket_name = MINIO_CONFIG["bucket_name"]
        minio_endpoint = MINIO_CONFIG["endpoint"]

        # 查找所有 markdown 格式的图片
        img_pattern = r"!\[([^\]]*)\]\(([^)]+)\)"

        def replace_image(match):
            alt_text = match.group(1)
            image_path = match.group(2)

            # 构建完整的本地图片路径
            full_image_path = image_dir / Path(image_path).name

            if full_image_path.exists():
                # 获取文件后缀
                file_extension = full_image_path.suffix
                # 生成 UUID 作为新文件名
                new_filename = f"{uuid.uuid4()}{file_extension}"

                try:
                    # 上传到 MinIO
                    object_name = f"images/{new_filename}"
                    minio_client.fput_object(bucket_name, object_name, str(full_image_path))

                    # 生成 MinIO 访问 URL
                    scheme = "https" if MINIO_CONFIG["secure"] else "http"
                    minio_url = f"{scheme}://{minio_endpoint}/{bucket_name}/{object_name}"

                    # 返回 HTML 格式的 img 标签
                    return f'<img src="{minio_url}" alt="{alt_text}">'
                except Exception as e:
                    logger.error(f"Failed to upload image to MinIO: {e}")
                    return match.group(0)  # 上传失败，保持原样

            return match.group(0)

        # 替换所有图片引用
        new_content = re.sub(img_pattern, replace_image, md_content)
        return new_content

    except Exception as e:
        logger.error(f"Error processing markdown images: {e}")
        return md_content  # 出错时返回原内容


@app.get("/")
async def root():
    """API根路径"""
    return {
        "service": "MinerU Tianshu",
        "version": "1.0.0",
        "description": "天枢 - 企业级 AI 数据预处理平台",
        "features": "文档、图片、音频、视频等多模态数据处理",
        "docs": "/docs",
    }


@app.post("/api/v1/tasks/submit")
async def submit_task(
    file: UploadFile = File(..., description="文件: PDF/图片/Office/HTML/音频/视频等多种格式"),
    backend: str = Form(
        "auto",
        description="处理后端: auto (自动选择) | pipeline/deepseek-ocr/paddleocr-vl (文档) | sensevoice (音频) | video (视频) | fasta/genbank (专业格式)",
    ),
    lang: str = Form("auto", description="语言: auto/ch/en/korean/japan等"),
    method: str = Form("auto", description="解析方法: auto/txt/ocr"),
    formula_enable: bool = Form(True, description="是否启用公式识别"),
    table_enable: bool = Form(True, description="是否启用表格识别"),
    priority: int = Form(0, description="优先级，数字越大越优先"),
    # DeepSeek OCR 专用参数
    deepseek_resolution: str = Form("base", description="DeepSeek OCR 分辨率: tiny/small/base/large/dynamic"),
    deepseek_prompt_type: str = Form("document", description="DeepSeek OCR 提示词类型: document/image/free/figure"),
    # 视频处理专用参数
    keep_audio: bool = Form(False, description="视频处理时是否保留提取的音频文件"),
    enable_keyframe_ocr: bool = Form(False, description="是否启用视频关键帧OCR识别（实验性功能）"),
    ocr_backend: str = Form("paddleocr-vl", description="关键帧OCR引擎: paddleocr-vl/deepseek-ocr"),
    keep_keyframes: bool = Form(False, description="是否保留提取的关键帧图像"),
    # 水印去除专用参数
    remove_watermark: bool = Form(False, description="是否启用水印去除（支持 PDF/图片）"),
    watermark_conf_threshold: float = Form(0.35, description="水印检测置信度阈值（0.0-1.0，推荐 0.35）"),
    watermark_dilation: int = Form(10, description="水印掩码膨胀大小（像素，推荐 10）"),
    # 认证依赖
    current_user: User = Depends(require_permission(Permission.TASK_SUBMIT)),
):
    """
    提交文档解析任务

    需要认证和 TASK_SUBMIT 权限。
    立即返回 task_id，任务在后台异步处理。
    """
    try:
        # 创建共享的上传目录（Backend 和 Worker 都能访问）
        upload_dir = Path("/app/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)

        # 生成唯一的文件名（避免冲突）
        unique_filename = f"{uuid.uuid4().hex}_{file.filename}"
        temp_file_path = upload_dir / unique_filename

        # 流式写入文件到磁盘，避免高内存使用
        with open(temp_file_path, "wb") as temp_file:
            while True:
                chunk = await file.read(1 << 23)  # 8MB chunks
                if not chunk:
                    break
                temp_file.write(chunk)

        # 创建任务 (关联用户)
        task_id = db.create_task(
            file_name=file.filename,
            file_path=str(temp_file_path),
            backend=backend,
            options={
                "lang": lang,
                "method": method,
                "formula_enable": formula_enable,
                "table_enable": table_enable,
                # DeepSeek OCR 参数
                "deepseek_resolution": deepseek_resolution,
                "deepseek_prompt_type": deepseek_prompt_type,
                # 视频处理参数
                "keep_audio": keep_audio,
                "enable_keyframe_ocr": enable_keyframe_ocr,
                "ocr_backend": ocr_backend,
                "keep_keyframes": keep_keyframes,
                # 水印去除参数
                "remove_watermark": remove_watermark,
                "watermark_conf_threshold": watermark_conf_threshold,
                "watermark_dilation": watermark_dilation,
            },
            priority=priority,
            user_id=current_user.user_id,  # 关联用户
        )

        logger.info(f"✅ Task submitted: {task_id} - {file.filename}")
        logger.info(f"   User: {current_user.username} ({current_user.role.value})")
        logger.info(f"   Backend: {backend}")
        logger.info(f"   Priority: {priority}")
        if backend == "deepseek-ocr":
            logger.info(f"   DeepSeek Resolution: {deepseek_resolution}")
            logger.info(f"   DeepSeek Prompt Type: {deepseek_prompt_type}")

        return {
            "success": True,
            "task_id": task_id,
            "status": "pending",
            "message": "Task submitted successfully",
            "file_name": file.filename,
            "user_id": current_user.user_id,
            "created_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"❌ Failed to submit task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/tasks/{task_id}")
async def get_task_status(
    task_id: str,
    upload_images: bool = Query(False, description="是否上传图片到MinIO并替换链接（仅当任务完成时有效）"),
    format: str = Query("markdown", description="返回格式: markdown(默认)/json/both"),
    current_user: User = Depends(get_current_active_user),
):
    """
    查询任务状态和详情

    需要认证。用户只能查看自己的任务，管理员可以查看所有任务。
    当任务完成时，会自动返回解析后的内容（data 字段）
    - format=markdown: 只返回 Markdown 内容（默认）
    - format=json: 只返回 JSON 结构化数据（MinerU 和 PaddleOCR-VL 支持）
    - format=both: 同时返回 Markdown 和 JSON
    可选择是否上传图片到 MinIO 并替换为 URL
    """
    task = db.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # 权限检查: 用户只能查看自己的任务，管理员/经理可以查看所有任务
    if not current_user.has_permission(Permission.TASK_VIEW_ALL):
        if task.get("user_id") != current_user.user_id:
            raise HTTPException(status_code=403, detail="Permission denied: You can only view your own tasks")

    response = {
        "success": True,
        "task_id": task_id,
        "status": task["status"],
        "file_name": task["file_name"],
        "backend": task["backend"],
        "priority": task["priority"],
        "error_message": task["error_message"],
        "created_at": task["created_at"],
        "started_at": task["started_at"],
        "completed_at": task["completed_at"],
        "worker_id": task["worker_id"],
        "retry_count": task["retry_count"],
        "user_id": task.get("user_id"),
    }
    logger.info(f"✅ Task status: {task['status']} - (result_path: {task['result_path']})")

    # 如果任务已完成，尝试返回解析内容
    if task["status"] == "completed":
        if not task["result_path"]:
            # 结果文件已被清理
            response["data"] = None
            response["message"] = "Task completed but result files have been cleaned up (older than retention period)"
            return response

        result_dir = Path(task["result_path"])
        logger.info(f"📂 Checking result directory: {result_dir}")

        if result_dir.exists():
            logger.info("✅ Result directory exists")
            # 递归查找 Markdown 文件（MinerU 输出结构：task_id/filename/auto/*.md）
            md_files = list(result_dir.rglob("*.md"))
            # 递归查找 JSON 文件
            # MinerU 输出格式: {filename}_content_list.json (主要的结构化内容)
            # 也支持其他引擎的: content.json, result.json
            json_files = [
                f
                for f in result_dir.rglob("*.json")
                if not f.parent.name.startswith("page_")
                and (f.name in ["content.json", "result.json"] or "_content_list.json" in f.name)
            ]
            logger.info(f"📄 Found {len(md_files)} markdown files and {len(json_files)} json files")

            if md_files:
                try:
                    # 初始化 data 字段
                    response["data"] = {}

                    # 标记 JSON 是否可用
                    response["data"]["json_available"] = len(json_files) > 0

                    # 根据 format 参数决定返回内容
                    if format in ["markdown", "both"]:
                        # 读取 Markdown 内容
                        md_file = md_files[0]
                        logger.info(f"📖 Reading markdown file: {md_file}")
                        with open(md_file, "r", encoding="utf-8") as f:
                            md_content = f.read()

                        logger.info(f"✅ Markdown content loaded, length: {len(md_content)} characters")

                        # 查找图片目录（在 markdown 文件的同级目录下）
                        image_dir = md_file.parent / "images"

                        # 处理图片（如果需要）
                        if upload_images and image_dir.exists():
                            logger.info(f"🖼️  Processing images for task {task_id}, upload_images={upload_images}")
                            md_content = process_markdown_images(md_content, image_dir, upload_images)

                        # 添加 Markdown 相关字段
                        response["data"]["markdown_file"] = md_file.name
                        response["data"]["content"] = md_content
                        response["data"]["images_uploaded"] = upload_images
                        response["data"]["has_images"] = image_dir.exists() if not upload_images else None

                    # 如果用户请求 JSON 格式
                    if format in ["json", "both"] and json_files:
                        import json as json_lib

                        json_file = json_files[0]
                        logger.info(f"📖 Reading JSON file: {json_file}")
                        try:
                            with open(json_file, "r", encoding="utf-8") as f:
                                json_content = json_lib.load(f)
                            response["data"]["json_file"] = json_file.name
                            response["data"]["json_content"] = json_content
                            logger.info("✅ JSON content loaded successfully")
                        except Exception as json_e:
                            logger.warning(f"⚠️  Failed to load JSON: {json_e}")
                    elif format == "json" and not json_files:
                        # 用户请求 JSON 但没有 JSON 文件
                        logger.warning("⚠️  JSON format requested but no JSON file available")
                        response["data"]["message"] = "JSON format not available for this backend"

                    # 如果没有返回任何内容，添加提示
                    if not response["data"]:
                        response["data"] = None
                        logger.warning(f"⚠️  No data returned for format: {format}")
                    else:
                        logger.info(f"✅ Response data field added successfully (format={format})")

                except Exception as e:
                    logger.error(f"❌ Failed to read content: {e}")
                    logger.exception(e)
                    # 读取失败不影响状态查询，只是不返回 data
                    response["data"] = None
            else:
                logger.warning(f"⚠️  No markdown files found in {result_dir}")
        else:
            logger.error(f"❌ Result directory does not exist: {result_dir}")
    elif task["status"] == "completed":
        logger.warning("⚠️  Task completed but result_path is empty")
    else:
        logger.info(f"ℹ️  Task status is {task['status']}, skipping content loading")

    return response


@app.delete("/api/v1/tasks/{task_id}")
async def cancel_task(task_id: str, current_user: User = Depends(get_current_active_user)):
    """
    取消任务（仅限 pending 状态）

    需要认证。用户只能取消自己的任务，管理员可以取消任何任务。
    """
    task = db.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # 权限检查: 用户只能取消自己的任务，管理员可以取消任何任务
    if not current_user.has_permission(Permission.TASK_DELETE_ALL):
        if task.get("user_id") != current_user.user_id:
            raise HTTPException(status_code=403, detail="Permission denied: You can only cancel your own tasks")

    if task["status"] == "pending":
        db.update_task_status(task_id, "cancelled")

        # 删除临时文件
        file_path = Path(task["file_path"])
        if file_path.exists():
            file_path.unlink()

        logger.info(f"⏹️  Task cancelled: {task_id} by user {current_user.username}")
        return {"success": True, "message": "Task cancelled successfully"}
    else:
        raise HTTPException(status_code=400, detail=f"Cannot cancel task in {task['status']} status")


@app.get("/api/v1/queue/stats")
async def get_queue_stats(current_user: User = Depends(require_permission(Permission.QUEUE_VIEW))):
    """
    获取队列统计信息

    需要认证和 QUEUE_VIEW 权限。
    """
    stats = db.get_queue_stats()

    return {
        "success": True,
        "stats": stats,
        "total": sum(stats.values()),
        "timestamp": datetime.now().isoformat(),
        "user": current_user.username,
    }


@app.get("/api/v1/queue/tasks")
async def list_tasks(
    status: Optional[str] = Query(None, description="筛选状态: pending/processing/completed/failed"),
    limit: int = Query(100, description="返回数量限制", le=1000),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取任务列表

    需要认证。普通用户只能看到自己的任务，管理员/经理可以看到所有任务。
    """
    # 检查用户权限
    can_view_all = current_user.has_permission(Permission.TASK_VIEW_ALL)

    if can_view_all:
        # 管理员/经理查看所有任务
        if status:
            tasks = db.get_tasks_by_status(status, limit)
        else:
            with db.get_cursor() as cursor:
                cursor.execute(
                    """
                    SELECT * FROM tasks
                    ORDER BY created_at DESC
                    LIMIT ?
                """,
                    (limit,),
                )
                tasks = [dict(row) for row in cursor.fetchall()]
    else:
        # 普通用户只能看到自己的任务
        with db.get_cursor() as cursor:
            if status:
                cursor.execute(
                    """
                    SELECT * FROM tasks
                    WHERE user_id = ? AND status = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """,
                    (current_user.user_id, status, limit),
                )
            else:
                cursor.execute(
                    """
                    SELECT * FROM tasks
                    WHERE user_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """,
                    (current_user.user_id, limit),
                )
            tasks = [dict(row) for row in cursor.fetchall()]

    return {"success": True, "count": len(tasks), "tasks": tasks, "can_view_all": can_view_all}


@app.post("/api/v1/admin/cleanup")
async def cleanup_old_tasks(
    days: int = Query(7, description="清理N天前的任务"),
    current_user: User = Depends(require_permission(Permission.QUEUE_MANAGE)),
):
    """
    清理旧任务记录（管理接口）

    需要管理员权限。
    """
    deleted_count = db.cleanup_old_tasks(days)

    logger.info(f"🧹 Cleaned up {deleted_count} old tasks by {current_user.username}")

    return {"success": True, "deleted_count": deleted_count, "message": f"Cleaned up tasks older than {days} days"}


@app.post("/api/v1/admin/reset-stale")
async def reset_stale_tasks(
    timeout_minutes: int = Query(60, description="超时时间（分钟）"),
    current_user: User = Depends(require_permission(Permission.QUEUE_MANAGE)),
):
    """
    重置超时的 processing 任务（管理接口）

    需要管理员权限。
    """
    reset_count = db.reset_stale_tasks(timeout_minutes)

    logger.info(f"🔄 Reset {reset_count} stale tasks by {current_user.username}")

    return {
        "success": True,
        "reset_count": reset_count,
        "message": f"Reset tasks processing for more than {timeout_minutes} minutes",
    }


@app.get("/api/v1/engines")
async def list_engines():
    """
    列出所有可用的处理引擎

    无需认证。返回系统中所有可用的处理引擎信息。
    """
    engines = {
        "document": [
            {
                "name": "pipeline",
                "display_name": "MinerU Pipeline",
                "description": "默认的 PDF/图片解析引擎，支持公式、表格等复杂结构",
                "supported_formats": [".pdf", ".png", ".jpg", ".jpeg"],
            },
        ],
        "ocr": [],
        "audio": [],
        "video": [],
        "format": [],
        "office": [
            {
                "name": "markitdown",
                "display_name": "MarkItDown",
                "description": "Office 文档和文本文件转换引擎",
                "supported_formats": [".docx", ".xlsx", ".pptx", ".doc", ".xls", ".ppt", ".html", ".txt", ".csv"],
            },
        ],
    }

    # 动态检测可用引擎
    import importlib.util

    if importlib.util.find_spec("deepseek_ocr") is not None:
        engines["ocr"].append(
            {
                "name": "deepseek_ocr",
                "display_name": "DeepSeek OCR",
                "description": "高精度 OCR 引擎，支持多种分辨率和提示词模式",
                "supported_formats": [".pdf", ".png", ".jpg", ".jpeg"],
            }
        )

    if importlib.util.find_spec("paddleocr_vl") is not None:
        engines["ocr"].append(
            {
                "name": "paddleocr_vl",
                "display_name": "PaddleOCR-VL",
                "description": "PaddlePaddle 视觉语言 OCR 引擎",
                "supported_formats": [".pdf", ".png", ".jpg", ".jpeg"],
            }
        )

    if importlib.util.find_spec("audio_engines") is not None:
        engines["audio"].append(
            {
                "name": "sensevoice",
                "display_name": "SenseVoice",
                "description": "语音识别引擎，支持多语言自动检测",
                "supported_formats": [".wav", ".mp3", ".flac", ".m4a", ".ogg"],
            }
        )

    if importlib.util.find_spec("video_engines") is not None:
        engines["video"].append(
            {
                "name": "video",
                "display_name": "Video Processing",
                "description": "视频处理引擎，支持关键帧提取和音频转录",
                "supported_formats": [".mp4", ".avi", ".mkv", ".mov", ".flv", ".wmv"],
            }
        )

    # 专业格式引擎
    try:
        from format_engines import FormatEngineRegistry

        for engine_info in FormatEngineRegistry.list_engines():
            engines["format"].append(
                {
                    "name": engine_info["name"],
                    "display_name": engine_info["name"].upper(),
                    "description": engine_info["description"],
                    "supported_formats": engine_info["extensions"],
                }
            )
    except ImportError:
        pass

    return {
        "success": True,
        "engines": engines,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/v1/health")
async def health_check():
    """
    健康检查接口
    """
    try:
        # 检查数据库连接
        stats = db.get_queue_stats()

        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "database": "connected",
            "queue_stats": stats,
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(status_code=503, content={"status": "unhealthy", "error": str(e)})


if __name__ == "__main__":
    # 从环境变量读取端口，默认为8000
    api_port = int(os.getenv("API_PORT", "8000"))

    logger.info("🚀 Starting MinerU Tianshu API Server...")
    logger.info(f"📖 API Documentation: http://localhost:{api_port}/docs")

    uvicorn.run(app, host="0.0.0.0", port=api_port, log_level="info")
