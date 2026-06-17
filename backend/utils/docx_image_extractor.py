"""
Office 文档图片提取器

从 DOCX、XLSX、PPTX 文件中提取嵌入的图片，并支持追加到 Markdown 内容中

Office 格式本质是 ZIP 包，结构如下:

DOCX:
docx.zip
├── word/
│   ├── document.xml
│   └── media/              # 图片目录

XLSX:
xlsx.zip
├── xl/
│   ├── worksheet*.xml
│   └── media/              # 图片目录

PPTX:
pptx.zip
├── ppt/
│   ├── slides/*.xml
│   └── media/              # 图片目录
"""

import zipfile
import shutil
import re
from pathlib import Path
from typing import List, Dict, Optional
from loguru import logger


MEDIA_PATHS = {
    ".docx": "word/media/",
    ".xlsx": "xl/media/",
    ".pptx": "ppt/media/",
}

RELS_PATHS = {
    ".docx": "word/_rels/document.xml.rels",
    ".xlsx": "xl/_rels/workbook.xml.rels",
    ".pptx": "ppt/_rels/presentation.xml.rels",
}


def extract_images_from_office(office_path: str, output_dir: str) -> List[str]:
    """
    从 Office 文档 (DOCX/XLSX/PPTX) 提取所有图片到指定目录

    Args:
        office_path: Office 文件路径
        output_dir: 图片输出目录

    Returns:
        图片文件名列表，如 ["image1.png", "image2.jpg"]
    """
    file_ext = Path(office_path).suffix.lower()
    media_path = MEDIA_PATHS.get(file_ext)

    if not media_path:
        logger.warning(f"Unsupported office format for image extraction: {file_ext}")
        return []

    return _extract_images_from_zip(office_path, output_dir, media_path)


def _extract_images_from_zip(
    file_path: str,
    output_dir: str,
    media_path_prefix: str,
) -> List[str]:
    """
    通用 ZIP 内图片提取

    Args:
        file_path: 文件路径
        output_dir: 输出目录
        media_path_prefix: ZIP 内媒体目录前缀，如 "word/media/"

    Returns:
        图片文件名列表
    """
    images = []
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(file_path, "r") as zf:
        for name in zf.namelist():
            if name.startswith(media_path_prefix) and not name.endswith("/"):
                img_name = Path(name).name
                img_path = output_path / img_name

                with zf.open(name) as src, open(img_path, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                images.append(img_name)

    return images


def extract_images_from_docx(docx_path: str, output_dir: str) -> List[str]:
    """
    从 DOCX 文件提取所有图片到指定目录

    Args:
        docx_path: DOCX 文件路径
        output_dir: 图片输出目录

    Returns:
        图片文件名列表
    """
    return _extract_images_from_zip(docx_path, output_dir, "word/media/")


def extract_images_from_xlsx(xlsx_path: str, output_dir: str) -> List[str]:
    """
    从 XLSX 文件提取所有图片到指定目录

    Args:
        xlsx_path: XLSX 文件路径
        output_dir: 图片输出目录

    Returns:
        图片文件名列表
    """
    return _extract_images_from_zip(xlsx_path, output_dir, "xl/media/")


def extract_images_from_pptx(pptx_path: str, output_dir: str) -> List[str]:
    """
    从 PPTX 文件提取所有图片到指定目录

    Args:
        pptx_path: PPTX 文件路径
        output_dir: 图片输出目录

    Returns:
        图片文件名列表
    """
    return _extract_images_from_zip(pptx_path, output_dir, "ppt/media/")


def get_image_rels_mapping(office_path: str) -> Dict[str, str]:
    """
    从 Office 文档中解析 rId 到图片文件名的映射关系

    Args:
        office_path: Office 文件路径

    Returns:
        {rId: image_filename} 映射
    """
    file_ext = Path(office_path).suffix.lower()
    rels_path = RELS_PATHS.get(file_ext)

    if not rels_path:
        return {}

    rels_mapping = {}

    with zipfile.ZipFile(office_path, "r") as zf:
        try:
            rels_content = zf.read(rels_path).decode("utf-8")
        except KeyError:
            return rels_mapping

        pattern = r'Id="(rId\d+)"[^>]*Target="media/([^"]+)"'
        for match in re.finditer(pattern, rels_content):
            rid, img_name = match.groups()
            rels_mapping[rid] = img_name

    return rels_mapping


def build_markdown_with_inline_images(
    markdown_content: str,
    office_path: str,
    images_dir: str,
) -> str:
    """
    解析 Office XML，将文档中的图片引用替换为本地路径

    注意: 这个函数用于将图片插入到文档中对应的位置，
    需要解析主 XML 文档中的 blip 元素。对于简单场景，
    建议直接使用 append_images_to_markdown() 将图片追加到末尾。

    Args:
        markdown_content: 原始 Markdown 内容
        office_path: Office 文件路径
        images_dir: 图片目录路径

    Returns:
        更新后的 Markdown 内容
    """
    file_ext = Path(office_path).suffix.lower()

    if file_ext == ".docx":
        doc_xml_path = "word/document.xml"
    elif file_ext == ".xlsx":
        doc_xml_path = "xl/workbook.xml"
    elif file_ext == ".pptx":
        doc_xml_path = "ppt/presentation.xml"
    else:
        return markdown_content

    rels_mapping = get_image_rels_mapping(office_path)
    if not rels_mapping:
        return markdown_content

    try:
        with zipfile.ZipFile(office_path, "r") as zf:
            doc_content = zf.read(doc_xml_path).decode("utf-8")
    except KeyError:
        return markdown_content

    for rid, img_name in rels_mapping.items():
        img_path = f"{images_dir}/{img_name}"
        pattern = rf'<a:blip[^>]*r:embed="{rid}"[^>]*/>'
        if re.search(pattern, doc_content):
            markdown_img = f"![{img_name}]({img_path})"
            doc_content = re.sub(pattern, markdown_img, doc_content)

    return markdown_content


def append_images_to_markdown(
    markdown_content: str,
    image_names: List[str],
    images_dir: Optional[str] = None,
) -> str:
    """
    将图片追加到 Markdown 末尾

    Args:
        markdown_content: 原始 Markdown 内容
        image_names: 图片文件名列表
        images_dir: 图片目录路径 (可选，默认使用 "images")

    Returns:
        追加图片后的 Markdown 内容
    """
    if not image_names:
        return markdown_content

    img_dir = images_dir or "images"
    lines = ["\n\n## 图片"]

    for name in image_names:
        lines.append(f"![{name}]({img_dir}/{name})")

    return markdown_content + "\n" + "\n".join(lines)


def extract_images_with_metadata(office_path: str, output_dir: str) -> List[Dict]:
    """
    从 Office 文档提取图片并返回元数据信息

    Args:
        office_path: Office 文件路径 (DOCX/XLSX/PPTX)
        output_dir: 图片输出目录

    Returns:
        图片元数据列表，如 [
            {"name": "image1.png", "path": "/output/images/image1.png", "size": 12345},
            {"name": "image2.jpg", "path": "/output/images/image2.jpg", "size": 67890}
        ]
    """
    image_names = extract_images_from_office(office_path, output_dir)

    metadata = []
    for name in image_names:
        img_path = Path(output_dir) / name
        if img_path.exists():
            metadata.append(
                {
                    "name": name,
                    "path": str(img_path),
                    "size": img_path.stat().st_size,
                }
            )

    return metadata
