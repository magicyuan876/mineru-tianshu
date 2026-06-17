"""
Markdown 图片提取器

从 Markdown 文件中提取图片:
1. 本地图片（相对/绝对路径）
2. 远程图片（URL）
3. 上传到 RustFS 并替换为 <img> 标签
"""

import re
import shutil
import requests
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from loguru import logger


MARKDOWN_IMAGE_PATTERN = r"!\[([^\]]*)\]\(([^)]+)\)"
WIKI_IMAGE_PATTERN = r"!\[\[(.*?)\]\]"


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
                "rustfs_url": None,
            }

            is_url = src.startswith(("http://", "https://"))

            if is_url:
                try:
                    local_path = self._download_image(src, output_path)
                    img_info["local_path"] = local_path
                except Exception as e:
                    logger.warning(f"⚠️  Failed to download image {src}: {e}")
                    img_info["local_path"] = None
            else:
                local_path = self._resolve_local_image(src, base_dir, output_path)
                if local_path and local_path.exists():
                    img_info["local_path"] = str(local_path)
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
                "rustfs_url": None,
            }

            is_url = src.startswith(("http://", "https://"))

            if is_url:
                try:
                    local_path = self._download_image(src, output_path)
                    img_info["local_path"] = local_path
                except Exception as e:
                    logger.warning(f"⚠️  Failed to download wiki image {src}: {e}")
            else:
                local_path = self._resolve_local_image(src, base_dir, output_path)
                if local_path and local_path.exists():
                    img_info["local_path"] = str(local_path)

            images.append(img_info)

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

    def _download_image(self, url: str, output_dir: Path) -> Optional[str]:
        """下载远程图片"""
        try:
            response = requests.get(url, timeout=30, stream=True)
            response.raise_for_status()

            content_type = response.headers.get("content-type", "")
            ext = self._get_extension_from_content_type(content_type)
            if not ext:
                ext = Path(url).suffix or ".jpg"

            filename = self._generate_image_filename(ext)
            filepath = output_dir / filename

            with response as resp:
                with open(filepath, "wb") as f:
                    shutil.copyfileobj(resp.raw, f)

            logger.debug(f"✅ Downloaded: {url} -> {filepath}")
            return str(filepath)

        except Exception as e:
            logger.error(f"❌ Failed to download {url}: {e}")
            raise

    def _resolve_local_image(self, src: str, base_dir: Path, output_dir: Path) -> Optional[Path]:
        """解析本地图片路径"""
        src_path = Path(src)

        if src_path.is_absolute():
            if src_path.exists():
                return src_path
            return None

        resolved = base_dir / src_path
        resolved = resolved.resolve()

        if resolved.exists():
            return resolved

        for pattern in ["**/" + src_path.name, "**/*" + src_path.suffix]:
            matches = list(base_dir.glob(pattern))
            if matches:
                return matches[0]

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
    """将 Markdown 图片引用替换为 <img> 标签"""
    for img in images:
        if not img["rustfs_url"]:
            continue

        src = img["src"]
        url = img["rustfs_url"]
        alt = img["alt"] or ""

        md_pattern = rf"!\[([^\]]*)\]\({re.escape(src)}\)"
        content = re.sub(md_pattern, f'<img src="{url}" alt="{alt}">', content)

        wiki_pattern = rf"\!\[\[({re.escape(src)})\]\]"
        content = re.sub(wiki_pattern, f'<img src="{url}" alt="{alt}">', content)

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
