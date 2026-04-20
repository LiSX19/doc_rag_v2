"""
向量检索器实现
"""

from typing import Any, Dict, List, Optional

from src.embedders.base import BaseEmbedder
from src.utils import OutputManager, get_logger
from src.vector_stores.base import BaseVectorStore, SearchResult

from .base import BaseRetriever

logger = get_logger(__name__)


class VectorRetriever(BaseRetriever):
    """向量检索器"""
    
    def __init__(
        self,
        embedder: BaseEmbedder,
        vector_store: BaseVectorStore,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化向量检索器
        
        Args:
            embedder: Embedding模型
            vector_store: 向量数据库
            config: 配置字典，包含：
                - top_k: 默认返回结果数量
                - threshold: 相似度阈值
                - rerank.enabled: 是否启用重排序
                - rerank.model: 重排序模型
        """
        super().__init__(config)
        
        self.embedder = embedder
        self.vector_store = vector_store
        
        # 读取 retriever 配置（适配 configs.yaml 结构）
        retriever_config = self.config.get('retriever', self.config)
        
        self.top_k = retriever_config.get('top_k', 5)
        self.threshold = retriever_config.get('filter', {}).get('threshold', 0.5)
        self.use_rerank = retriever_config.get('rerank', {}).get('enabled', False)
        self.rerank_model = retriever_config.get('rerank', {}).get('model', 'BAAI/bge-reranker-base')
        
        # 输出管理器
        self.output_manager = OutputManager(config)
    
    def retrieve(self, query: str, top_k: Optional[int] = None) -> List[SearchResult]:
        """
        检索相关文档
        
        Args:
            query: 查询文本
            top_k: 返回结果数量（覆盖默认配置）
            
        Returns:
            搜索结果列表
        """
        if top_k is None:
            top_k = self.top_k
        
        # 生成查询向量
        query_embedding = self.embedder.embed(query)
        
        # 向量搜索
        results = self.vector_store.search(
            query_embedding=query_embedding,
            top_k=top_k * 2 if self.use_rerank else top_k  # 如果重排序，多取一些
        )
        
        # 过滤低分结果
        results = [r for r in results if r.score >= self.threshold]
        
        # 重排序
        if self.use_rerank and len(results) > 0:
            results = self._rerank(query, results)
        
        # 限制返回数量
        results = results[:top_k]
        
        return results
    
    def retrieve_and_save(
        self,
        query: str,
        filename: Optional[str] = None,
        top_k: Optional[int] = None
    ) -> List[SearchResult]:
        """
        检索并保存结果
        
        Args:
            query: 查询文本
            filename: 文件名（用于保存输出）
            top_k: 返回结果数量
            
        Returns:
            搜索结果列表
        """
        results = self.retrieve(query, top_k)
        
        # 保存检索结果
        if results:
            results_data = [
                {
                    'content': r.content,
                    'score': r.score,
                    'metadata': r.metadata,
                }
                for r in results
            ]
            self.output_manager.save_retrieval_results(
                query=query,
                results=results_data,
                filename=filename
            )
        
        return results
    
    def _rerank(self, query: str, results: List[SearchResult]) -> List[SearchResult]:
        """
        重排序
        
        Args:
            query: 查询文本
            results: 初步搜索结果
            
        Returns:
            重排序后的结果
        """
        # TODO: 实现重排序逻辑
        # 需要使用FlagEmbedding或CrossEncoder
        # 暂时按原分数排序
        return sorted(results, key=lambda x: x.score, reverse=True)
