"""
编码管理器

负责管理编码器的生命周期、批量编码和结果存储
支持增量编码和编码缓存
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np

from src.chunkers.chunk_manager import ChunkDatabase, ChunkRecord
from src.utils import get_logger, OutputManager

from .base import BaseEncoder, EncodedVector
from .dense_encoder import DenseEncoder
from .hybrid_encoder import HybridEncoder
from .sparse_encoder import BM25Encoder, TFIDFEncoder

logger = get_logger(__name__)


class EncodingRecord:
    """编码记录"""
    
    def __init__(
        self,
        chunk_id: str,
        content_hash: str,
        dense_vector_path: Optional[str] = None,
        sparse_vector_path: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        encoded_at: Optional[str] = None
    ):
        self.chunk_id = chunk_id
        self.content_hash = content_hash
        self.dense_vector_path = dense_vector_path
        self.sparse_vector_path = sparse_vector_path
        self.metadata = metadata or {}
        self.encoded_at = encoded_at or datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'chunk_id': self.chunk_id,
            'content_hash': self.content_hash,
            'dense_vector_path': self.dense_vector_path,
            'sparse_vector_path': self.sparse_vector_path,
            'metadata': self.metadata,
            'encoded_at': self.encoded_at,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EncodingRecord':
        return cls(
            chunk_id=data['chunk_id'],
            content_hash=data['content_hash'],
            dense_vector_path=data.get('dense_vector_path'),
            sparse_vector_path=data.get('sparse_vector_path'),
            metadata=data.get('metadata', {}),
            encoded_at=data.get('encoded_at'),
        )


class EncodingDatabase:
    """编码数据库"""
    
    def __init__(self, db_path: Union[str, Path]):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.records: Dict[str, EncodingRecord] = {}
        self._load()
    
    def _load(self):
        """加载数据库"""
        if not self.db_path.exists():
            return
        
        try:
            with open(self.db_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for record_data in data.get('records', []):
                record = EncodingRecord.from_dict(record_data)
                self.records[record.chunk_id] = record
            
            logger.info(f"已加载 {len(self.records)} 条编码记录")
        except Exception as e:
            logger.error(f"加载编码数据库失败: {e}")
            self.records = {}
    
    def _save(self):
        """保存数据库"""
        try:
            data = {
                'records': [r.to_dict() for r in self.records.values()],
                'updated_at': datetime.now().isoformat(),
            }
            
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存编码数据库失败: {e}")
    
    def add_record(self, record: EncodingRecord):
        """添加记录"""
        self.records[record.chunk_id] = record
        self._save()
    
    def add_records(self, records: List[EncodingRecord]):
        """批量添加记录"""
        for record in records:
            self.records[record.chunk_id] = record
        self._save()
    
    def get_record(self, chunk_id: str) -> Optional[EncodingRecord]:
        """获取记录"""
        return self.records.get(chunk_id)
    
    def check_content_hash(self, chunk_id: str, content_hash: str) -> bool:
        """检查内容哈希是否匹配"""
        record = self.records.get(chunk_id)
        if not record:
            return False
        return record.content_hash == content_hash
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'total_records': len(self.records),
            'db_path': str(self.db_path),
        }


class EncoderManager:
    """编码管理器
    
    管理编码器的创建、配置和批量编码操作
    支持编码缓存和增量编码
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化编码管理器
        
        Args:
            config: 配置字典，包含:
                - encoder.type: 编码器类型 ('dense', 'sparse', 'hybrid')
                - encoder.cache_dir: 缓存目录
                - encoder.incremental: 是否启用增量编码
        """
        self.config = config or {}
        
        # 读取编码器配置
        encoder_config = self.config.get('encoder', {})
        self.encoder_type = encoder_config.get('type', 'dense')
        self.cache_dir = Path(encoder_config.get('cache_dir', './cache/encodings'))
        self.incremental = encoder_config.get('incremental', True)
        
        # 创建缓存目录
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化数据库
        db_path = self.cache_dir / 'encoding_db.json'
        self.db = EncodingDatabase(db_path)
        
        # 初始化输出管理器
        self.output_manager = OutputManager(config)
        
        # 编码器实例（懒加载）
        self._encoder: Optional[BaseEncoder] = None
        
        logger.info(f"编码管理器初始化完成，类型: {self.encoder_type}")
    
    @property
    def encoder(self) -> BaseEncoder:
        """获取编码器实例（懒加载）"""
        if self._encoder is None:
            self._encoder = self._create_encoder()
        return self._encoder
    
    def _create_encoder(self) -> BaseEncoder:
        """创建编码器实例"""
        if self.encoder_type == 'dense':
            return DenseEncoder(self.config)
        elif self.encoder_type == 'sparse':
            return BM25Encoder(self.config)
        elif self.encoder_type == 'hybrid':
            return HybridEncoder(self.config)
        else:
            raise ValueError(f"未知的编码器类型: {self.encoder_type}")
    
    def initialize(self):
        """初始化编码器"""
        self.encoder.initialize()
    
    def fit(self, texts: List[str]):
        """
        拟合编码器（用于稀疏编码器）
        
        Args:
            texts: 文档集合
        """
        self.initialize()
        
        if hasattr(self.encoder, 'fit'):
            self.encoder.fit(texts)
    
    def compute_content_hash(self, content: str) -> str:
        """计算内容哈希"""
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def encode_chunks(
        self,
        chunks: List[Union[ChunkRecord, Dict[str, Any]]],
        use_cache: bool = True
    ) -> List[EncodedVector]:
        """
        编码分块列表
        
        Args:
            chunks: 分块列表
            use_cache: 是否使用缓存
            
        Returns:
            编码向量列表
        """
        self.initialize()
        
        if not chunks:
            return []
        
        results = []
        chunks_to_encode = []
        
        # 检查缓存
        for chunk in chunks:
            # 提取信息
            if isinstance(chunk, ChunkRecord):
                chunk_id = chunk.chunk_id
                content = chunk.content
            elif isinstance(chunk, dict):
                chunk_id = chunk.get('chunk_id', '')
                content = chunk.get('content', '')
            else:
                chunk_id = getattr(chunk, 'chunk_id', '')
                content = getattr(chunk, 'content', str(chunk))
            
            # 检查是否需要编码
            content_hash = self.compute_content_hash(content)
            
            if use_cache and self.incremental:
                record = self.db.get_record(chunk_id)
                if record and record.content_hash == content_hash:
                    # 从缓存加载
                    cached_vector = self._load_cached_vector(record)
                    if cached_vector:
                        results.append((chunk_id, cached_vector))
                        continue
            
            chunks_to_encode.append({
                'chunk_id': chunk_id,
                'content': content,
                'content_hash': content_hash,
            })
        
        # 批量编码新分块
        if chunks_to_encode:
            logger.info(f"编码 {len(chunks_to_encode)} 个新分块")
            
            texts = [c['content'] for c in chunks_to_encode]
            chunk_ids = [c['chunk_id'] for c in chunks_to_encode]
            
            encoded_vectors = self.encoder.encode_batch(texts, chunk_ids)
            
            # 保存到缓存
            if use_cache and self.incremental:
                self._save_encoded_vectors(chunks_to_encode, encoded_vectors)
            
            # 添加到结果
            for chunk_info, vector in zip(chunks_to_encode, encoded_vectors):
                results.append((chunk_info['chunk_id'], vector))
        
        # 按原始顺序排序
        chunk_id_order = {c.chunk_id if isinstance(c, ChunkRecord) else c.get('chunk_id', ''): i 
                         for i, c in enumerate(chunks)}
        results.sort(key=lambda x: chunk_id_order.get(x[0], 0))
        
        return [vector for _, vector in results]
    
    def _load_cached_vector(self, record: EncodingRecord) -> Optional[EncodedVector]:
        """从缓存加载向量"""
        try:
            dense_vector = None
            sparse_vector = None
            
            # 加载稠密向量
            if record.dense_vector_path and Path(record.dense_vector_path).exists():
                dense_vector = np.load(record.dense_vector_path)
            
            # 加载稀疏向量
            if record.sparse_vector_path and Path(record.sparse_vector_path).exists():
                with open(record.sparse_vector_path, 'r', encoding='utf-8') as f:
                    sparse_data = json.load(f)
                    sparse_vector = {int(k): v for k, v in sparse_data.items()}
            
            if dense_vector is not None or sparse_vector is not None:
                return EncodedVector(
                    chunk_id=record.chunk_id,
                    content='',  # 缓存中不存储内容
                    dense_vector=dense_vector,
                    sparse_vector=sparse_vector,
                    metadata=record.metadata
                )
        except Exception as e:
            logger.warning(f"加载缓存向量失败: {e}")
        
        return None
    
    def _save_encoded_vectors(
        self,
        chunks_info: List[Dict[str, Any]],
        encoded_vectors: List[EncodedVector]
    ):
        """保存编码结果到缓存"""
        records = []
        
        for chunk_info, vector in zip(chunks_info, encoded_vectors):
            dense_path = None
            sparse_path = None
            
            # 保存稠密向量
            if vector.has_dense:
                dense_path = self.cache_dir / f"{chunk_info['chunk_id']}_dense.npy"
                np.save(dense_path, vector.dense_vector)
                dense_path = str(dense_path)
            
            # 保存稀疏向量
            if vector.has_sparse:
                sparse_path = self.cache_dir / f"{chunk_info['chunk_id']}_sparse.json"
                with open(sparse_path, 'w', encoding='utf-8') as f:
                    json.dump(vector.sparse_vector, f)
                sparse_path = str(sparse_path)
            
            # 创建记录
            record = EncodingRecord(
                chunk_id=chunk_info['chunk_id'],
                content_hash=chunk_info['content_hash'],
                dense_vector_path=dense_path,
                sparse_vector_path=sparse_path,
                metadata=vector.metadata
            )
            records.append(record)
        
        # 批量保存记录
        self.db.add_records(records)
    
    def encode_from_database(
        self,
        chunk_db: ChunkDatabase,
        use_cache: bool = True
    ) -> List[EncodedVector]:
        """
        从分块数据库编码所有分块
        
        Args:
            chunk_db: 分块数据库
            use_cache: 是否使用缓存
            
        Returns:
            编码向量列表
        """
        # 获取所有分块
        all_chunks = chunk_db.get_all_chunks()
        
        if not all_chunks:
            logger.warning("分块数据库为空")
            return []
        
        logger.info(f"从数据库加载了 {len(all_chunks)} 个分块")
        
        # 拟合稀疏编码器（如果需要）
        if hasattr(self.encoder, 'fit') and self.encoder_type in ['sparse', 'hybrid']:
            logger.info("拟合稀疏编码器...")
            texts = [chunk.content for chunk in all_chunks]
            self.encoder.fit(texts)
        
        # 编码所有分块
        return self.encode_chunks(all_chunks, use_cache=use_cache)
    
    def save_embeddings_to_npy(
        self,
        encoded_vectors: List[EncodedVector],
        output_path: Optional[Union[str, Path]] = None
    ) -> Path:
        """
        保存稠密向量到 numpy 文件
        
        Args:
            encoded_vectors: 编码向量列表
            output_path: 输出路径（可选）
            
        Returns:
            保存的文件路径
        """
        if output_path is None:
            output_path = self.output_manager.embeddings_dir / f"embeddings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.npy"
        else:
            output_path = Path(output_path)
        
        # 提取稠密向量
        dense_vectors = []
        for vec in encoded_vectors:
            if vec.has_dense:
                dense_vectors.append(vec.dense_vector)
        
        if not dense_vectors:
            logger.warning("没有稠密向量可保存")
            return output_path
        
        # 保存为 numpy 数组
        embeddings_array = np.array(dense_vectors)
        np.save(output_path, embeddings_array)
        
        # 保存元数据
        metadata_path = output_path.with_suffix('.meta.json')
        metadata = {
            'shape': embeddings_array.shape,
            'dtype': str(embeddings_array.dtype),
            'count': len(encoded_vectors),
            'encoder_type': self.encoder_type,
            'timestamp': datetime.now().isoformat(),
        }
        
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        logger.info(f"已保存 {len(dense_vectors)} 个向量到: {output_path}")
        return output_path
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'encoder_type': self.encoder_type,
            'cache_records': self.db.get_stats(),
            'cache_dir': str(self.cache_dir),
        }
