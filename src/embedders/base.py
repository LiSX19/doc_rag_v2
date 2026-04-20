"""
Embedding基类
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

import numpy as np


class BaseEmbedder(ABC):
    """Embedding基类"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化Embedder
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        self.model = None
        self.is_loaded = False
    
    @abstractmethod
    def load_model(self):
        """加载模型"""
        pass
    
    @abstractmethod
    def embed(self, texts: Union[str, List[str]]) -> np.ndarray:
        """
        生成文本的embedding
        
        Args:
            texts: 单个文本或文本列表
            
        Returns:
            Embedding向量，形状为 (N, D) 其中N是文本数量，D是向量维度
        """
        pass
    
    def embed_chunks(self, chunks: List[Any]) -> np.ndarray:
        """
        为文本块生成embedding
        
        Args:
            chunks: 文本块列表，每个块需要有content属性
            
        Returns:
            Embedding向量
        """
        texts = [chunk.content for chunk in chunks]
        return self.embed(texts)
    
    @property
    @abstractmethod
    def dimension(self) -> int:
        """返回embedding维度"""
        pass
