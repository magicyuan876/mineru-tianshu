import logging
import time
from collections.abc import Generator
from dataclasses import dataclass
from typing import Any, Dict
import os

import httpx
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from dify_plugin.errors.tool import ToolProviderCredentialValidationError

# 禁用代理
os.environ['NO_PROXY'] = 'localhost,127.0.0.1'
os.environ['no_proxy'] = 'localhost,127.0.0.1'

# 配置日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s - [Parse Tool] - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)


@dataclass
class Credentials:
    api_base_url: str
    api_key: str


class TianshuParseTool(Tool):
    """
    天枢文档解析工具 - 简化版
    支持单个或多个文件，自动轮询等待结果
    """

    def _get_credentials(self) -> Credentials:
        """Get and validate credentials."""
        api_base_url = self.runtime.credentials.get("api_base_url")
        api_key = self.runtime.credentials.get("api_key")

        if not api_base_url:
            raise ToolProviderCredentialValidationError("Please input API Base URL")
        if not api_key:
            raise ToolProviderCredentialValidationError("Please input API Key")

        return Credentials(
            api_base_url=api_base_url.rstrip("/"),
            api_key=api_key
        )

    def _get_headers(self, credentials: Credentials) -> Dict[str, str]:
        """Get request headers."""
        return {
            'X-API-Key': credentials.api_key,
            'Accept': 'application/json'
        }

    def _get_file_content(self, file: Any) -> tuple[str, bytes]:
        """
        获取文件内容 - 完全参考 Dify 官方 MinerU 插件实现
        官方代码: file_data = {"file": (file.filename, file.blob)}
        返回: (文件名, 文件内容)
        """
        # 官方 MinerU 插件直接使用 file.blob，非常简单！
        # 参考: tools/mineru/parse_pdf.py 第 227 行
        file_name = file.filename
        file_content = file.blob

        logger.info(f"   📄 文件: {file_name}")
        logger.info(f"   📦 大小: {len(file_content)} bytes")

        return file_name, file_content

    def _submit_file(
        self,
        file_name: str,
        file_content: bytes,
        credentials: Credentials,
        backend: str,
        lang: str,
        formula_enable: bool,
        priority: int,
        password: str = ""
    ) -> str:
        """
        提交单个文件到解析服务
        返回: task_id
        """
        files = {
            "file": (file_name, file_content, "application/octet-stream")
        }
        data = {
            "backend": backend,
            "lang": lang,
            "method": "auto",
            "formula_enable": str(formula_enable).lower(),
            "table_enable": "true",
            "priority": str(priority)
        }
        if password:
            data["password"] = password

        headers = self._get_headers(credentials)
        url = f"{credentials.api_base_url}/api/v1/tasks/submit"

        with httpx.Client(timeout=120.0) as client:
            response = client.post(url, headers=headers, files=files, data=data)
            response.raise_for_status()
            result = response.json()

        if not result.get("success"):
            raise ValueError(result.get("detail", "Failed to submit task"))

        task_id = result.get("task_id")
        if not task_id:
            raise ValueError("No task_id returned from server")

        return task_id

    def _wait_for_result(
        self,
        task_id: str,
        credentials: Credentials,
        format_type: str = "markdown",
        max_wait: int = 300,
        poll_interval: int = 2
    ) -> Dict[str, Any]:
        """
        轮询等待任务完成
        返回: 解析结果
        """
        headers = self._get_headers(credentials)
        url = f"{credentials.api_base_url}/api/v1/tasks/{task_id}"
        params = {"format": format_type, "upload_images": "false"}

        start_time = time.time()
        last_status = None

        while time.time() - start_time < max_wait:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(url, headers=headers, params=params)
                response.raise_for_status()
                result = response.json()

            if not result.get("success"):
                raise ValueError(result.get("detail", "Failed to query task"))

            status = result.get("status")

            # 状态变化时输出日志
            if status != last_status:
                logger.info(f"   任务状态: {status}")
                last_status = status

            # 完成
            if status == "completed":
                data = result.get("data", {})
                return {
                    "status": "completed",
                    "file_name": result.get("file_name", ""),
                    "content": data.get("content", ""),
                    "json_content": data.get("json_content")
                }

            # 失败
            elif status == "failed":
                error_msg = result.get("error_message", "Task failed")
                raise ValueError(f"Task failed: {error_msg}")

            # 处理中，继续等待
            elif status in ["pending", "processing"]:
                time.sleep(poll_interval)
                continue

            # 未知状态
            else:
                logger.warning(f"   未知状态: {status}")
                time.sleep(poll_interval)
                continue

        raise TimeoutError(f"Task timeout after {max_wait} seconds")

    def _invoke(self, tool_parameters: Dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        """
        解析文档工具 - 支持单个或多个文件
        自动提交任务并等待结果返回
        """
        logger.info("=" * 80)
        logger.info("开始文档解析（简化版 - 自动轮询）")
        logger.info("=" * 80)

        try:
            credentials = self._get_credentials()

            # 获取文件参数（兼容单个和多个）
            files_input = tool_parameters.get("files") or tool_parameters.get("file")
            if not files_input:
                yield self.create_text_message("请上传至少一个文件")
                return

            # 标准化为列表
            files_list = files_input if isinstance(files_input, list) else [files_input]
            total_files = len(files_list)

            # 获取解析参数
            backend = tool_parameters.get("backend", "auto")
            lang = tool_parameters.get("lang", "auto")
            formula_enable = tool_parameters.get("formula_enable", True)
            priority = tool_parameters.get("priority", 0)
            password = tool_parameters.get("password", "") or ""
            max_wait = tool_parameters.get("max_wait_time", 300)  # 最大等待时间（秒）

            logger.info(f"📦 收到 {total_files} 个文件")
            logger.info(f"📋 解析参数: backend={backend}, lang={lang}")

            # 处理每个文件
            all_results = []

            for idx, file in enumerate(files_list, 1):
                try:
                    logger.info(f"\n[{idx}/{total_files}] 处理文件...")

                    # 1. 获取文件内容
                    file_name, file_content = self._get_file_content(file)
                    logger.info(f"   📄 {file_name} ({len(file_content)} bytes)")

                    # 2. 提交任务
                    logger.info("   ⬆️  提交任务...")
                    task_id = self._submit_file(
                        file_name, file_content, credentials,
                        backend, lang, formula_enable, priority, password
                    )
                    logger.info(f"   ✅ Task ID: {task_id}")

                    # 3. 等待结果
                    logger.info("   ⏳ 等待解析完成...")
                    result = self._wait_for_result(task_id, credentials, "markdown", max_wait)

                    logger.info(f"   ✅ 解析完成 ({len(result['content'])} 字符)")

                    all_results.append({
                        "file_name": file_name,
                        "task_id": task_id,
                        "status": "success",
                        "content": result["content"]
                    })

                except Exception as e:
                    logger.error(f"   ❌ 失败: {str(e)}")
                    all_results.append({
                        "file_name": getattr(file, 'filename', f'file_{idx}'),
                        "status": "failed",
                        "error": str(e)
                    })

            # 汇总结果
            logger.info("\n" + "=" * 80)
            successful = sum(1 for r in all_results if r["status"] == "success")
            failed = total_files - successful
            logger.info(f"📊 完成: 成功 {successful}, 失败 {failed}")
            logger.info("=" * 80)

            # 返回结果
            if total_files == 1:
                # 单文件：直接返回内容
                result = all_results[0]
                if result["status"] == "success":
                    yield self.create_text_message(result["content"])
                else:
                    yield self.create_text_message(f"❌ 解析失败: {result['error']}")
            else:
                # 多文件：返回汇总
                summary = f"📊 处理了 {total_files} 个文件\n"
                summary += f"✅ 成功: {successful}\n"
                summary += f"❌ 失败: {failed}\n\n"

                for r in all_results:
                    if r["status"] == "success":
                        content_preview = r["content"][:200] + "..." if len(r["content"]) > 200 else r["content"]
                        summary += f"✅ {r['file_name']}:\n{content_preview}\n\n"
                    else:
                        summary += f"❌ {r['file_name']}: {r['error']}\n\n"

                yield self.create_json_message({"results": all_results})
                yield self.create_text_message(summary)

        except Exception as e:
            logger.exception("❌ 工具执行异常:")
            yield self.create_text_message(f"错误: {str(e)}")
