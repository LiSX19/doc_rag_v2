"""
Chroma向量数据库实现
"""

from typing import Any, Dict, List, Optional

import chromadb
import numpy as np
from chromadb.config import Settings

from .base import BaseVectorStore, SearchResult


class ChromaStore(BaseVectorStore):
    """Chroma向量数据库"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化Chroma存储
        
        Args:
            config: 配置字典，包含：
                - persist_directory: 持久化目录
                - collection_name: 集合名称
                - hnsw_space: 距离度量 (cosine/l2/ip)
                - hnsw_construction_ef: HNSW构建参数
                - hnsw_search_ef: HNSW搜索参数
                - hnsw_M: HNSW参数M
        """
        super().__init__(config)
        
        # 读取 vector_store 配置（适配 configs.yaml 结构）
        vs_config = self.config.get('vector_store', self.config)
        chroma_config = vs_config.get('chroma', {})
        self.persist_directory = chroma_config.get('persist_directory', './chroma_db')
        self.collection_name = chroma_config.get('collection_name', 'doc_rag_collection')
        
        # HNSW参数
        self.hnsw_space = chroma_config.get('hnsw_space', 'cosine')
        self.hnsw_construction_ef = chroma_config.get('hnsw_construction_ef', 128)
        self.hnsw_search_ef = chroma_config.get('hnsw_search_ef', 64)
        self.hnsw_M = chroma_config.get('hnsw_M', 16)
        
        self.client = None
        self.collection = None
    
    def initialize(self):
        """初始化数据库连接"""
        if self.is_initialized:
            return
        
        # 创建客户端
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(
                anonymized_telemetry=False
            )
        )
        
        # 获取或创建集合
        metadata = {
            "hnsw:space": self.hnsw_space,
            "hnsw:construction_ef": self.hnsw_construction_ef,
            "hnsw:search_ef": self.hnsw_search_ef,
            "hnsw:M": self.hnsw_M,
        }
        
        try:
            self.collection = self.client.get_collection(
                name=self.collection_name
            )
        except Exception:
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata=metadata
            )
        
        self.is_initialized = True
    
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
            embeddings: Embedding向量
            contents: 文档内容列表
            metadatas: 元数据列表
        """
        if not self.is_initialized:
            self.initialize()
        
        # 确保embeddings是列表格式
        if isinstance(embeddings, np.ndarray):
            embeddings = embeddings.tolist()
        
        # 添加文档
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=contents,
            metadatas=metadatas
        )
    
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
        if not self.is_initialized:
            self.initialize()
        
        # 确保是列表格式
        if isinstance(query_embedding, np.ndarray):
            query_embedding = query_embedding.tolist()
        
        # 如果是二维数组，取第一个
        if isinstance(query_embedding[0], list):
            query_embedding = query_embedding[0]
        
        # 执行搜索
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=filter_dict
        )
        
        # 解析结果
        search_results = []
        for i in range(len(results['ids'][0])):
            result = SearchResult(
                id=results['ids'][0][i],
                content=results['documents'][0][i],
                score=results['distances'][0][i] if 'distances' in results else 0.0,
                metadata=results['metadatas'][0][i] if 'metadatas' in results else {}
            )
            search_results.append(result)
        
        return search_results
    
    def delete(self, ids: List[str]):
        """
        删除文档
        
        Args:
            ids: 文档ID列表
        """
        if not self.is_initialized:
            self.initialize()
        
        self.collection.delete(ids=ids)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取数据库统计信息
        
        Returns:
            统计信息字典
        """
        if not self.is_initialized:
            self.initialize()
        
        count = self.collection.count()
        
        return {
            'collection_name': self.collection_name,
            'document_count': count,
            'persist_directory': self.persist_directory,
        }
