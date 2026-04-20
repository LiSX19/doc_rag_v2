"""
文本分块器基类
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class TextChunk:
    """文本块类"""
    
    def __init__(
        self,
        content: str,
        index: int,
        metadata: Optional[Dict[str, Any]] = None,
        start_pos: int = 0,
        end_pos: int = 0
    ):
        """
        初始化文本块
        
        Args:
            content: 块内容
            index: 块索引
            metadata: 元数据
            start_pos: 在原文中的起始位置
            end_pos: 在原文中的结束位置
        """
        self.content = content
        self.index = index
        self.metadata = metadata or {}
        self.start_pos = start_pos
        self.end_pos = end_pos
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'content': self.content,
            'index': self.index,
            'metadata': self.metadata,
            'start_pos': self.start_pos,
            'end_pos': self.end_pos,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TextChunk':
        """从字典创建"""
        return cls(
            content=data['content'],
            index=data['index'],
            metadata=data.get('metadata', {}),
            start_pos=data.get('start_pos', 0),
            end_pos=data.get('end_pos', 0),
        )


class BaseChunker(ABC):
    """文本分块器基类"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化分块器
        
        Args:
            config: 分块器配置
        """
        self.config = config or {}
    
    @abstractmethod
    def split(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[TextChunk]:
        """
        分割文本
        
        Args:
            text: 原始文本
            metadata: 文档元数据
            
        Returns:
            文本块列表
        """
        pass
    
    def split_batch(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None
    ) -> List[List[TextChunk]]:
        """
        批量分割文本
        
        Args:
            texts: 文本列表
            metadatas: 元数据列表
            
        Returns:
            文本块列表的列表
        """
        if metadatas is None:
            metadatas = [None] * len(texts)
        
        return [self.split(text, meta) for text, meta in zip(texts, metadatas)]
