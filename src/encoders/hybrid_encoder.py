"""
混合编码器

结合稠密向量和稀疏向量的优势，生成混合表示
适用于需要同时考虑语义相似性和关键词匹配的场景
"""

from typing import Any, Dict, List, Optional, Union

import numpy as np

from src.utils import get_logger

from .base import BaseEncoder, EncodedVector
from .dense_encoder import DenseEncoder
from .sparse_encoder import BM25Encoder, TFIDFEncoder

logger = get_logger(__name__)


class HybridEncoder(BaseEncoder):
    """混合编码器
    
    同时生成稠密向量和稀疏向量，结合两者的优势：
    - 稠密向量：捕捉语义相似性
    - 稀疏向量：捕捉关键词匹配
    
    Attributes:
        dense_encoder: 稠密向量编码器
        sparse_encoder: 稀疏向量编码器
        dense_weight: 稠密向量权重
        sparse_weight: 稀疏向量权重
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化混合编码器
        
        Args:
            config: 配置字典，包含:
                - encoder.hybrid.dense_weight: 稠密向量权重 (默认: 0.7)
                - encoder.hybrid.sparse_weight: 稀疏向量权重 (默认: 0.3)
                - encoder.hybrid.dense_config: 稠密编码器配置
                - encoder.hybrid.sparse_config: 稀疏编码器配置
                - encoder.hybrid.sparse_type: 稀疏编码器类型 ('bm25' 或 'tfidf')
        """
        super().__init__(config)
        
        # 读取配置
        encoder_config = self.config.get('encoder', {})
        hybrid_config = encoder_config.get('hybrid', {})
        
        # 权重配置
        self.dense_weight = hybrid_config.get('dense_weight', 0.7)
        self.sparse_weight = hybrid_config.get('sparse_weight', 0.3)
        
        # 归一化权重
        total_weight = self.dense_weight + self.sparse_weight
        if total_weight > 0:
            self.dense_weight /= total_weight
            self.sparse_weight /= total_weight
        
        # 子编码器配置
        self.sparse_type = hybrid_config.get('sparse_type', 'bm25')
        
        # 创建子编码器配置
        dense_config = hybrid_config.get('dense_config', {})
        sparse_config = hybrid_config.get('sparse_config', {})
        
        # 构建完整的配置字典
        dense_full_config = self.config.copy()
        dense_full_config['encoder'] = dense_full_config.get('encoder', {})
        dense_full_config['encoder']['dense'] = dense_config
        
        sparse_full_config = self.config.copy()
        sparse_full_config['encoder'] = sparse_full_config.get('encoder', {})
        sparse_full_config['encoder']['sparse'] = sparse_config
        
        # 初始化子编码器
        self.dense_encoder = DenseEncoder(dense_full_config)
        
        if self.sparse_type == 'tfidf':
            self.sparse_encoder = TFIDFEncoder(sparse_full_config)
        else:
            self.sparse_encoder = BM25Encoder(sparse_full_config)
        
        # 是否已拟合
        self._is_fitted = False
    
    def initialize(self):
        """初始化子编码器"""
        self.dense_encoder.initialize()
        self.sparse_encoder.initialize()
        self.is_initialized = True
    
    def fit(self, texts: List[str]):
        """
        拟合稀疏编码器
        
        Args:
            texts: 文档集合
        """
        if not self.is_initialized:
            self.initialize()
        
        logger.info(f"拟合混合编码器，文档数: {len(texts)}")
        
        # 拟合稀疏编码器
        self.sparse_encoder.fit(texts)
        
        self._is_fitted = True
        logger.info("混合编码器拟合完成")
    
    def encode(self, text: str, chunk_id: Optional[str] = None) -> EncodedVector:
        """
        编码单个文本
        
        Args:
            text: 要编码的文本
            chunk_id: 分块ID
            
        Returns:
            混合编码向量
        """
        if not self.is_initialized:
            self.initialize()
        
        # 分别编码
        dense_result = self.dense_encoder.encode(text, chunk_id)
        sparse_result = self.sparse_encoder.encode(text, chunk_id)
        
        # 合并结果
        return EncodedVector(
            chunk_id=chunk_id or '',
            content=text,
            dense_vector=dense_result.dense_vector,
            sparse_vector=sparse_result.sparse_vector,
            metadata={
                'vector_type': 'hybrid',
                'dense_weight': self.dense_weight,
                'sparse_weight': self.sparse_weight,
                'dense_model': self.dense_encoder.model_name,
                'sparse_algorithm': self.sparse_encoder.vector_type,
            }
        )
    
    def encode_batch(
        self,
        texts: List[str],
        chunk_ids: Optional[List[str]] = None
    ) -> List[EncodedVector]:
        """
        批量编码文本
        
        Args:
            texts: 文本列表
            chunk_ids: 分块ID列表
            
        Returns:
            混合编码向量列表
        """
        if not self.is_initialized:
            self.initialize()
        
        if not texts:
            return []
        
        # 确保 chunk_ids 长度匹配
        if chunk_ids is None:
            chunk_ids = [None] * len(texts)
        
        # 分别批量编码
        dense_results = self.dense_encoder.encode_batch(texts, chunk_ids)
        sparse_results = self.sparse_encoder.encode_batch(texts, chunk_ids)
        
        # 合并结果
        results = []
        for i, (dense, sparse) in enumerate(zip(dense_results, sparse_results)):
            results.append(EncodedVector(
                chunk_id=chunk_ids[i] or '',
                content=texts[i],
                dense_vector=dense.dense_vector,
                sparse_vector=sparse.sparse_vector,
                metadata={
                    'vector_type': 'hybrid',
                    'dense_weight': self.dense_weight,
                    'sparse_weight': self.sparse_weight,
                    'dense_model': self.dense_encoder.model_name,
                    'sparse_algorithm': self.sparse_encoder.vector_type,
                    'batch_index': i,
                }
            ))
        
        return results
    
    @property
    def dimension(self) -> int:
        """返回稠密向量维度"""
        return self.dense_encoder.dimension
    
    @property
    def sparse_dimension(self) -> int:
        """返回稀疏向量维度"""
        return self.sparse_encoder.dimension
    
    @property
    def vector_type(self) -> str:
        """返回向量类型"""
        return 'hybrid'
    
    def compute_similarity(
        self,
        vec1: EncodedVector,
        vec2: EncodedVector
    ) -> float:
        """
        计算两个混合向量的相似度
        
        综合稠密向量和稀疏向量的相似度，按权重加权
        
        Args:
            vec1: 第一个向量
            vec2: 第二个向量
            
        Returns:
            综合相似度分数 (0-1)
        """
        total_similarity = 0.0
        
        # 稠密向量相似度（余弦相似度）
        if vec1.has_dense and vec2.has_dense:
            dense_sim = self._cosine_similarity(vec1.dense_vector, vec2.dense_vector)
            total_similarity += self.dense_weight * dense_sim
        
        # 稀疏向量相似度（点积归一化）
        if vec1.has_sparse and vec2.has_sparse:
            sparse_sim = self._sparse_similarity(vec1.sparse_vector, vec2.sparse_vector)
            total_similarity += self.sparse_weight * sparse_sim
        
        return total_similarity
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """计算余弦相似度"""
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(np.dot(vec1, vec2) / (norm1 * norm2))
    
    def _sparse_similarity(
        self,
        vec1: Dict[int, float],
        vec2: Dict[int, float]
    ) -> float:
        """计算稀疏向量相似度"""
        # 计算点积
        dot_product = 0.0
        for idx, weight in vec1.items():
            if idx in vec2:
                dot_product += weight * vec2[idx]
        
        # 计算范数
        norm1 = math.sqrt(sum(w ** 2 for w in vec1.values()))
        norm2 = math.sqrt(sum(w ** 2 for w in vec2.values()))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)


import math
