"""
MinerU Tianshu - MCP Server
天枢 MCP 协议服务器

企业级 AI 数据预处理平台 - MCP 接口
通过 Model Context Protocol 暴露数据处理能力

支持功能:
- 文档、图片、音频、视频等多模态数据处理
- Base64 编码的文件传输
- URL 文件下载
- 异步任务处理和状态查询
- 队列统计和任务管理
"""

import asyncio
import json
import os
import sys
from typing import Any
from pathlib import Path
import base64

from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent
from starlette.applications import Starlette
from starlette.routing import Route
import aiohttp
from loguru import logger
import uvicorn

# API 配置（从环境变量读取）
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# 初始化 MCP Server
app = Server("mineru-tianshu")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """列出所有可用的工具"""
    return [
        Tool(
            name="parse_document",
            description="""
解析文档（PDF、图片、Office文档等）为 Markdown 格式。

📁 支持 2 种文件输入方式：
1. file_base64: Base64 编码的文件内容（推荐用于小文件 < 100MB）
2. file_url: 公网可访问的文件 URL（服务器会自动下载）

支持的文件格式：
- PDF 和图片（使用 MinerU GPU 加速解析）
- Office 文档（Word、Excel、PowerPoint）
- 网页和文本（HTML、Markdown、TXT、CSV）

功能特性：
- 公式识别和表格识别
- 支持中英文、日文、韩文等多语言
- 支持任务优先级设置
- 异步处理，可选择等待完成或稍后查询
            """.strip(),
            inputSchema={
                "type": "object",
                "properties": {
                    # 方式 1: Base64 编码（小文件推荐）
                    "file_base64": {"type": "string", "description": "Base64 编码的文件内容（适用于 < 100MB 的文件）"},
                    "file_name": {"type": "string", "description": "文件名（使用 file_base64 时必需）"},
                    # 方式 2: URL 下载
                    "file_url": {"type": "string", "description": "文件的公网 URL（服务器会自动下载）"},
                    # 解析选项
                    "backend": {
                        "type": "string",
                        "enum": ["pipeline", "vlm-transformers", "vlm-vllm-engine"],
                        "description": "处理后端，默认: pipeline",
                        "default": "pipeline",
                    },
                    "lang": {
                        "type": "string",
                        "enum": ["ch", "en", "korean", "japan"],
                        "description": "文档语言，默认: ch",
                        "default": "ch",
                    },
                    "method": {
                        "type": "string",
                        "enum": ["auto", "txt", "ocr"],
                        "description": "解析方法，默认: auto",
                        "default": "auto",
                    },
                    "formula_enable": {
                        "type": "boolean",
                        "description": "是否启用公式识别，默认: true",
                        "default": True,
                    },
                    "table_enable": {"type": "boolean", "description": "是否启用表格识别，默认: true", "default": True},
                    "priority": {
                        "type": "integer",
                        "description": "任务优先级（0-100），数字越大越优先，默认: 0",
                        "default": 0,
                        "minimum": 0,
                        "maximum": 100,
                    },
                    "wait_for_completion": {
                        "type": "boolean",
                        "description": "是否等待任务完成，默认: true",
                        "default": True,
                    },
                    "max_wait_seconds": {
                        "type": "integer",
                        "description": "最大等待时间（秒），默认: 300",
                        "default": 300,
                        "minimum": 10,
                        "maximum": 3600,
                    },
                },
                # 必须提供 2 种方式之一
                "oneOf": [{"required": ["file_base64", "file_name"]}, {"required": ["file_url"]}],
            },
        ),
        Tool(
            name="get_task_status",
            description="""
查询文档解析任务的状态和结果。

可以查询任务的：
- 当前状态（pending/processing/completed/failed/cancelled）
- 处理进度和时间信息
- 错误信息（如果失败）
- 解析结果内容（如果完成）
            """.strip(),
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "任务 ID（由 parse_document 返回）"},
                    "include_content": {
                        "type": "boolean",
                        "description": "是否包含完整的解析结果内容，默认: true",
                        "default": True,
                    },
                },
                "required": ["task_id"],
            },
        ),
        Tool(
            name="list_tasks",
            description="""
列出最近的文档解析任务。

可以按状态筛选，查看任务队列情况。
            """.strip(),
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["pending", "processing", "completed", "failed", "cancelled"],
                        "description": "筛选指定状态的任务（可选，不填则返回所有状态）",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回数量限制，默认: 10",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 100,
                    },
                },
            },
        ),
        Tool(
            name="get_queue_stats",
            description="""
获取任务队列统计信息。

返回各个状态的任务数量，了解系统负载情况。
            """.strip(),
            inputSchema={"type": "object", "properties": {}},
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """处理工具调用"""
    try:
        logger.info(f"🔧 Tool called: {name}")

        if name == "parse_document":
            return await parse_document(arguments)
        elif name == "get_task_status":
            return await get_task_status(arguments)
        elif name == "list_tasks":
            return await list_tasks(arguments)
        elif name == "get_queue_stats":
            return await get_queue_stats(arguments)
        else:
            return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}, indent=2))]
    except Exception as e:
        logger.error(f"❌ Tool call failed: {name}, error: {e}")
        logger.exception(e)
        return [TextContent(type="text", text=json.dumps({"error": str(e), "tool": name}, indent=2))]


async def parse_document(args: dict) -> list[TextContent]:
    """解析文档 - 支持 Base64 和 URL 两种输入方式"""
    async with aiohttp.ClientSession() as session:
        temp_file = None
        file_data = None
        file_name = None

        try:
            # 方式 1: Base64 编码
            if "file_base64" in args:
                logger.info("📦 Receiving file via Base64 encoding")

                try:
                    # Security: Safe use of base64 for file transmission via MCP protocol
                    # This is legitimate business logic, not code obfuscation
                    file_content = base64.b64decode(args["file_base64"])
                except Exception as e:
                    return [
                        TextContent(
                            type="text", text=json.dumps({"error": f"Invalid base64 encoding: {str(e)}"}, indent=2)
                        )
                    ]

                file_name = args["file_name"]

                # 检查文件大小
                size_mb = len(file_content) / (1024 * 1024)
                if size_mb > 100:
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps(
                                {"error": f"File too large ({size_mb:.1f}MB). Maximum size is 100MB."}, indent=2
                            ),
                        )
                    ]

                logger.info(f"📦 File: {file_name}, Size: {size_mb:.2f}MB")

                # 创建临时文件（使用共享上传目录）
                import uuid

                upload_dir = Path("/app/uploads")
                upload_dir.mkdir(parents=True, exist_ok=True)
                temp_file_path = upload_dir / f"{uuid.uuid4().hex}_{file_name}"
                temp_file_path.write_bytes(file_content)
                file_data = open(temp_file_path, "rb")

            # 方式 2: URL 下载
            elif "file_url" in args:
                url = args["file_url"]
                logger.info(f"🌐 Downloading file from URL: {url}")

                try:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                        if resp.status != 200:
                            return [
                                TextContent(
                                    type="text",
                                    text=json.dumps(
                                        {"error": f"Failed to download file from {url}", "status_code": resp.status},
                                        indent=2,
                                    ),
                                )
                            ]

                        # 从 URL 推断文件名
                        file_name = Path(url).name or "downloaded_file"

                        # 尝试从 Content-Disposition 获取文件名
                        if "content-disposition" in resp.headers:
                            import re

                            cd = resp.headers["content-disposition"]
                            match = re.search(r'filename[*]?=["\']?([^"\';\r\n]+)', cd)
                            if match:
                                file_name = match.group(1)

                        # 下载到临时文件
                        file_content = await resp.read()
                        size_mb = len(file_content) / (1024 * 1024)

                        if size_mb > 100:
                            return [
                                TextContent(
                                    type="text",
                                    text=json.dumps(
                                        {
                                            "error": f"Downloaded file too large ({size_mb:.1f}MB). Maximum size is 100MB."
                                        },
                                        indent=2,
                                    ),
                                )
                            ]

                        logger.info(f"📦 Downloaded: {file_name}, Size: {size_mb:.2f}MB")

                        # 创建临时文件（使用共享上传目录）
                        import uuid

                        upload_dir = Path("/app/uploads")
                        upload_dir.mkdir(parents=True, exist_ok=True)
                        temp_file_path = upload_dir / f"{uuid.uuid4().hex}_{file_name}"
                        temp_file_path.write_bytes(file_content)
                        file_data = open(temp_file_path, "rb")

                except asyncio.TimeoutError:
                    return [
                        TextContent(
                            type="text", text=json.dumps({"error": f"Timeout downloading file from {url}"}, indent=2)
                        )
                    ]
                except Exception as e:
                    return [
                        TextContent(
                            type="text", text=json.dumps({"error": f"Failed to download file: {str(e)}"}, indent=2)
                        )
                    ]

            else:
                return [
                    TextContent(
                        type="text", text=json.dumps({"error": "Must provide either file_base64 or file_url"}, indent=2)
                    )
                ]

            # 提交任务到 API Server
            form_data = aiohttp.FormData()
            form_data.add_field("file", file_data, filename=file_name)
            form_data.add_field("backend", args.get("backend", "pipeline"))
            form_data.add_field("lang", args.get("lang", "ch"))
            form_data.add_field("method", args.get("method", "auto"))
            form_data.add_field("formula_enable", str(args.get("formula_enable", True)).lower())
            form_data.add_field("table_enable", str(args.get("table_enable", True)).lower())
            form_data.add_field("priority", str(args.get("priority", 0)))

            logger.info(f"📤 Submitting task for: {file_name}")

            async with session.post(f"{API_BASE_URL}/api/v1/tasks/submit", data=form_data) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps(
                                {"error": "Failed to submit task", "details": error_text, "status_code": resp.status},
                                indent=2,
                            ),
                        )
                    ]

                result = await resp.json()
                task_id = result["task_id"]
                logger.info(f"✅ Task submitted: {task_id}")

            # 关闭文件
            if file_data:
                file_data.close()

            # 是否等待完成
            if not args.get("wait_for_completion", True):
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "status": "submitted",
                                "task_id": task_id,
                                "file_name": file_name,
                                "message": "Task submitted successfully. Use get_task_status to check progress.",
                            },
                            indent=2,
                            ensure_ascii=False,
                        ),
                    )
                ]

            # 等待任务完成
            logger.info(f"⏳ Waiting for task completion: {task_id}")
            max_wait = args.get("max_wait_seconds", 300)
            poll_interval = 2
            elapsed = 0

            while elapsed < max_wait:
                async with session.get(f"{API_BASE_URL}/api/v1/tasks/{task_id}") as resp:
                    if resp.status != 200:
                        return [
                            TextContent(
                                type="text",
                                text=json.dumps({"error": "Failed to query task status", "task_id": task_id}, indent=2),
                            )
                        ]

                    task_status = await resp.json()
                    status = task_status["status"]

                    if status == "completed":
                        # 任务完成，返回结果
                        logger.info(f"✅ Task completed: {task_id}")
                        content = task_status.get("data", {}).get("content", "") if task_status.get("data") else ""

                        return [
                            TextContent(
                                type="text",
                                text=json.dumps(
                                    {
                                        "status": "completed",
                                        "task_id": task_id,
                                        "file_name": file_name,
                                        "content": content,
                                        "processing_time": _calculate_processing_time(task_status),
                                        "created_at": task_status.get("created_at"),
                                        "started_at": task_status.get("started_at"),
                                        "completed_at": task_status.get("completed_at"),
                                    },
                                    indent=2,
                                    ensure_ascii=False,
                                ),
                            )
                        ]

                    elif status == "failed":
                        logger.error(f"❌ Task failed: {task_id}")
                        return [
                            TextContent(
                                type="text",
                                text=json.dumps(
                                    {
                                        "status": "failed",
                                        "task_id": task_id,
                                        "file_name": file_name,
                                        "error": task_status.get("error_message", "Unknown error"),
                                        "created_at": task_status.get("created_at"),
                                        "started_at": task_status.get("started_at"),
                                        "completed_at": task_status.get("completed_at"),
                                    },
                                    indent=2,
                                    ensure_ascii=False,
                                ),
                            )
                        ]

                    elif status == "cancelled":
                        logger.warning(f"⚠️ Task cancelled: {task_id}")
                        return [
                            TextContent(
                                type="text",
                                text=json.dumps(
                                    {"status": "cancelled", "task_id": task_id, "file_name": file_name},
                                    indent=2,
                                    ensure_ascii=False,
                                ),
                            )
                        ]

                    elif status in ["pending", "processing"]:
                        await asyncio.sleep(poll_interval)
                        elapsed += poll_interval
                        if elapsed % 10 == 0:  # 每 10 秒记录一次
                            logger.info(f"⏳ Task {task_id} status: {status}, elapsed: {elapsed}s")

                    else:
                        return [
                            TextContent(
                                type="text",
                                text=json.dumps(
                                    {"status": status, "task_id": task_id, "file_name": file_name},
                                    indent=2,
                                    ensure_ascii=False,
                                ),
                            )
                        ]

            # 超时
            logger.warning(f"⏰ Task timeout: {task_id}")
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "status": "timeout",
                            "task_id": task_id,
                            "file_name": file_name,
                            "message": f"Task did not complete within {max_wait} seconds. Use get_task_status to check later.",
                        },
                        indent=2,
                        ensure_ascii=False,
                    ),
                )
            ]

        finally:
            # 清理临时文件
            if temp_file and Path(temp_file.name).exists():
                try:
                    Path(temp_file.name).unlink()
                except Exception as e:
                    logger.warning(f"Failed to delete temp file: {e}")


async def get_task_status(args: dict) -> list[TextContent]:
    """查询任务状态"""
    task_id = args["task_id"]
    include_content = args.get("include_content", True)

    logger.info(f"📊 Querying task status: {task_id}")

    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_BASE_URL}/api/v1/tasks/{task_id}") as resp:
            if resp.status == 404:
                return [TextContent(type="text", text=json.dumps({"error": f"Task not found: {task_id}"}, indent=2))]

            if resp.status != 200:
                return [
                    TextContent(
                        type="text",
                        text=json.dumps({"error": "Failed to query task status", "task_id": task_id}, indent=2),
                    )
                ]

            task = await resp.json()

            # 构建响应
            response = {
                "task_id": task_id,
                "status": task["status"],
                "file_name": task["file_name"],
                "backend": task["backend"],
                "priority": task["priority"],
                "created_at": task["created_at"],
                "started_at": task["started_at"],
                "completed_at": task["completed_at"],
                "worker_id": task["worker_id"],
                "retry_count": task["retry_count"],
            }

            if task.get("error_message"):
                response["error_message"] = task["error_message"]

            if include_content and task["status"] == "completed" and task.get("data"):
                response["content"] = task["data"].get("content", "")
                response["processing_time"] = _calculate_processing_time(task)
                if task["data"].get("markdown_file"):
                    response["markdown_file"] = task["data"]["markdown_file"]

            return [TextContent(type="text", text=json.dumps(response, indent=2, ensure_ascii=False))]


async def list_tasks(args: dict) -> list[TextContent]:
    """列出任务"""
    status = args.get("status")
    limit = args.get("limit", 10)

    logger.info(f"📋 Listing tasks: status={status}, limit={limit}")

    params = {"limit": limit}
    if status:
        params["status"] = status

    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_BASE_URL}/api/v1/queue/tasks", params=params) as resp:
            if resp.status != 200:
                return [TextContent(type="text", text=json.dumps({"error": "Failed to list tasks"}, indent=2))]

            result = await resp.json()
            tasks = result["tasks"]

            # 简化任务信息
            simplified_tasks = [
                {
                    "task_id": t["task_id"],
                    "file_name": t["file_name"],
                    "status": t["status"],
                    "backend": t["backend"],
                    "priority": t["priority"],
                    "created_at": t["created_at"],
                    "started_at": t["started_at"],
                    "completed_at": t["completed_at"],
                    "worker_id": t["worker_id"],
                }
                for t in tasks
            ]

            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {"count": len(simplified_tasks), "tasks": simplified_tasks}, indent=2, ensure_ascii=False
                    ),
                )
            ]


async def get_queue_stats(args: dict) -> list[TextContent]:
    """获取队列统计"""
    logger.info("📊 Getting queue stats")

    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_BASE_URL}/api/v1/queue/stats") as resp:
            if resp.status != 200:
                return [TextContent(type="text", text=json.dumps({"error": "Failed to get queue stats"}, indent=2))]

            result = await resp.json()

            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "stats": result["stats"],
                            "total": result.get("total", sum(result["stats"].values())),
                            "timestamp": result.get("timestamp"),
                        },
                        indent=2,
                        ensure_ascii=False,
                    ),
                )
            ]


def _calculate_processing_time(task: dict) -> str:
    """计算处理时间"""
    from datetime import datetime

    if task.get("started_at") and task.get("completed_at"):
        try:
            start = datetime.fromisoformat(task["started_at"])
            end = datetime.fromisoformat(task["completed_at"])
            duration = (end - start).total_seconds()
            return f"{duration:.2f} seconds"
        except Exception:
            return "N/A"
    return "N/A"


async def main():
    """启动 MCP Server (SSE 模式)"""
    logger.info("=" * 60)
    logger.info("🚀 Starting MinerU Tianshu MCP Server")
    logger.info("=" * 60)
    logger.info(f"📡 API Base URL: {API_BASE_URL}")

    # 创建 SSE Transport
    sse = SseServerTransport("/messages")

    # SSE 处理函数
    async def handle_sse(request):
        async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
            await app.run(streams[0], streams[1], app.create_initialization_options())

    # POST 消息处理函数
    async def handle_messages(request):
        await sse.handle_post_message(request.scope, request.receive, request._send)

    # 健康检查端点
    async def health_check(request):
        from starlette.responses import JSONResponse

        return JSONResponse(
            {
                "status": "healthy",
                "service": "MinerU Tianshu MCP Server",
                "version": "1.0.0",
                "endpoints": {"sse": "/sse", "messages": "/messages (POST)", "health": "/health"},
                "tools": ["parse_document", "get_task_status", "list_tasks", "get_queue_stats"],
                "api_base_url": API_BASE_URL,
            }
        )

    # 创建 Starlette 应用
    starlette_app = Starlette(
        routes=[
            Route("/sse", endpoint=handle_sse),
            Route("/messages", endpoint=handle_messages, methods=["POST"]),
            Route("/health", endpoint=health_check, methods=["GET"]),
            Route("/", endpoint=health_check, methods=["GET"]),  # 根路径也返回健康检查
        ]
    )

    # 从环境变量读取配置
    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_PORT", "8001"))

    logger.info(f"🌐 MCP Server listening on http://{host}:{port}")
    logger.info(f"📡 SSE endpoint: http://{host}:{port}/sse")
    logger.info(f"📮 Messages endpoint: http://{host}:{port}/messages")
    logger.info(f"🏥 Health check: http://{host}:{port}/health")
    logger.info("📚 Available tools: parse_document, get_task_status, list_tasks, get_queue_stats")
    logger.info("=" * 60)

    config = uvicorn.Config(starlette_app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 MCP Server stopped by user")
    except Exception as e:
        logger.error(f"❌ MCP Server failed to start: {e}")
        logger.exception(e)
        sys.exit(1)
