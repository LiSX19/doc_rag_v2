"""
编码模块 - 负责将文本分块转换为向量表示

该模块提供统一的编码接口，支持多种编码策略：
- 稠密向量编码 (Dense Embedding)
- 稀疏向量编码 (Sparse Embedding)
- 混合编码 (Hybrid)

主要组件:
- BaseEncoder: 编码器基类
- DenseEncoder: 稠密向量编码器
- SparseEncoder: 稀疏向量编码器
- HybridEncoder: 混合编码器
- EncoderManager: 编码管理器，负责批量编码和存储
"""

from .base import BaseEncoder, EncodedVector
from .dense_encoder import DenseEncoder
from .sparse_encoder import SparseEncoder
from .hybrid_encoder import HybridEncoder
from .encoder_manager import EncoderManager

__all__ = [
    'BaseEncoder',
    'EncodedVector',
    'DenseEncoder',
    'SparseEncoder',
    'HybridEncoder',
    'EncoderManager',
]
