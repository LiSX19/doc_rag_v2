"""
向量数据库基类
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


class SearchResult:
    """搜索结果类"""
    
    def __init__(
        self,
        id: str,
        content: str,
        score: float,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        初始化搜索结果
        
        Args:
            id: 文档ID
            content: 文档内容
            score: 相似度分数
            metadata: 元数据
        """
        self.id = id
        self.content = content
        self.score = score
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'content': self.content,
            'score': self.score,
            'metadata': self.metadata,
        }


class BaseVectorStore(ABC):
    """向量数据库基类"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化向量数据库
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        self.is_initialized = False
    
    @abstractmethod
    def initialize(self):
        """初始化数据库连接"""
        pass
    
    @abstractmethod
    def add(
        self,
        ids: List[str],
        embeddings: np.ndarray,
        contents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None
    ):
        """
        添加文档
        
        Args:
            ids: 文档ID列表
            embeddings: Embedding向量，形状为 (N, D)
            contents: 文档内容列表
            metadatas: 元数据列表
        """
        pass
    
    @abstractmethod
    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        搜索相似文档
        
        Args:
            query_embedding: 查询向量
            top_k: 返回结果数量
            filter_dict: 过滤条件
            
        Returns:
            搜索结果列表
        """
        pass
    
    @abstractmethod
    def delete(self, ids: List[str]):
        """
        删除文档
        
        Args:
            ids: 文档ID列表
        """
        pass

    def get_existing_ids(self) -> List[str]:
        """
        获取向量数据库中所有已存储的文档ID

        Returns:
            已存储的ID列表（默认返回空列表）
        """
        return []

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """
        获取数据库统计信息
        
        Returns:
            统计信息字典
        """
        pass
