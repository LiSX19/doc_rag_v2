"""
编码器基类

定义编码器的抽象接口和通用数据结构
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

import numpy as np


@dataclass
class EncodedVector:
    """编码向量数据类
    
    统一表示各种编码结果（稠密向量、稀疏向量、混合向量）
    
    Attributes:
        chunk_id: 分块唯一ID
        content: 原始文本内容
        dense_vector: 稠密向量 (可选)
        sparse_vector: 稀疏向量，格式为 {索引: 权重} 字典 (可选)
        metadata: 元数据
    """
    chunk_id: str
    content: str
    dense_vector: Optional[np.ndarray] = None
    sparse_vector: Optional[Dict[int, float]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            'chunk_id': self.chunk_id,
            'content': self.content,
            'metadata': self.metadata,
        }
        
        if self.dense_vector is not None:
            result['dense_vector'] = self.dense_vector.tolist()
            result['dense_dim'] = len(self.dense_vector)
        
        if self.sparse_vector is not None:
            result['sparse_vector'] = self.sparse_vector
            result['sparse_dim'] = max(self.sparse_vector.keys()) + 1 if self.sparse_vector else 0
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EncodedVector':
        """从字典创建"""
        dense_vector = None
        if 'dense_vector' in data:
            dense_vector = np.array(data['dense_vector'], dtype=np.float32)
        
        return cls(
            chunk_id=data['chunk_id'],
            content=data['content'],
            dense_vector=dense_vector,
            sparse_vector=data.get('sparse_vector'),
            metadata=data.get('metadata', {})
        )
    
    @property
    def has_dense(self) -> bool:
        """是否有稠密向量"""
        return self.dense_vector is not None
    
    @property
    def has_sparse(self) -> bool:
        """是否有稀疏向量"""
        return self.sparse_vector is not None and len(self.sparse_vector) > 0
    
    @property
    def is_hybrid(self) -> bool:
        """是否是混合向量（同时有稠密和稀疏）"""
        return self.has_dense and self.has_sparse


class BaseEncoder(ABC):
    """编码器基类
    
    所有编码器的抽象基类，定义统一的编码接口
    
    子类需要实现:
    - encode(): 编码文本
    - encode_batch(): 批量编码
    - dimension: 向量维度属性
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化编码器
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        self.is_initialized = False
    
    @abstractmethod
    def initialize(self):
        """初始化编码器（加载模型等）"""
        pass
    
    @abstractmethod
    def encode(self, text: str, chunk_id: Optional[str] = None) -> EncodedVector:
        """
        编码单个文本
        
        Args:
            text: 要编码的文本
            chunk_id: 分块ID（可选）
            
        Returns:
            编码向量
        """
        pass
    
    @abstractmethod
    def encode_batch(
        self,
        texts: List[str],
        chunk_ids: Optional[List[str]] = None
    ) -> List[EncodedVector]:
        """
        批量编码文本
        
        Args:
            texts: 文本列表
            chunk_ids: 分块ID列表（可选）
            
        Returns:
            编码向量列表
        """
        pass
    
    @property
    @abstractmethod
    def dimension(self) -> int:
        """返回向量维度"""
        pass
    
    @property
    @abstractmethod
    def vector_type(self) -> str:
        """返回向量类型 ('dense', 'sparse', 'hybrid')"""
        pass
    
    def encode_chunks(self, chunks: List[Any]) -> List[EncodedVector]:
        """
        编码分块对象列表
        
        Args:
            chunks: 分块对象列表，每个对象需要有 content 和 chunk_id 属性
            
        Returns:
            编码向量列表
        """
        texts = []
        chunk_ids = []
        
        for chunk in chunks:
            # 支持不同格式的分块对象
            if hasattr(chunk, 'content'):
                texts.append(chunk.content)
            elif isinstance(chunk, dict):
                texts.append(chunk.get('content', ''))
            else:
                texts.append(str(chunk))
            
            # 获取chunk_id
            if hasattr(chunk, 'chunk_id'):
                chunk_ids.append(chunk.chunk_id)
            elif isinstance(chunk, dict) and 'chunk_id' in chunk:
                chunk_ids.append(chunk['chunk_id'])
            else:
                chunk_ids.append(None)
        
        return self.encode_batch(texts, chunk_ids)
