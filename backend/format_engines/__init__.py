"""
Format Engines - 格式引擎插件系统

支持专业领域文档格式解析，为 RAG 应用提供结构化数据预处理

支持的格式：
- FASTA: 生物序列格式
- GenBank: 基因序列注释格式
- 更多格式可通过插件扩展...
"""

from .base import FormatEngine, FormatEngineRegistry
from .fasta_engine import FASTAEngine
from .genbank_engine import GenBankEngine

# 自动注册所有引擎
__all__ = [
    "FormatEngine",
    "FormatEngineRegistry",
    "FASTAEngine",
    "GenBankEngine",
]
