"""
去重器实现

提供多级去重功能：
1. 哈希去重（精确去重）
2. SimHash去重（近似去重）
3. Embedding去重（语义去重）
"""

import hashlib
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
from simhash import Simhash

from src.chunkers.base import TextChunk
from src.utils import OutputManager, get_logger
from src.utils.file_utils import FileUtils

from .base import BaseDeduper, DedupResult

logger = get_logger(__name__)


class Deduper(BaseDeduper):
    """多级去重器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化去重器
        
        Args:
            config: 配置字典，包含：
                - strategy: 去重策略 (test/production)
                - use_hash: 是否使用哈希去重
                - use_simhash: 是否使用SimHash去重
                - use_embedding: 是否使用Embedding去重
                - simhash_threshold: SimHash阈值
                - embedding_threshold: Embedding相似度阈值
        """
        super().__init__(config)
        
        # 读取 deduper 配置（适配 configs.yaml 结构）
        deduper_config = self.config.get('deduper', self.config)
        
        self.strategy = deduper_config.get('strategy', 'test')
        
        # 根据策略读取配置
        if self.strategy == 'test':
            test_config = deduper_config.get('test', {})
            self.use_hash = test_config.get('use_hash', True)
            self.use_simhash = test_config.get('use_simhash', True)
            self.use_embedding = False
            self.simhash_threshold = test_config.get('simhash_threshold', 3)
            self.embedding_threshold = 0.95
        else:  # production
            prod_config = deduper_config.get('production', {})
            self.use_hash = prod_config.get('use_hash', True)
            self.use_simhash = prod_config.get('use_simhash', True)
            self.use_embedding = prod_config.get('use_embedding', True)
            self.simhash_threshold = prod_config.get('simhash_threshold', 3)
            self.embedding_threshold = prod_config.get('embedding_threshold', 0.95)
        
        self.duplicate_strategy = deduper_config.get('duplicate_strategy', 'keep_first')
        
        # 输出管理器
        self.output_manager = OutputManager(config)
    
    def deduplicate(self, chunks: List[TextChunk], filename: Optional[str] = None) -> DedupResult:
        """
        去重
        
        Args:
            chunks: 文本块列表
            
        Returns:
            去重结果
        """
        if not chunks:
            return DedupResult([], [], [], self.calculate_stats(0, 0))
        
        original_count = len(chunks)
        
        # 步骤1: 哈希去重
        if self.use_hash:
            chunks, hash_removed = self._hash_deduplicate(chunks)
        
        # 步骤2: SimHash去重
        if self.use_simhash:
            chunks, simhash_removed = self._simhash_deduplicate(chunks)
        
        # 步骤3: Embedding去重
        if self.use_embedding:
            chunks, embedding_removed = self._embedding_deduplicate(chunks)
        
        # 收集所有被移除的块
        removed_chunks = []
        if self.use_hash:
            removed_chunks.extend(hash_removed)
        if self.use_simhash:
            removed_chunks.extend(simhash_removed)
        if self.use_embedding:
            removed_chunks.extend(embedding_removed)
        
        # 统计信息
        stats = self.calculate_stats(original_count, len(chunks))
        
        # 构建重复组信息
        duplicate_groups = self._build_duplicate_groups(original_count, chunks, removed_chunks)
        
        # 保存去重报告
        report = {
            'filename': filename,
            'strategy': self.strategy,
            'original_count': original_count,
            'unique_count': len(chunks),
            'removed_count': len(removed_chunks),
            'stats': stats,
            'duplicate_groups': duplicate_groups,
        }
        self.output_manager.save_dedup_report(report, filename)
        
        return DedupResult(
            chunks=chunks,
            removed_chunks=removed_chunks,
            duplicate_groups=duplicate_groups,
            stats=stats
        )
    
    def _hash_deduplicate(self, chunks: List[TextChunk]) -> Tuple[List[TextChunk], List[TextChunk]]:
        """哈希去重"""
        seen_hashes: Set[str] = set()
        kept = []
        removed = []
        
        for chunk in chunks:
            content_hash = FileUtils.calculate_content_hash(chunk.content, 'md5')
            
            if content_hash in seen_hashes:
                removed.append(chunk)
            else:
                seen_hashes.add(content_hash)
                kept.append(chunk)
        
        return kept, removed
    
    def _simhash_deduplicate(self, chunks: List[TextChunk]) -> Tuple[List[TextChunk], List[TextChunk]]:
        """SimHash去重"""
        if not chunks:
            return [], []
        
        # 计算所有块的SimHash
        simhashes = []
        for chunk in chunks:
            # 分词（简单按字符）
            features = [chunk.content[i:i+3] for i in range(len(chunk.content)-2)]
            simhash = Simhash(features)
            simhashes.append(simhash)
        
        kept = []
        removed = []
        removed_indices = set()
        
        for i, chunk in enumerate(chunks):
            if i in removed_indices:
                continue
            
            is_duplicate = False
            for j in range(i):
                if j in removed_indices:
                    continue
                
                distance = simhashes[i].distance(simhashes[j])
                if distance <= self.simhash_threshold:
                    is_duplicate = True
                    break
            
            if is_duplicate:
                removed.append(chunk)
                removed_indices.add(i)
            else:
                kept.append(chunk)
        
        return kept, removed
    
    def _embedding_deduplicate(self, chunks: List[TextChunk]) -> Tuple[List[TextChunk], List[TextChunk]]:
        """Embedding去重（需要外部提供embeddings）"""
        # TODO: 实现基于Embedding的去重
        # 这需要先计算所有块的embedding，然后计算相似度
        # 暂时返回原样
        return chunks, []
    
    def _build_duplicate_groups(
        self,
        original_count: int,
        kept_chunks: List[TextChunk],
        removed_chunks: List[TextChunk]
    ) -> List[List[int]]:
        """构建重复组信息"""
        # 简化实现：将被移除的块单独分组
        groups = []
        
        for removed in removed_chunks:
            # 找到相似的保留块
            for kept in kept_chunks:
                if self._is_similar(removed, kept):
                    groups.append([kept.index, removed.index])
                    break
            else:
                groups.append([removed.index])
        
        return groups
    
    def _is_similar(self, chunk1: TextChunk, chunk2: TextChunk) -> bool:
        """检查两个块是否相似"""
        # 简化实现：检查内容相似度
        # 实际实现应该使用更复杂的算法
        return chunk1.content[:100] == chunk2.content[:100]
