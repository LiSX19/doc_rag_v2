"""
Embedding模块

提供文本向量化和模型管理功能。
"""

from .base import BaseEmbedder
from .bge_embedder import BGEEmbedder

__all__ = [
    "BaseEmbedder",
    "BGEEmbedder",
]
