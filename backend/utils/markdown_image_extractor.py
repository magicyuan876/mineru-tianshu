"""
Markdown 图片提取器

从 Markdown 文件中提取图片:
1. 本地图片（相对/绝对路径）
2. 远程图片（URL）
3. 上传到 RustFS 并替换为 <img> 标签
"""

import os
import re
import socket
import shutil
import ipaddress
import requests
from pathlib import Path
from urllib.parse import urlparse
from typing import List, Dict, Optional, Tuple
from loguru import logger


MARKDOWN_IMAGE_PATTERN = r"!\[([^\]]*)\]\(([^)]+)\)"
WIKI_IMAGE_PATTERN = r"!\[\[(.*?)\]\]"

# 远程图片拉取安全配置（上传的 Markdown 是不可信输入）
# - ALLOW_REMOTE_IMAGES=false 可彻底关闭远程拉取
# - 单图大小上限，避免被超大文件拖垮磁盘/内存
# - 最大重定向跳数，每跳都重新做 SSRF 校验
ALLOW_REMOTE_IMAGES = os.getenv("MARKDOWN_ALLOW_REMOTE_IMAGES", "true").lower() in ("true", "1", "yes")
MAX_IMAGE_BYTES = int(os.getenv("MARKDOWN_MAX_IMAGE_BYTES", str(20 * 1024 * 1024)))
MAX_REDIRECTS = 5


class MarkdownImageExtractor:
    """Markdown 图片提取器"""

    def __init__(self, rustfs_client=None):
        """
        初始化提取器

        Args:
            rustfs_client: RustFS 客户端实例（可选）
        """
        self._rustfs_client = rustfs_client

    def set_rustfs_client(self, client):
        """设置 RustFS 客户端"""
        self._rustfs_client = client

    def extract_images_from_markdown(
        self,
        markdown_content: str,
        markdown_file_path: Optional[str] = None,
        output_dir: Optional[str] = None,
    ) -> Dict:
        """
        从 Markdown 中提取所有图片

        Args:
            markdown_content: Markdown 内容
            markdown_file_path: Markdown 文件路径（用于解析相对路径）
            output_dir: 图片输出目录

        Returns:
            {
                "images": [
                    {
                        "original": "!![alt](path_or_url)",
                        "src": "path_or_url",
                        "alt": "alt text",
                        "local_path": "/path/to/saved/image.jpg",  # 如果是本地图片
                        "rustfs_url": "http://...",  # 上传后的 URL
                    }
                ],
                "content_without_markdown_images": "markdown without image refs",
                "chunks": ["chunk1 with <img>", "chunk2 with <img>"]
            }
        """
        markdown_path = Path(markdown_file_path) if markdown_file_path else None
        base_dir = markdown_path.parent if markdown_path else Path.cwd()

        if output_dir:
            output_path = Path(output_dir)
        else:
            output_path = base_dir / "images"
        output_path.mkdir(parents=True, exist_ok=True)

        images = []
        content = markdown_content

        for match in re.finditer(MARKDOWN_IMAGE_PATTERN, markdown_content):
            alt_text = match.group(1) or ""
            src = match.group(2)

            img_info = {
                "original": match.group(0),
                "src": src,
                "alt": alt_text,
                "local_path": None,
                "local_rel": None,
                "rustfs_url": None,
            }

            is_url = src.startswith(("http://", "https://"))

            if is_url:
                try:
                    local_path = self._download_image(src, output_path)
                    if local_path:
                        img_info["local_path"], img_info["local_rel"] = self._ensure_in_output(local_path, output_path)
                except Exception as e:
                    logger.warning(f"⚠️  Failed to download image {src}: {e}")
                    img_info["local_path"] = None
            else:
                local_path = self._resolve_local_image(src, base_dir, output_path)
                if local_path and local_path.exists():
                    img_info["local_path"], img_info["local_rel"] = self._ensure_in_output(local_path, output_path)
                else:
                    logger.warning(f"⚠️  Local image not found: {src}")

            images.append(img_info)

        for match in re.finditer(WIKI_IMAGE_PATTERN, content):
            src = match.group(1)
            img_info = {
                "original": match.group(0),
                "src": src,
                "alt": Path(src).stem,
                "local_path": None,
                "local_rel": None,
                "rustfs_url": None,
            }

            is_url = src.startswith(("http://", "https://"))

            if is_url:
                try:
                    local_path = self._download_image(src, output_path)
                    if local_path:
                        img_info["local_path"], img_info["local_rel"] = self._ensure_in_output(local_path, output_path)
                except Exception as e:
                    logger.warning(f"⚠️  Failed to download wiki image {src}: {e}")
            else:
                local_path = self._resolve_local_image(src, base_dir, output_path)
                if local_path and local_path.exists():
                    img_info["local_path"], img_info["local_rel"] = self._ensure_in_output(local_path, output_path)

            images.append(img_info)

        # 仅在显式提供了 RustFS 客户端时才上传。
        # 关键：rustfs_client 为 None 表示调用方（如 use_rustfs=false 的任务）要求保留本地图片，
        # 不能在此自动 new 一个 RustFSClient 偷偷上传，否则任务级开关 use_rustfs=false 形同虚设。
        if self._rustfs_client is not None:
            for img_info in images:
                if img_info["local_path"]:
                    try:
                        url = self._upload_to_rustfs(img_info["local_path"])
                        img_info["rustfs_url"] = url
                    except Exception as e:
                        logger.warning(f"⚠️  Failed to upload to rustfs: {e}")

        content = self._remove_markdown_images(content)
        chunks = self._split_into_chunks(content, images)

        return {
            "images": images,
            "content_without_markdown_images": content,
            "chunks": chunks,
        }

    @staticmethod
    def _assert_safe_remote_url(url: str) -> None:
        """SSRF 防护：仅允许 http(s)，且目标主机解析出的所有 IP 必须是公网地址。

        阻断对内网/回环/链路本地（含云元数据 169.254.169.254）/保留地址的访问。
        DNS 可能解析出多个地址，逐一校验，任一非公网即拒绝（含 DNS rebind 缓解）。
        """
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"unsupported url scheme: {parsed.scheme!r}")
        host = parsed.hostname
        if not host:
            raise ValueError("missing host in url")
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        try:
            infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
        except socket.gaierror as e:
            raise ValueError(f"dns resolution failed for {host}: {e}")
        if not infos:
            raise ValueError(f"dns resolution returned no records for {host}")
        for info in infos:
            ip = ipaddress.ip_address(info[4][0])
            if (not ip.is_global) or ip.is_multicast or ip.is_reserved or ip.is_loopback or ip.is_link_local:
                raise ValueError(f"refused non-public address {ip} for host {host}")

    def _download_image(self, url: str, output_dir: Path) -> Optional[str]:
        """下载远程图片（带 SSRF 防护、重定向逐跳校验与大小上限）"""
        if not ALLOW_REMOTE_IMAGES:
            logger.warning(f"⚠️  远程图片拉取已禁用 (MARKDOWN_ALLOW_REMOTE_IMAGES=false)，跳过: {url}")
            return None
        try:
            current = url
            resp = None
            for _ in range(MAX_REDIRECTS + 1):
                self._assert_safe_remote_url(current)
                resp = requests.get(current, timeout=30, stream=True, allow_redirects=False)
                if resp.is_redirect or resp.is_permanent_redirect:
                    location = resp.headers.get("Location")
                    resp.close()
                    if not location:
                        raise ValueError("redirect response without Location header")
                    current = requests.compat.urljoin(current, location)
                    continue
                break
            else:
                raise ValueError("too many redirects")

            resp.raise_for_status()

            content_type = resp.headers.get("content-type", "")
            ext = self._get_extension_from_content_type(content_type)
            if not ext:
                ext = Path(urlparse(url).path).suffix or ".jpg"

            filename = self._generate_image_filename(ext)
            filepath = output_dir / filename

            downloaded = 0
            with resp as r:
                with open(filepath, "wb") as f:
                    for chunk in r.iter_content(chunk_size=65536):
                        if not chunk:
                            continue
                        downloaded += len(chunk)
                        if downloaded > MAX_IMAGE_BYTES:
                            f.close()
                            filepath.unlink(missing_ok=True)
                            raise ValueError(f"image exceeds size limit ({MAX_IMAGE_BYTES} bytes)")
                        f.write(chunk)

            logger.debug(f"✅ Downloaded: {url} -> {filepath}")
            return str(filepath)

        except Exception as e:
            logger.error(f"❌ Failed to download {url}: {e}")
            raise

    def _ensure_in_output(self, local_path, output_dir: Path) -> Tuple[str, str]:
        """
        确保图片实体落在输出目录内，返回 (最终本地路径, 相对引用 'images/<name>')。

        use_rustfs=false 时不上传 RustFS，必须把被引用的本地图片复制进任务输出目录，
        否则图片散落在源文件旁、随产物清理而丢失，且交接接口 /tasks/{id}/images 无法枚举。
        """
        local_path = Path(local_path)
        dest = output_dir / local_path.name
        if local_path.resolve() != dest.resolve():
            try:
                shutil.copy2(local_path, dest)
            except Exception as e:
                logger.warning(f"⚠️  Failed to copy image into output dir ({local_path.name}): {e}")
                dest = local_path
        return str(dest), f"images/{dest.name}"

    @staticmethod
    def _is_within(path: Path, root: Path) -> bool:
        try:
            path.relative_to(root)
            return True
        except ValueError:
            return False

    def _resolve_local_image(self, src: str, base_dir: Path, output_dir: Path) -> Optional[Path]:
        """解析本地图片路径。

        安全约束：被引用的本地图片必须位于 Markdown 所在目录（base_dir）子树内。
        上传的 Markdown 是不可信输入，绝不允许通过绝对路径（如 /etc/passwd）或 ../
        逃逸读取任务目录之外的任意文件（LFI / 任意文件读取）。
        """
        try:
            base_real = base_dir.resolve()
        except Exception:
            return None

        src_path = Path(src)

        candidates: List[Path] = []
        if src_path.is_absolute():
            candidates.append(src_path)
        else:
            candidates.append(base_dir / src_path)
            # 按精确文件名在 base_dir 子树内兜底匹配（glob 已限定在子树内）。
            # 不再用 "**/*<suffix>" 宽松匹配——那会为任意缺失图片返回目录里第一个同后缀文件，
            # 把不相关的图片塞进结果。
            if src_path.name:
                candidates.extend(base_dir.glob("**/" + src_path.name))

        for cand in candidates:
            try:
                real = cand.resolve()
            except Exception:
                continue
            if not real.exists() or not real.is_file():
                continue
            if not self._is_within(real, base_real):
                logger.warning(f"⚠️  拒绝越界本地图片引用（疑似任意文件读取）: {src}")
                continue
            return real

        return None

    def _upload_to_rustfs(self, local_path: str) -> str:
        """上传图片到 RustFS"""
        if self._rustfs_client is None:
            from storage import RustFSClient

            if self._rustfs_client is None:
                self._rustfs_client = RustFSClient()

        return self._rustfs_client.upload_file(local_path)

    def _get_extension_from_content_type(self, content_type: str) -> Optional[str]:
        """从 Content-Type 获取扩展名"""
        mapping = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/gif": ".gif",
            "image/webp": ".webp",
            "image/bmp": ".bmp",
            "image/svg+xml": ".svg",
        }
        return mapping.get(content_type.split(";")[0].strip().lower())

    def _generate_image_filename(self, extension: str) -> str:
        """生成唯一文件名"""
        import time
        import secrets

        timestamp = int(time.time() * 1000)
        random_part = secrets.token_hex(4)
        return f"img_{timestamp}_{random_part}{extension}"

    def _remove_markdown_images(self, content: str) -> str:
        """移除 Markdown 中的图片引用"""
        content = re.sub(MARKDOWN_IMAGE_PATTERN, "", content)
        content = re.sub(WIKI_IMAGE_PATTERN, "", content)
        return content

    def _split_into_chunks(self, content: str, images: List[Dict]) -> List[str]:
        """
        将 Markdown 内容切分成块，每块包含 <img> 标签

        Args:
            content: 去除图片引用的 Markdown 内容
            images: 图片信息列表

        Returns:
            切分后的块列表，每块包含 <img> 标签或纯文本
        """
        if not images:
            return [content] if content.strip() else []

        chunks = []
        current_chunk = []

        lines = content.split("\n")

        for line in lines:
            if line.strip():
                current_chunk.append(line)
            else:
                if current_chunk:
                    chunks.append("\n".join(current_chunk))
                    current_chunk = []

        if current_chunk:
            chunks.append("\n".join(current_chunk))

        chunks_with_images = []
        rustfs_url_map = {img["src"]: img["rustfs_url"] for img in images if img["rustfs_url"]}

        for chunk in chunks:
            for src, url in rustfs_url_map.items():
                pattern = rf"!\[([^\]]*)\]\({re.escape(src)}\)"
                chunk = re.sub(pattern, f'<img src="{url}" alt="">', chunk)

                wiki_pattern = rf"\!\[\[({re.escape(src)})\]\]"
                chunk = re.sub(wiki_pattern, f'<img src="{url}" alt="">', chunk)

            chunks_with_images.append(chunk)

        for i, img in enumerate(images):
            if img["rustfs_url"]:
                img_tag = f'<img src="{img["rustfs_url"]}" alt="{img["alt"]}">'
                if i < len(chunks_with_images):
                    chunks_with_images[i] = chunks_with_images[i] + "\n" + img_tag
                else:
                    chunks_with_images.append(img_tag)

        return chunks_with_images if chunks_with_images else [content]


def process_markdown_images(
    markdown_content: str,
    markdown_file_path: Optional[str] = None,
    output_dir: Optional[str] = None,
    rustfs_client=None,
) -> Dict:
    """
    处理 Markdown 中的图片，上传到 RustFS 并返回 <img> 标签

    Args:
        markdown_content: Markdown 内容
        markdown_file_path: Markdown 文件路径（用于解析相对路径）
        output_dir: 图片输出目录
        rustfs_client: RustFS 客户端实例

    Returns:
        {
            "content": "处理后的 Markdown 内容（图片引用替换为 <img> 标签）",
            "chunks": ["chunk1 with <img>", "chunk2"],
            "images": [...],  # 图片元数据
            "rustfs_urls": {"original_src": "rustfs_url", ...}
        }
    """
    extractor = MarkdownImageExtractor(rustfs_client)

    result = extractor.extract_images_from_markdown(
        markdown_content=markdown_content,
        markdown_file_path=markdown_file_path,
        output_dir=output_dir,
    )

    rustfs_urls = {img["src"]: img["rustfs_url"] for img in result["images"] if img["rustfs_url"]}

    content_with_img_tags = _replace_images_with_img_tags(
        markdown_content,
        result["images"],
    )

    chunks_with_img_tags = [_replace_images_with_img_tags(chunk, result["images"]) for chunk in result["chunks"]]

    return {
        "content": content_with_img_tags,
        "chunks": chunks_with_img_tags,
        "images": result["images"],
        "rustfs_urls": rustfs_urls,
    }


def _replace_images_with_img_tags(content: str, images: List[Dict]) -> str:
    """改写 Markdown 图片引用：有 RustFS 时替换为 <img> 标签；
    无 RustFS 时改写为输出目录内的本地相对路径 images/<name>，
    使 result.md 指向随产物留存的图片副本（供 /tasks/{id}/images 交接接口枚举）。"""
    for img in images:
        src = img["src"]
        alt = img.get("alt") or ""

        if img.get("rustfs_url"):
            repl = f'<img src="{img["rustfs_url"]}" alt="{alt}">'
        elif img.get("local_rel"):
            repl = f'![{alt}]({img["local_rel"]})'
        else:
            continue

        md_pattern = rf"!\[([^\]]*)\]\({re.escape(src)}\)"
        content = re.sub(md_pattern, repl, content)

        wiki_pattern = rf"\!\[\[({re.escape(src)})\]\]"
        content = re.sub(wiki_pattern, repl, content)

    return content


def chunk_markdown_by_heading(
    markdown_content: str,
    include_images: bool = True,
    image_info: Optional[List[Dict]] = None,
) -> List[Dict]:
    """
    按标题切分 Markdown，返回带有图片信息的块

    Args:
        markdown_content: Markdown 内容
        include_images: 是否在块中包含 <img> 标签
        image_info: 图片信息列表（包含 rustfs_url）

    Returns:
        [{"heading": "## 标题", "content": "...", "images": [...]}, ...]
    """
    if image_info is None:
        image_info = []

    rustfs_url_map = {
        img["src"]: {"url": img["rustfs_url"], "alt": img.get("alt", "")} for img in image_info if img.get("rustfs_url")
    }

    chunks = []
    current_heading = None
    current_content_lines = []
    current_images = []

    lines = markdown_content.split("\n")
    code_block = False

    for line in lines:
        if line.startswith("```"):
            code_block = not code_block
            current_content_lines.append(line)
            continue

        if code_block:
            current_content_lines.append(line)
            continue

        header_match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if header_match:
            if current_content_lines or current_heading:
                chunk_content = "\n".join(current_content_lines)
                if include_images and rustfs_url_map:
                    for src, info in rustfs_url_map.items():
                        alt_text = info["alt"] or ""
                        img_tag = f'<img src="{info["url"]}" alt="{alt_text}">'
                        pattern = rf"!\[([^\]]*)\]\({re.escape(src)}\)"
                        chunk_content = re.sub(pattern, img_tag, chunk_content)

                chunks.append(
                    {
                        "heading": current_heading,
                        "content": chunk_content.strip(),
                        "images": current_images.copy(),
                    }
                )

            current_heading = line
            current_content_lines = []
            current_images = []
        else:
            current_content_lines.append(line)

            for src, info in rustfs_url_map.items():
                if src in line:
                    current_images.append({"src": src, "rustfs_url": info["url"]})

    if current_content_lines or current_heading:
        chunk_content = "\n".join(current_content_lines)
        if include_images and rustfs_url_map:
            for src, info in rustfs_url_map.items():
                alt_text = info["alt"] or ""
                img_tag = f'<img src="{info["url"]}" alt="{alt_text}">'
                pattern = rf"!\[([^\]]*)\]\({re.escape(src)}\)"
                chunk_content = re.sub(pattern, img_tag, chunk_content)

        chunks.append(
            {
                "heading": current_heading,
                "content": chunk_content.strip(),
                "images": current_images.copy(),
            }
        )

    return chunks
