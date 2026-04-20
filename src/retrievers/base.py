"""
检索器基类
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from src.vector_stores.base import SearchResult


class BaseRetriever(ABC):
    """检索器基类"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化检索器
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
    
    @abstractmethod
    def retrieve(self, query: str, top_k: int = 5) -> List[SearchResult]:
        """
        检索相关文档
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            
        Returns:
            搜索结果列表
        """
        pass
    
    def retrieve_batch(
        self,
        queries: List[str],
        top_k: int = 5
    ) -> List[List[SearchResult]]:
        """
        批量检索
        
        Args:
            queries: 查询文本列表
            top_k: 每个查询返回结果数量
            
        Returns:
            搜索结果列表的列表
        """
        return [self.retrieve(query, top_k) for query in queries]
