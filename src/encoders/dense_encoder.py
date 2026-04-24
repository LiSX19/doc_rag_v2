"""
稠密向量编码器

使用深度学习模型（如 BGE、BERT）生成稠密向量表示
"""

from typing import Any, Dict, List, Optional, Union

import numpy as np
from sentence_transformers import SentenceTransformer

from src.utils import get_logger, OutputManager

from .base import BaseEncoder, EncodedVector

logger = get_logger(__name__)


class DenseEncoder(BaseEncoder):
    """稠密向量编码器
    
    基于 SentenceTransformer 的稠密向量编码实现
    支持 BGE、BERT 等模型
    
    Attributes:
        model: SentenceTransformer 模型实例
        model_name: 模型名称或路径
        device: 运行设备 (cpu/cuda)
        normalize: 是否归一化向量
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化稠密向量编码器
        
        Args:
            config: 配置字典，包含:
                - encoder.dense.model_name: 模型名称 (默认: BAAI/bge-small-zh-v1.5)
                - encoder.dense.model_path: 本地模型路径（优先使用）
                - encoder.dense.device: 设备 (auto/cpu/cuda)
                - encoder.dense.normalize: 是否归一化 (默认: True)
                - encoder.dense.batch_size: 批处理大小 (默认: 32)
                - encoder.dense.max_seq_length: 最大序列长度 (默认: 512)
        """
        super().__init__(config)
        
        # 读取编码器配置
        encoder_config = self.config.get('encoder', {})
        dense_config = encoder_config.get('dense', {})
        
        # 模型配置
        self.model_name = dense_config.get('model_name', 'BAAI/bge-small-zh-v1.5')
        self.model_path = dense_config.get('model_path')
        self.device = dense_config.get('device', 'auto')
        self.normalize = dense_config.get('normalize', True)
        self.batch_size = dense_config.get('batch_size', 32)
        self.max_seq_length = dense_config.get('max_seq_length', 512)
        
        # 指令前缀（BGE模型推荐）
        self.instruction = dense_config.get('instruction', '为这个句子生成表示以用于检索相关文章：')
        self.use_instruction = dense_config.get('use_instruction', True)
        
        # 模型实例
        self.model: Optional[SentenceTransformer] = None
        self._dimension: Optional[int] = None
        
        # 输出管理器
        self.output_manager = OutputManager(config)
    
    def initialize(self):
        """初始化编码器，加载模型"""
        if self.is_initialized:
            return
        
        try:
            # 确定模型路径
            model_path = self.model_path or self.model_name
            
            # 自动选择设备
            if self.device == 'auto':
                import torch
                self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
            
            logger.info(f"正在加载稠密向量模型: {model_path} (设备: {self.device})")
            
            # 加载模型
            self.model = SentenceTransformer(model_path, device=self.device)
            
            # 设置最大序列长度
            if self.max_seq_length:
                self.model.max_seq_length = self.max_seq_length
            
            # 获取维度
            self._dimension = self.model.get_sentence_embedding_dimension()
            
            self.is_initialized = True
            logger.info(f"稠密向量模型加载完成，维度: {self._dimension}")
            
        except Exception as e:
            logger.error(f"加载稠密向量模型失败: {e}")
            raise
    
    def encode(self, text: str, chunk_id: Optional[str] = None) -> EncodedVector:
        """
        编码单个文本
        
        Args:
            text: 要编码的文本
            chunk_id: 分块ID
            
        Returns:
            编码向量
        """
        if not self.is_initialized:
            self.initialize()
        
        # 添加指令前缀
        if self.use_instruction and self.instruction:
            text_to_encode = self.instruction + text
        else:
            text_to_encode = text
        
        # 生成向量
        vector = self.model.encode(
            text_to_encode,
            normalize_embeddings=self.normalize,
            convert_to_numpy=True
        )
        
        return EncodedVector(
            chunk_id=chunk_id or '',
            content=text,
            dense_vector=vector.astype(np.float32),
            metadata={
                'model': self.model_name,
                'vector_type': 'dense',
                'normalized': self.normalize,
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
            编码向量列表
        """
        if not self.is_initialized:
            self.initialize()
        
        if not texts:
            return []
        
        # 确保 chunk_ids 长度匹配
        if chunk_ids is None:
            chunk_ids = [None] * len(texts)
        
        # 添加指令前缀
        if self.use_instruction and self.instruction:
            texts_to_encode = [self.instruction + text for text in texts]
        else:
            texts_to_encode = texts
        
        # 批量生成向量
        vectors = self.model.encode(
            texts_to_encode,
            batch_size=self.batch_size,
            normalize_embeddings=self.normalize,
            convert_to_numpy=True,
            show_progress_bar=len(texts) > 100
        )
        
        # 构建结果
        results = []
        for i, (text, vector) in enumerate(zip(texts, vectors)):
            results.append(EncodedVector(
                chunk_id=chunk_ids[i] or '',
                content=text,
                dense_vector=vector.astype(np.float32),
                metadata={
                    'model': self.model_name,
                    'vector_type': 'dense',
                    'normalized': self.normalize,
                    'batch_index': i,
                }
            ))
        
        return results
    
    @property
    def dimension(self) -> int:
        """返回向量维度"""
        if self._dimension is None:
            self.initialize()
        return self._dimension
    
    @property
    def vector_type(self) -> str:
        """返回向量类型"""
        return 'dense'
    
    def encode_and_save(
        self,
        texts: List[str],
        filename: str,
        chunk_ids: Optional[List[str]] = None,
        metadata: Optional[Dict] = None
    ) -> List[EncodedVector]:
        """
        编码并保存结果
        
        Args:
            texts: 文本列表
            filename: 文件名（用于保存）
            chunk_ids: 分块ID列表
            metadata: 额外元数据
            
        Returns:
            编码向量列表
        """
        # 执行编码
        encoded_vectors = self.encode_batch(texts, chunk_ids)
        
        # 提取稠密向量
        embeddings = np.array([ev.dense_vector for ev in encoded_vectors])
        
        # 保存
        self.output_manager.save_embeddings(
            filename=filename,
            embeddings=embeddings,
            metadata={
                'model': self.model_name,
                'vector_type': 'dense',
                'count': len(texts),
                'dimension': self.dimension,
                **(metadata or {})
            }
        )
        
        return encoded_vectors
    
    def embed(self, texts: Union[str, List[str]]) -> np.ndarray:
        """
        生成文本的embedding（兼容BaseEmbedder接口）
        
        Args:
            texts: 单个文本或文本列表
            
        Returns:
            Embedding向量，形状为 (N, D) 其中N是文本数量，D是向量维度
        """
        if not self.is_initialized:
            self.initialize()
        
        # 确保是列表
        if isinstance(texts, str):
            texts = [texts]
        
        if not texts:
            return np.array([])
        
        # 添加指令前缀
        if self.use_instruction and self.instruction:
            texts_to_encode = [self.instruction + text for text in texts]
        else:
            texts_to_encode = texts
        
        # 生成embedding
        embeddings = self.model.encode(
            texts_to_encode,
            batch_size=self.batch_size,
            normalize_embeddings=self.normalize,
            convert_to_numpy=True,
            show_progress_bar=len(texts) > 100
        )
        
        return embeddings
    
    def embed_chunks(self, chunks: List[Any]) -> np.ndarray:
        """
        为文本块生成embedding（兼容BaseEmbedder接口）
        
        Args:
            chunks: 文本块列表，每个块需要有content属性
            
        Returns:
            Embedding向量
        """
        from typing import Any
        
        texts = []
        for chunk in chunks:
            # 支持不同格式的分块对象
            if hasattr(chunk, 'content'):
                texts.append(chunk.content)
            elif isinstance(chunk, dict):
                texts.append(chunk.get('content', ''))
            else:
                texts.append(str(chunk))
        
        return self.embed(texts)
    
    def load_model(self):
        """加载模型（兼容BaseEmbedder接口）"""
        self.initialize()
    
    @property
    def is_loaded(self) -> bool:
        """模型是否已加载（兼容BaseEmbedder接口）"""
        return self.is_initialized
