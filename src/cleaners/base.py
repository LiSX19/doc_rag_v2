"""
文本清洗器基类
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseCleaner(ABC):
    """文本清洗器基类"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化清洗器
        
        Args:
            config: 清洗器配置
        """
        self.config = config or {}
    
    @abstractmethod
    def clean(self, text: str) -> str:
        """
        清洗文本
        
        Args:
            text: 原始文本
            
        Returns:
            清洗后的文本
        """
        pass
    
    def clean_batch(self, texts: List[str]) -> List[str]:
        """
        批量清洗文本
        
        Args:
            texts: 文本列表
            
        Returns:
            清洗后的文本列表
        """
        return [self.clean(text) for text in texts]
