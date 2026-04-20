"""
去重器基类
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set, Tuple

from src.chunkers.base import TextChunk


class DedupResult:
    """去重结果类"""
    
    def __init__(
        self,
        chunks: List[TextChunk],
        removed_chunks: List[TextChunk],
        duplicate_groups: List[List[int]],
        stats: Optional[Dict[str, Any]] = None
    ):
        """
        初始化去重结果
        
        Args:
            chunks: 保留的文本块
            removed_chunks: 移除的重复文本块
            duplicate_groups: 重复组（每组包含重复块的索引）
            stats: 统计信息
        """
        self.chunks = chunks
        self.removed_chunks = removed_chunks
        self.duplicate_groups = duplicate_groups
        self.stats = stats or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'kept_count': len(self.chunks),
            'removed_count': len(self.removed_chunks),
            'duplicate_groups': self.duplicate_groups,
            'stats': self.stats,
        }


class BaseDeduper(ABC):
    """去重器基类"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化去重器
        
        Args:
            config: 去重器配置
        """
        self.config = config or {}
    
    @abstractmethod
    def deduplicate(self, chunks: List[TextChunk]) -> DedupResult:
        """
        去重
        
        Args:
            chunks: 文本块列表
            
        Returns:
            去重结果
        """
        pass
    
    def calculate_stats(self, original_count: int, kept_count: int) -> Dict[str, Any]:
        """
        计算去重统计信息
        
        Args:
            original_count: 原始块数
            kept_count: 保留块数
            
        Returns:
            统计信息字典
        """
        removed_count = original_count - kept_count
        dedup_rate = removed_count / original_count if original_count > 0 else 0
        
        return {
            'original_count': original_count,
            'kept_count': kept_count,
            'removed_count': removed_count,
            'dedup_rate': round(dedup_rate, 4),
        }
