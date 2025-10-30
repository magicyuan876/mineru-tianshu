"""
Format Engine Base Class - 格式引擎基类

定义插件化格式引擎的标准接口
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Set, Optional
from loguru import logger


class FormatEngine(ABC):
    """
    格式引擎基类

    所有格式引擎必须继承此类并实现 parse 方法
    """

    # 子类必须定义支持的文件扩展名
    SUPPORTED_EXTENSIONS: Set[str] = set()

    # 子类必须定义格式名称
    FORMAT_NAME: str = "unknown"

    # 子类必须定义格式描述
    FORMAT_DESCRIPTION: str = ""

    def __init__(self):
        """初始化格式引擎"""
        self.logger = logger

    @abstractmethod
    def parse(self, file_path: str, options: Optional[Dict] = None) -> Dict:
        """
        解析文件

        Args:
            file_path: 文件路径
            options: 可选的解析选项

        Returns:
            解析结果字典，必须包含以下字段：
            {
                "format": str,              # 格式名称
                "markdown": str,            # Markdown 格式的内容（用于 RAG）
                "json_content": dict,       # 结构化 JSON 数据（用于 RAG）
                "metadata": dict,           # 元数据信息（可选）
                "summary": str,             # 简要摘要（可选）
            }
        """
        pass

    def validate_file(self, file_path: str) -> bool:
        """
        验证文件是否为支持的格式

        Args:
            file_path: 文件路径

        Returns:
            是否为支持的格式
        """
        suffix = Path(file_path).suffix.lower()
        return suffix in self.SUPPORTED_EXTENSIONS

    def get_info(self) -> Dict:
        """
        获取引擎信息

        Returns:
            引擎信息字典
        """
        return {
            "name": self.FORMAT_NAME,
            "description": self.FORMAT_DESCRIPTION,
            "extensions": list(self.SUPPORTED_EXTENSIONS),
        }


class FormatEngineRegistry:
    """
    格式引擎注册器

    管理所有可用的格式引擎
    """

    _engines: Dict[str, FormatEngine] = {}
    _extension_map: Dict[str, str] = {}  # 扩展名 -> 格式名称映射

    @classmethod
    def register(cls, engine: FormatEngine):
        """
        注册格式引擎

        Args:
            engine: 格式引擎实例
        """
        format_name = engine.FORMAT_NAME

        if format_name in cls._engines:
            logger.warning(f"⚠️  Format engine '{format_name}' already registered, overwriting...")

        cls._engines[format_name] = engine

        # 注册扩展名映射
        for ext in engine.SUPPORTED_EXTENSIONS:
            cls._extension_map[ext] = format_name

        logger.info(f"✅ Registered format engine: {format_name}")
        logger.info(f"   Extensions: {', '.join(engine.SUPPORTED_EXTENSIONS)}")

    @classmethod
    def get_engine(cls, format_name: str) -> Optional[FormatEngine]:
        """
        根据格式名称获取引擎

        Args:
            format_name: 格式名称

        Returns:
            格式引擎实例，如果不存在则返回 None
        """
        return cls._engines.get(format_name)

    @classmethod
    def get_engine_by_extension(cls, file_path: str) -> Optional[FormatEngine]:
        """
        根据文件扩展名获取引擎

        Args:
            file_path: 文件路径

        Returns:
            格式引擎实例，如果不支持该扩展名则返回 None
        """
        suffix = Path(file_path).suffix.lower()
        format_name = cls._extension_map.get(suffix)

        if format_name:
            return cls._engines.get(format_name)

        return None

    @classmethod
    def is_supported(cls, file_path: str) -> bool:
        """
        检查文件是否被任何引擎支持

        Args:
            file_path: 文件路径

        Returns:
            是否支持该文件
        """
        suffix = Path(file_path).suffix.lower()
        return suffix in cls._extension_map

    @classmethod
    def list_engines(cls) -> List[Dict]:
        """
        列出所有已注册的引擎

        Returns:
            引擎信息列表
        """
        return [engine.get_info() for engine in cls._engines.values()]

    @classmethod
    def get_supported_extensions(cls) -> List[str]:
        """
        获取所有支持的扩展名

        Returns:
            扩展名列表
        """
        return list(cls._extension_map.keys())
