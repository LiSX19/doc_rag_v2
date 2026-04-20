"""
BGE Embedding实现
"""

from typing import Any, Dict, List, Optional, Union

import numpy as np
from sentence_transformers import SentenceTransformer
from src.utils import OutputManager, get_logger

from .base import BaseEmbedder

logger = get_logger(__name__)


class BGEEmbedder(BaseEmbedder):
    """BGE Embedding模型"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化BGE Embedder
        
        Args:
            config: 配置字典，包含：
                - model.name: 模型名称
                - model.path: 模型本地路径
                - model.device: 设备 (cpu/cuda/auto)
                - model.normalize_embeddings: 是否归一化
                - batch_size: 批处理大小
        """
        super().__init__(config)
        
        # 读取 embedder 配置（适配 configs.yaml 结构）
        embedder_config = self.config.get('embedder', self.config)
        
        model_config = embedder_config.get('model', {})
        self.model_name = model_config.get('name', 'BAAI/bge-small-zh-v1.5')
        self.model_path = model_config.get('path')
        self.device = model_config.get('device', 'auto')
        self.normalize_embeddings = model_config.get('normalize_embeddings', True)
        
        self.batch_size = embedder_config.get('batch_size', 32)
        
        # 输出管理器
        self.output_manager = OutputManager(config)
    
    def load_model(self):
        """加载模型"""
        if self.is_loaded:
            return
        
        # 优先使用本地路径
        model_path = self.model_path or self.model_name
        
        # 自动选择设备
        if self.device == 'auto':
            import torch
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        
        self.model = SentenceTransformer(model_path, device=self.device)
        self.is_loaded = True
    
    def embed(self, texts: Union[str, List[str]]) -> np.ndarray:
        """
        生成文本的embedding
        
        Args:
            texts: 单个文本或文本列表
            
        Returns:
            Embedding向量
        """
        if not self.is_loaded:
            self.load_model()
        
        # 确保是列表
        if isinstance(texts, str):
            texts = [texts]
        
        # 添加指令前缀（BGE模型推荐）
        instruction = "为这个句子生成表示以用于检索相关文章："
        texts = [instruction + text for text in texts]
        
        # 生成embedding
        embeddings = self.model.encode(
            texts,
            batch_size=self.batch_size,
            normalize_embeddings=self.normalize_embeddings,
            show_progress_bar=len(texts) > 100
        )
        
        return embeddings
    
    def embed_and_save(
        self,
        texts: Union[str, List[str]],
        filename: str,
        metadata: Optional[Dict] = None
    ) -> np.ndarray:
        """
        生成embedding并保存
        
        Args:
            texts: 文本或文本列表
            filename: 文件名（用于保存输出）
            metadata: 元数据
            
        Returns:
            Embedding数组
        """
        embeddings = self.embed(texts)
        
        # 保存embedding
        self.output_manager.save_embeddings(
            filename=filename,
            embeddings=embeddings,
            metadata={
                'model': self.model_name,
                'count': len(texts) if isinstance(texts, list) else 1,
                **(metadata or {})
            }
        )
        
        return embeddings
    
    @property
    def dimension(self) -> int:
        """返回embedding维度"""
        if not self.is_loaded:
            self.load_model()
        return self.model.get_sentence_embedding_dimension()
