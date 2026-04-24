"""
稀疏向量编码器

使用 BM25、TF-IDF 等传统方法生成稀疏向量表示
适用于关键词匹配和精确检索
"""

import math
import re
from collections import Counter
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from src.utils import get_logger

from .base import BaseEncoder, EncodedVector

logger = get_logger(__name__)


class BM25Encoder(BaseEncoder):
    """BM25 稀疏向量编码器
    
    基于 BM25 算法计算词项权重
    适合关键词匹配场景
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化 BM25 编码器
        
        Args:
            config: 配置字典，包含:
                - encoder.sparse.bm25.k1: BM25参数k1 (默认: 1.5)
                - encoder.sparse.bm25.b: BM25参数b (默认: 0.75)
                - encoder.sparse.bm25.max_features: 最大特征数 (默认: 50000)
                - encoder.sparse.bm25.min_df: 最小文档频率 (默认: 1)
                - encoder.sparse.bm25.max_df: 最大文档频率 (默认: 0.95)
        """
        super().__init__(config)
        
        # 读取配置
        encoder_config = self.config.get('encoder', {})
        sparse_config = encoder_config.get('sparse', {})
        bm25_config = sparse_config.get('bm25', {})
        
        # BM25 参数
        self.k1 = bm25_config.get('k1', 1.5)
        self.b = bm25_config.get('b', 0.75)
        self.max_features = bm25_config.get('max_features', 50000)
        self.min_df = bm25_config.get('min_df', 1)
        self.max_df = bm25_config.get('max_df', 0.95)
        
        # 词汇表和统计信息
        self.vocabulary: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}
        self.avg_doc_length: float = 0.0
        self.doc_count: int = 0
        self._dimension: int = 0
    
    def initialize(self):
        """初始化（BM25不需要预加载模型）"""
        self.is_initialized = True
    
    def _tokenize(self, text: str) -> List[str]:
        """分词"""
        # 简单的中文分词：按字符和英文单词分割
        # 实际项目中可以使用 jieba 等分词工具
        tokens = []
        
        # 提取英文单词
        english_words = re.findall(r'[a-zA-Z]+', text.lower())
        tokens.extend(english_words)
        
        # 提取中文字符（去除标点）
        chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)
        tokens.extend(chinese_chars)
        
        # 提取数字
        numbers = re.findall(r'\d+', text)
        tokens.extend(numbers)
        
        return tokens
    
    def fit(self, texts: List[str]):
        """
        拟合 BM25 参数
        
        Args:
            texts: 文档集合
        """
        logger.info(f"拟合 BM25 参数，文档数: {len(texts)}")
        
        # 分词
        tokenized_docs = [self._tokenize(text) for text in texts]
        
        # 构建词汇表
        term_doc_freq: Dict[str, int] = Counter()
        doc_lengths = []
        
        for tokens in tokenized_docs:
            doc_lengths.append(len(tokens))
            unique_terms = set(tokens)
            for term in unique_terms:
                term_doc_freq[term] += 1
        
        # 计算平均文档长度
        self.avg_doc_length = sum(doc_lengths) / len(doc_lengths) if doc_lengths else 0
        self.doc_count = len(texts)
        
        # 构建词汇表（限制特征数）
        sorted_terms = sorted(term_doc_freq.items(), key=lambda x: x[1], reverse=True)
        if self.max_features:
            sorted_terms = sorted_terms[:self.max_features]
        
        self.vocabulary = {term: idx for idx, (term, _) in enumerate(sorted_terms)}
        self._dimension = len(self.vocabulary)
        
        # 计算 IDF
        for term, idx in self.vocabulary.items():
            df = term_doc_freq[term]
            # BM25 IDF 公式
            idf = math.log((self.doc_count - df + 0.5) / (df + 0.5) + 1.0)
            self.idf[term] = idf
        
        logger.info(f"BM25 拟合完成，词汇表大小: {self._dimension}")
    
    def _compute_bm25_weights(
        self,
        tokens: List[str],
        doc_length: int
    ) -> Dict[int, float]:
        """
        计算 BM25 权重
        
        Args:
            tokens: 分词结果
            doc_length: 文档长度
            
        Returns:
            稀疏向量 {索引: 权重}
        """
        # 词频统计
        term_freq = Counter(tokens)
        
        # 计算 BM25 权重
        sparse_vector = {}
        
        for term, freq in term_freq.items():
            if term not in self.vocabulary:
                continue
            
            idx = self.vocabulary[term]
            idf = self.idf.get(term, 0)
            
            # BM25 公式
            numerator = freq * (self.k1 + 1)
            denominator = freq + self.k1 * (1 - self.b + self.b * doc_length / self.avg_doc_length)
            
            weight = idf * numerator / denominator if denominator > 0 else 0
            
            if weight > 0:
                sparse_vector[idx] = weight
        
        return sparse_vector
    
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
        
        # 分词
        tokens = self._tokenize(text)
        
        # 计算 BM25 权重
        sparse_vector = self._compute_bm25_weights(tokens, len(tokens))
        
        return EncodedVector(
            chunk_id=chunk_id or '',
            content=text,
            sparse_vector=sparse_vector,
            metadata={
                'algorithm': 'BM25',
                'vector_type': 'sparse',
                'k1': self.k1,
                'b': self.b,
                'doc_length': len(tokens),
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
        
        results = []
        for i, text in enumerate(texts):
            encoded = self.encode(text, chunk_ids[i])
            encoded.metadata['batch_index'] = i
            results.append(encoded)
        
        return results
    
    @property
    def dimension(self) -> int:
        """返回向量维度（词汇表大小）"""
        return self._dimension
    
    @property
    def vector_type(self) -> str:
        """返回向量类型"""
        return 'sparse'


class TFIDFEncoder(BaseEncoder):
    """TF-IDF 稀疏向量编码器
    
    基于 sklearn 的 TfidfVectorizer
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化 TF-IDF 编码器
        
        Args:
            config: 配置字典，包含:
                - encoder.sparse.tfidf.max_features: 最大特征数
                - encoder.sparse.tfidf.min_df: 最小文档频率
                - encoder.sparse.tfidf.max_df: 最大文档频率
                - encoder.sparse.tfidf.ngram_range: n-gram范围
        """
        super().__init__(config)
        
        # 读取配置
        encoder_config = self.config.get('encoder', {})
        sparse_config = encoder_config.get('sparse', {})
        tfidf_config = sparse_config.get('tfidf', {})
        
        self.max_features = tfidf_config.get('max_features', 50000)
        self.min_df = tfidf_config.get('min_df', 1)
        self.max_df = tfidf_config.get('max_df', 0.95)
        self.ngram_range = tuple(tfidf_config.get('ngram_range', [1, 2]))
        
        # 向量化器
        self.vectorizer: Optional[TfidfVectorizer] = None
    
    def initialize(self):
        """初始化"""
        self.is_initialized = True
    
    def fit(self, texts: List[str]):
        """
        拟合 TF-IDF 向量化器
        
        Args:
            texts: 文档集合
        """
        logger.info(f"拟合 TF-IDF 向量化器，文档数: {len(texts)}")
        
        self.vectorizer = TfidfVectorizer(
            max_features=self.max_features,
            min_df=self.min_df,
            max_df=self.max_df,
            ngram_range=self.ngram_range,
            token_pattern=r'(?u)\b\w+\b',
        )
        
        self.vectorizer.fit(texts)
        logger.info(f"TF-IDF 拟合完成，特征数: {len(self.vectorizer.vocabulary_)}")
    
    def encode(self, text: str, chunk_id: Optional[str] = None) -> EncodedVector:
        """编码单个文本"""
        if not self.is_initialized:
            self.initialize()
        
        if self.vectorizer is None:
            raise RuntimeError("TF-IDF 编码器需要先调用 fit() 方法")
        
        # 转换
        tfidf_matrix = self.vectorizer.transform([text])
        
        # 转换为稀疏向量格式
        sparse_vector = {}
        rows, cols = tfidf_matrix.nonzero()
        for row, col in zip(rows, cols):
            sparse_vector[int(col)] = float(tfidf_matrix[row, col])
        
        return EncodedVector(
            chunk_id=chunk_id or '',
            content=text,
            sparse_vector=sparse_vector,
            metadata={
                'algorithm': 'TF-IDF',
                'vector_type': 'sparse',
            }
        )
    
    def encode_batch(
        self,
        texts: List[str],
        chunk_ids: Optional[List[str]] = None
    ) -> List[EncodedVector]:
        """批量编码文本"""
        if not self.is_initialized:
            self.initialize()
        
        if not texts:
            return []
        
        if chunk_ids is None:
            chunk_ids = [None] * len(texts)
        
        if self.vectorizer is None:
            raise RuntimeError("TF-IDF 编码器需要先调用 fit() 方法")
        
        # 批量转换
        tfidf_matrix = self.vectorizer.transform(texts)
        
        results = []
        for i, text in enumerate(texts):
            sparse_vector = {}
            row = tfidf_matrix[i]
            cols = row.nonzero()[1]
            for col in cols:
                sparse_vector[int(col)] = float(row[0, col])
            
            results.append(EncodedVector(
                chunk_id=chunk_ids[i] or '',
                content=text,
                sparse_vector=sparse_vector,
                metadata={
                    'algorithm': 'TF-IDF',
                    'vector_type': 'sparse',
                    'batch_index': i,
                }
            ))
        
        return results
    
    @property
    def dimension(self) -> int:
        """返回向量维度"""
        if self.vectorizer is None:
            return 0
        return len(self.vectorizer.vocabulary_)
    
    @property
    def vector_type(self) -> str:
        """返回向量类型"""
        return 'sparse'


# 默认使用 BM25
SparseEncoder = BM25Encoder
