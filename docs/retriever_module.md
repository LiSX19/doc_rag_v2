# Retriever 模块详细说明文档

## 目录
1. [模块概述](#模块概述)
2. [文件结构](#文件结构)
3. [核心类与接口](#核心类与接口)
4. [向量检索器](#向量检索器)
5. [检索流程](#检索流程)
6. [重排序机制](#重排序机制)
7. [配置参数](#配置参数)
8. [使用示例](#使用示例)
9. [扩展开发](#扩展开发)

---

## 模块概述

Retriever 模块是文档 RAG 系统的检索组件，负责从向量数据库中检索与用户查询相关的文档片段。该模块支持多种检索策略，包括向量相似度检索、关键词检索和混合检索，并提供重排序功能以提高检索结果的相关性。

### 主要功能

1. **多策略检索**: 支持向量检索、关键词检索和混合检索
2. **智能重排序**: 使用交叉编码器对初步检索结果进行重排序
3. **批处理支持**: 支持批量查询的并行处理
4. **可配置过滤**: 基于相似度阈值和其他条件过滤结果
5. **结果缓存**: 缓存频繁查询的结果以提高性能

### 检索流程

```
用户查询
    │
    ├─> 1. 查询编码
    │      ├─ 使用编码器将查询文本转换为向量
    │      ├─ 支持稠密向量、稀疏向量和混合向量
    │      └─ 缓存编码结果以提高性能
    │
    ├─> 2. 向量检索
    │      ├─ 在向量数据库中搜索相似向量
    │      ├─ 计算余弦相似度
    │      ├─ 返回 top-k 相似结果
    │      └─ 应用相似度阈值过滤
    │
    ├─> 3. 重排序 (可选)
    │      ├─ 使用交叉编码器重新评分
    │      ├─ 考虑查询和文档的交互关系
    │      ├─ 重新排列结果顺序
    │      └─ 提高结果相关性
    │
    ├─> 4. 结果处理
    │      ├─ 格式化检索结果
    │      ├─ 添加元数据
    │      ├─ 生成可读的输出
    │      └─ 缓存结果以供后续使用
    │
    └─> 5. 返回结果
           ├─ 检索到的文档片段
           ├─ 相似度分数
           ├─ 元数据信息
           └─ 检索统计信息
```

---

## 文件结构

```
src/retrievers/
├── __init__.py              # 模块导出
├── base.py                  # 基类和接口定义
└── vector_retriever.py      # 向量检索器实现
```

---

## 核心类与接口

### 1. BaseRetriever (抽象基类)

所有检索器的基类，定义统一的检索接口：

```python
class BaseRetriever(ABC):
    """检索器基类"""
    
    @abstractmethod
    def retrieve(self, query: str, top_k: int = 5) -> List[SearchResult]:
        """
        检索相关文档
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            
        Returns:
            搜索结果列表
        """
        pass
    
    def retrieve_batch(
        self,
        queries: List[str],
        top_k: int = 5
    ) -> List[List[SearchResult]]:
        """
        批量检索
        
        Args:
            queries: 查询文本列表
            top_k: 每个查询返回结果数量
            
        Returns:
            搜索结果列表的列表
        """
    
    def _validate_query(self, query: str) -> bool:
        """验证查询是否有效"""
    
    def _preprocess_query(self, query: str) -> str:
        """预处理查询文本"""
```

### 2. SearchResult (搜索结果类)

定义搜索结果的数据结构：

```python
class SearchResult:
    """搜索结果类"""
    
    def __init__(
        self,
        id: str,                      # 文档唯一标识
        content: str,                 # 文档内容
        score: float,                 # 相似度分数 (0.0-1.0)
        metadata: Optional[Dict[str, Any]] = None  # 元数据
    ):
        # 初始化逻辑
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（支持JSON序列化）"""
    
    def __repr__(self) -> str:
        """字符串表示"""
        return f"SearchResult(id={self.id}, score={self.score:.3f})"
    
    def __lt__(self, other: 'SearchResult') -> bool:
        """比较运算符（用于排序）"""
        return self.score < other.score
    
    def get_formatted_content(self, max_length: int = 200) -> str:
        """获取格式化的内容（限制长度）"""
        if len(self.content) <= max_length:
            return self.content
        return self.content[:max_length] + "..."
```

### 3. VectorRetriever (向量检索器)

基于向量相似度的检索器实现：

```python
class VectorRetriever(BaseRetriever):
    """向量检索器"""
    
    def __init__(
        self,
        encoder: BaseEncoder,
        vector_store: BaseVectorStore,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化向量检索器
        
        Args:
            encoder: 编码器，用于将查询转换为向量
            vector_store: 向量数据库，存储和检索向量
            config: 配置字典，包含：
                - retriever.top_k: 默认返回结果数量
                - retriever.filter.threshold: 相似度阈值
                - retriever.rerank.enabled: 是否启用重排序
                - retriever.rerank.model: 重排序模型
        """
    
    def retrieve(self, query: str, top_k: int = 5) -> List[SearchResult]:
        """执行向量检索"""
    
    def retrieve_batch(
        self,
        queries: List[str],
        top_k: int = 5
    ) -> List[List[SearchResult]]:
        """批量检索（优化版本）"""
    
    def _encode_query(self, query: str) -> np.ndarray:
        """编码查询文本为向量"""
    
    def _search_vector_store(
        self,
        query_vector: np.ndarray,
        top_k: int = 5
    ) -> List[SearchResult]:
        """在向量数据库中搜索"""
    
    def _rerank_results(
        self,
        query: str,
        results: List[SearchResult]
    ) -> List[SearchResult]:
        """重排序检索结果（如果启用）"""
```

---

## 向量检索器

### 1. 向量检索原理

向量检索基于向量空间模型，将文本转换为高维向量，通过计算向量之间的相似度来度量文本之间的相关性。

**核心概念**:
- **查询编码**: 将用户查询转换为向量表示
- **向量相似度**: 计算查询向量与文档向量的余弦相似度
- **相似度阈值**: 过滤低相似度的结果
- **Top-K 检索**: 返回相似度最高的 K 个结果

**相似度计算公式**:
```
cosine_similarity(A, B) = (A · B) / (||A|| × ||B||)
```

其中:
- A · B 是向量 A 和 B 的点积
- ||A|| 是向量 A 的欧几里得范数
- 结果范围: [-1, 1]，通常归一化到 [0, 1]

### 2. 检索流程详解

#### 步骤 1: 查询预处理
```python
def _preprocess_query(self, query: str) -> str:
    """预处理查询文本"""
    # 1. 去除多余空白
    query = ' '.join(query.split())
    
    # 2. 转换为小写（对于英文）
    if self.config.get('lowercase', True):
        query = query.lower()
    
    # 3. 移除特殊字符（可选）
    if self.config.get('remove_special_chars', False):
        import re
        query = re.sub(r'[^\w\s]', '', query)
    
    return query
```

#### 步骤 2: 查询编码
```python
def _encode_query(self, query: str) -> np.ndarray:
    """编码查询文本为向量"""
    # 使用编码器将查询转换为向量
    encoded_vector = self.encoder.encode(query, chunk_id=f"query_{hash(query)}")
    
    # 根据编码器类型获取向量
    if encoded_vector.dense_vector is not None:
        vector = encoded_vector.dense_vector
    elif encoded_vector.sparse_vector is not None:
        # 稀疏向量需要特殊处理
        vector = self._sparse_to_dense(encoded_vector.sparse_vector)
    else:
        raise ValueError("编码器未返回有效向量")
    
    # 向量归一化（确保单位长度）
    if self.config.get('normalize_vectors', True):
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
    
    return vector
```

#### 步骤 3: 向量搜索
```python
def _search_vector_store(
    self,
    query_vector: np.ndarray,
    top_k: int = 5
) -> List[SearchResult]:
    """在向量数据库中搜索"""
    # 调用向量数据库的搜索接口
    raw_results = self.vector_store.search(
        query_vector=query_vector,
        top_k=top_k * 2,  # 获取更多结果以供过滤和重排序
        threshold=self.threshold
    )
    
    # 应用相似度阈值过滤
    filtered_results = [
        result for result in raw_results 
        if result.score >= self.threshold
    ]
    
    # 按分数降序排序
    filtered_results.sort(key=lambda x: x.score, reverse=True)
    
    # 返回 top-k 结果
    return filtered_results[:top_k]
```

#### 步骤 4: 结果后处理
```python
def _postprocess_results(
    self,
    query: str,
    results: List[SearchResult]
) -> List[SearchResult]:
    """后处理检索结果"""
    if not results:
        return []
    
    # 1. 添加查询上下文到元数据
    for result in results:
        result.metadata['query'] = query
        result.metadata['retrieved_at'] = datetime.now().isoformat()
    
    # 2. 去重（基于内容相似度）
    if self.config.get('deduplicate', True):
        results = self._deduplicate_results(results)
    
    # 3. 格式化内容
    for result in results:
        # 确保内容长度合理
        if len(result.content) > 1000:
            result.content = result.content[:1000] + "..."
    
    return results
```

### 3. 批量检索优化

向量检索器实现了优化的批量检索功能：

```python
def retrieve_batch(
    self,
    queries: List[str],
    top_k: int = 5
) -> List[List[SearchResult]]:
    """批量检索（优化版本）"""
    if not queries:
        return []
    
    # 批量编码查询
    query_vectors = []
    for query in queries:
        vector = self._encode_query(query)
        query_vectors.append(vector)
    
    # 批量搜索（如果向量数据库支持）
    if hasattr(self.vector_store, 'search_batch'):
        all_results = self.vector_store.search_batch(
            query_vectors=query_vectors,
            top_k=top_k,
            threshold=self.threshold
        )
    else:
        # 串行搜索
        all_results = []
        for vector in query_vectors:
            results = self._search_vector_store(vector, top_k)
            all_results.append(results)
    
    # 批量重排序（如果启用）
    if self.use_rerank:
        for i, (query, results) in enumerate(zip(queries, all_results)):
            if results:
                all_results[i] = self._rerank_results(query, results)
    
    return all_results
```

---

## 重排序机制

### 1. 重排序原理

重排序 (Reranking) 是在初步检索后，使用更精确但计算成本更高的模型对结果进行重新评分和排序的过程。

**为什么需要重排序**:
1. **向量检索的局限性**: 向量相似度主要基于语义相似度，可能忽略查询和文档之间的交互关系
2. **精确度提升**: 重排序模型（如交叉编码器）可以更准确地判断相关性
3. **结果优化**: 改善 top-k 结果的顺序，将最相关的结果放在前面

**重排序流程**:
```
初步检索结果 (top-k × 2)
    │
    ├─> 1. 准备重排序数据
    │      ├─ 构建 (query, document) 对
    │      ├─ 批次处理（减少计算成本）
    │      └─ 缓存中间结果
    │
    ├─> 2. 交叉编码器评分
    │      ├─ 使用预训练模型计算相关性分数
    │      ├─ 考虑查询和文档的交互
    │      └─ 生成新的分数
    │
    ├─> 3. 重新排序
    │      ├─ 按新分数降序排序
    │      ├─ 过滤低分结果
    │      └─ 返回重新排序的结果
    │
    └─> 4. 结果融合 (可选)
           ├─ 结合向量分数和重排序分数
           ├─ 加权平均或最大值选择
           └─ 生成最终排序
```

### 2. 重排序实现

```python
def _rerank_results(
    self,
    query: str,
    results: List[SearchResult]
) -> List[SearchResult]:
    """重排序检索结果"""
    if not results or len(results) <= 1:
        return results
    
    # 如果未初始化重排序器，则懒加载
    if not hasattr(self, '_reranker'):
        self._reranker = self._load_reranker()
    
    # 准备重排序数据
    documents = [result.content for result in results]
    
    try:
        # 计算重排序分数
        rerank_scores = self._reranker.predict(
            [(query, doc) for doc in documents]
        )
        
        # 更新结果分数
        for i, (result, new_score) in enumerate(zip(results, rerank_scores)):
            # 融合原始分数和重排序分数
            if self.config.get('rerank', {}).get('fusion', 'replace') == 'weighted':
                # 加权融合
                alpha = self.config.get('rerank', {}).get('alpha', 0.7)
                final_score = alpha * new_score + (1 - alpha) * result.score
            else:
                # 直接替换
                final_score = new_score
            
            result.score = final_score
            result.metadata['rerank_score'] = new_score
            result.metadata['original_score'] = result.score
        
        # 重新排序
        results.sort(key=lambda x: x.score, reverse=True)
        
    except Exception as e:
        logger.warning(f"重排序失败: {e}, 返回原始结果")
        # 失败时返回原始结果
    
    return results

def _load_reranker(self):
    """加载重排序模型"""
    from sentence_transformers import CrossEncoder
    
    rerank_config = self.config.get('retriever', {}).get('rerank', {})
    model_name = rerank_config.get('model', 'BAAI/bge-reranker-base')
    
    reranker = CrossEncoder(
        model_name,
        max_length=512,
        device='cuda' if torch.cuda.is_available() else 'cpu'
    )
    
    return reranker
```

### 3. 重排序配置

```yaml
retriever:
  # 基础检索配置
  top_k: 5
  filter:
    threshold: 0.5
  
  # 重排序配置
  rerank:
    enabled: true                    # 是否启用重排序
    model: "BAAI/bge-reranker-base" # 重排序模型
    fusion: "weighted"              # 分数融合策略: weighted/replace
    alpha: 0.7                      # 加权融合权重（仅当fusion=weighted时有效）
    
    # 性能配置
    batch_size: 16                  # 重排序批处理大小
    max_length: 512                 # 最大序列长度
    
    # 缓存配置
    cache_enabled: true             # 是否缓存重排序结果
    cache_size: 1000                # 缓存大小
    cache_ttl: 3600                 # 缓存生存时间（秒）
```

---

## 配置参数

### 1. 基础配置
```yaml
retriever:
  # 检索类型: vector（向量检索）/ keyword（关键词检索）/ hybrid（混合检索）
  type: "vector"
  
  # 通用配置
  top_k: 5                          # 返回结果数量
  deduplicate: true                 # 是否去重
  
  # 查询预处理配置
  preprocess:
    lowercase: true                 # 是否转换为小写
    remove_special_chars: false     # 是否移除特殊字符
    trim_whitespace: true           # 是否修剪空白
```

### 2. 向量检索配置
```yaml
retriever:
  type: "vector"
  
  vector:
    # 编码器配置（继承encoder模块配置）
    encoder:
      type: "dense"                 # 编码器类型: dense/sparse/hybrid
      normalize_vectors: true       # 是否归一化向量
    
    # 过滤配置
    filter:
      threshold: 0.5                # 相似度阈值
      min_score: 0.0                # 最低分数
      max_score: 1.0                # 最高分数
    
    # 重排序配置
    rerank:
      enabled: true                 # 是否启用重排序
      model: "BAAI/bge-reranker-base"
      fusion: "weighted"            # 分数融合策略
      alpha: 0.7                    # 融合权重
```

### 3. 关键词检索配置
```yaml
retriever:
  type: "keyword"
  
  keyword:
    # 算法配置
    algorithm: "bm25"               # 算法: bm25/tfidf
    k1: 1.5                         # BM25参数k1
    b: 0.75                         # BM25参数b
    
    # 分词配置
    tokenizer:
      type: "jieba"                 # 分词器: jieba/thulac
      user_dict: "./data/user_dict.txt"  # 用户词典
    
    # 索引配置
    index:
      path: "./cache/keyword_index"  # 索引路径
      rebuild: false                # 是否重建索引
```

### 4. 混合检索配置
```yaml
retriever:
  type: "hybrid"
  
  hybrid:
    # 策略配置
    strategy: "reciprocal_rank_fusion"  # 融合策略: rrf/weighted/concat
    vector_weight: 0.7               # 向量检索权重
    keyword_weight: 0.3              # 关键词检索权重
    
    # 组件配置
    vector_config: {}                # 向量检索配置（继承vector配置）
    keyword_config: {}               # 关键词检索配置（继承keyword配置）
```

### 5. 性能优化配置
```yaml
retriever:
  # 批处理配置
  batch:
    enabled: true                   # 是否启用批处理
    size: 32                        # 批处理大小
    parallel: true                  # 是否并行处理
    max_workers: 4                  # 最大工作线程数
  
  # 缓存配置
  cache:
    enabled: true                   # 是否启用缓存
    type: "lru"                     # 缓存类型: lru/fifo
    size: 1000                      # 缓存大小
    ttl: 3600                       # 缓存生存时间（秒）
  
  # 超时配置
  timeout:
    encode: 10.0                    # 编码超时（秒）
    search: 5.0                     # 搜索超时（秒）
    rerank: 15.0                    # 重排序超时（秒）
    total: 30.0                     # 总超时（秒）
```

---

## 使用示例

### 1. 基本使用
```python
from src.retrievers import VectorRetriever
from src.encoders import EncoderManager
from src.vector_stores import ChromaStore

# 初始化编码器
encoder_manager = EncoderManager(config)
encoder = encoder_manager.encoder

# 初始化向量数据库
vector_store = ChromaStore(config)

# 初始化检索器
retriever = VectorRetriever(
    encoder=encoder,
    vector_store=vector_store,
    config=config
)

# 执行检索
query = "什么是机器学习？"
results = retriever.retrieve(query, top_k=5)

# 处理结果
print(f"查询: {query}")
print(f"找到 {len(results)} 个相关文档:")
for i, result in enumerate(results):
    print(f"{i+1}. [分数: {result.score:.3f}] {result.content[:100]}...")
    print(f"   元数据: {result.metadata}")
```

### 2. 批量检索
```python
from src.retrievers import VectorRetriever

# 初始化检索器
retriever = VectorRetriever(encoder, vector_store, config)

# 批量查询
queries = [
    "什么是机器学习？",
    "深度学习与机器学习的区别",
    "监督学习有哪些方法"
]

# 批量检索
all_results = retriever.retrieve_batch(queries, top_k=3)

# 处理批量结果
for i, (query, results) in enumerate(zip(queries, all_results)):
    print(f"\n查询 {i+1}: {query}")
    print(f"检索到 {len(results)} 个结果:")
    
    for j, result in enumerate(results):
        print(f"  {j+1}. {result.content[:80]}... (分数: {result.score:.3f})")
```

### 3. 启用重排序
```python
from src.retrievers import VectorRetriever

# 配置启用重排序
config = {
    "retriever": {
        "top_k": 10,
        "filter": {"threshold": 0.3},
        "rerank": {
            "enabled": True,
            "model": "BAAI/bge-reranker-base",
            "fusion": "weighted",
            "alpha": 0.7
        }
    }
}

# 初始化检索器
retriever = VectorRetriever(encoder, vector_store, config)

# 执行检索（自动启用重排序）
query = "神经网络的基本原理"
results = retriever.retrieve(query, top_k=5)

# 查看重排序效果
print("重排序后的结果:")
for i, result in enumerate(results):
    original_score = result.metadata.get('original_score', result.score)
    rerank_score = result.metadata.get('rerank_score', None)
    
    if rerank_score is not None:
        print(f"{i+1}. 最终分数: {result.score:.3f} "
              f"(向量: {original_score:.3f}, 重排序: {rerank_score:.3f})")
    else:
        print(f"{i+1}. 分数: {result.score:.3f}")
    
    print(f"   内容: {result.content[:80]}...")
```

### 4. 自定义检索器
```python
from src.retrievers.base import BaseRetriever, SearchResult
from typing import List, Dict, Any, Optional

class CustomRetriever(BaseRetriever):
    """自定义检索器示例"""
    
    def __init__(self, config=None):
        super().__init__(config)
        self.config = config or {}
        
        # 自定义配置
        self.custom_param = self.config.get('custom_param', 'default')
        
        # 初始化自定义组件
        self._init_custom_components()
    
    def _init_custom_components(self):
        """初始化自定义组件"""
        # 例如：加载自定义索引、初始化算法等
        self.custom_index = {}
        logger.info(f"自定义检索器初始化完成，参数: {self.custom_param}")
    
    def retrieve(self, query: str, top_k: int = 5) -> List[SearchResult]:
        """自定义检索逻辑"""
        
        # 验证查询
        if not self._validate_query(query):
            return []
        
        # 预处理查询
        processed_query = self._preprocess_query(query)
        
        # 执行自定义检索算法
        raw_results = self._custom_search(processed_query, top_k * 2)
        
        # 过滤和排序
        filtered_results = [
            result for result in raw_results
            if result.score >= self.config.get('threshold', 0.0)
        ]
        filtered_results.sort(key=lambda x: x.score, reverse=True)
        
        # 返回 top-k 结果
        results = filtered_results[:top_k]
        
        # 后处理
        results = self._postprocess_results(query, results)
        
        return results
    
    def _custom_search(self, query: str, limit: int) -> List[SearchResult]:
        """自定义搜索算法"""
        results = []
        
        # 实现自定义搜索逻辑
        # 例如：基于规则的匹配、外部API调用等
        
        # 示例：简单的关键词匹配
        query_words = set(query.lower().split())
        
        for doc_id, doc_content in self.custom_index.items():
            # 计算匹配度
            doc_words = set(doc_content.lower().split())
            common_words = query_words & doc_words
            
            if common_words:
                # 计算分数
                score = len(common_words) / len(query_words) if query_words else 0
                
                # 创建搜索结果
                result = SearchResult(
                    id=doc_id,
                    content=doc_content,
                    score=score,
                    metadata={
                        'matched_words': list(common_words),
                        'algorithm': 'custom_keyword_match'
                    }
                )
                results.append(result)
        
        return results
    
    def retrieve_batch(
        self,
        queries: List[str],
        top_k: int = 5
    ) -> List[List[SearchResult]]:
        """批量检索（自定义实现）"""
        all_results = []
        
        for query in queries:
            results = self.retrieve(query, top_k)
            all_results.append(results)
        
        return all_results
```

### 5. 检索结果分析
```python
from src.retrievers import VectorRetriever
import matplotlib.pyplot as plt

# 初始化检索器
retriever = VectorRetriever(encoder, vector_store, config)

# 执行检索
query = "人工智能的发展历史"
results = retriever.retrieve(query, top_k=10)

# 分析结果
if results:
    # 提取分数用于分析
    scores = [result.score for result in results]
    
    print(f"查询: {query}")
    print(f"检索到 {len(results)} 个结果")
    print(f"最高分: {max(scores):.3f}")
    print(f"最低分: {min(scores):.3f}")
    print(f"平均分: {sum(scores)/len(scores):.3f}")
    print(f"中位数: {sorted(scores)[len(scores)//2]:.3f}")
    
    # 分数分布
    score_ranges = [(0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.0)]
    distribution = {f"{low:.1f}-{high:.1f}": 0 for low, high in score_ranges}
    
    for score in scores:
        for low, high in score_ranges:
            if low <= score < high:
                distribution[f"{low:.1f}-{high:.1f}"] += 1
                break
    
    print("\n分数分布:")
    for range_str, count in distribution.items():
        print(f"  {range_str}: {count} 个 ({count/len(results)*100:.1f}%)")
    
    # 可视化（可选）
    if len(results) > 1:
        plt.figure(figsize=(10, 6))
        plt.bar(range(len(results)), scores)
        plt.xlabel('结果排名')
        plt.ylabel('相似度分数')
        plt.title(f'检索结果分数分布 - "{query}"')
        plt.ylim(0, 1.0)
        plt.grid(True, alpha=0.3)
        plt.show()
```

---

## 扩展开发

### 1. 添加新的检索算法

**步骤 1**: 创建新的检索器类
```python
from src.retrievers.base import BaseRetriever, SearchResult

class BM25Retriever(BaseRetriever):
    """BM25检索器"""
    
    def __init__(self, config=None):
        super().__init__(config)
        self.config = config or {}
        
        # 读取BM25配置
        retriever_config = self.config.get('retriever', self.config)
        bm25_config = retriever_config.get('bm25', {})
        
        self.k1 = bm25_config.get('k1', 1.5)
        self.b = bm25_config.get('b', 0.75)
        
        # 初始化BM25索引
        self.index = self._build_index()
        self.avgdl = self._calculate_avgdl()
    
    def _build_index(self):
        """构建BM25索引"""
        # 从向量数据库或其他来源加载文档
        # 构建词频统计等
        return {}  # 返回索引数据结构
    
    def retrieve(self, query: str, top_k: int = 5) -> List[SearchResult]:
        """BM25检索"""
        # 分词
        query_terms = self._tokenize(query)
        
        results = []
        for doc_id, doc_info in self.index.items():
            # 计算BM25分数
            score = self._bm25_score(query_terms, doc_id, doc_info)
            
            if score > 0:
                result = SearchResult(
                    id=doc_id,
                    content=doc_info['content'],
                    score=score,
                    metadata={
                        'algorithm': 'bm25',
                        'k1': self.k1,
                        'b': self.b
                    }
                )
                results.append(result)
        
        # 排序并返回top-k
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]
    
    def _bm25_score(self, query_terms, doc_id, doc_info):
        """计算BM25分数"""
        score = 0.0
        for term in query_terms:
            if term in doc_info['term_freq']:
                tf = doc_info['term_freq'][term]
                idf = self._idf(term)
                
                # BM25公式
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * doc_info['length'] / self.avgdl)
                
                score += idf * (numerator / denominator)
        
        return score
    
    def _idf(self, term):
        """计算逆文档频率"""
        # IDF计算公式
        N = len(self.index)
        df = self._document_frequency(term)
        
        if df == 0:
            return 0
        
        return np.log((N - df + 0.5) / (df + 0.5) + 1)
```

**步骤 2**: 更新配置支持
```yaml
retriever:
  type: "bm25"  # 新的检索器类型
  
  bm25:
    k1: 1.5
    b: 0.75
    index_path: "./cache/bm25_index"
    rebuild: false
```

### 2. 实现混合检索

```python
from src.retrievers.base import BaseRetriever, SearchResult

class HybridRetriever(BaseRetriever):
    """混合检索器（结合向量检索和关键词检索）"""
    
    def __init__(self, config=None):
        super().__init__(config)
        self.config = config or {}
        
        # 读取混合配置
        retriever_config = self.config.get('retriever', self.config)
        hybrid_config = retriever_config.get('hybrid', {})
        
        self.strategy = hybrid_config.get('strategy', 'reciprocal_rank_fusion')
        self.vector_weight = hybrid_config.get('vector_weight', 0.7)
        self.keyword_weight = hybrid_config.get('keyword_weight', 0.3)
        
        # 初始化子检索器
        self.vector_retriever = self._init_vector_retriever()
        self.keyword_retriever = self._init_keyword_retriever()
    
    def retrieve(self, query: str, top_k: int = 5) -> List[SearchResult]:
        """混合检索"""
        # 并行执行两种检索
        vector_results = self.vector_retriever.retrieve(query, top_k * 2)
        keyword_results = self.keyword_retriever.retrieve(query, top_k * 2)
        
        # 融合结果
        if self.strategy == 'reciprocal_rank_fusion':
            fused_results = self._reciprocal_rank_fusion(
                vector_results, keyword_results, top_k
            )
        elif self.strategy == 'weighted':
            fused_results = self._weighted_fusion(
                vector_results, keyword_results, top_k
            )
        elif self.strategy == 'concat':
            fused_results = self._concat_fusion(
                vector_results, keyword_results, top_k
            )
        else:
            raise ValueError(f"未知的融合策略: {self.strategy}")
        
        return fused_results
    
    def _reciprocal_rank_fusion(self, results1, results2, top_k):
        """倒数排名融合 (Reciprocal Rank Fusion)"""
        # 创建文档ID到排名的映射
        rank_map = {}
        
        # 处理第一个结果列表
        for rank, result in enumerate(results1):
            doc_id = result.id
            if doc_id not in rank_map:
                rank_map[doc_id] = {'scores': [], 'content': result.content}
            rank_map[doc_id]['scores'].append(1.0 / (60 + rank + 1))
        
        # 处理第二个结果列表
        for rank, result in enumerate(results2):
            doc_id = result.id
            if doc_id not in rank_map:
                rank_map[doc_id] = {'scores': [], 'content': result.content}
            rank_map[doc_id]['scores'].append(1.0 / (60 + rank + 1))
        
        # 计算融合分数
        fused_results = []
        for doc_id, info in rank_map.items():
            fused_score = sum(info['scores'])
            result = SearchResult(
                id=doc_id,
                content=info['content'],
                score=fused_score,
                metadata={'fusion_strategy': 'rrf', 'component_scores': info['scores']}
            )
            fused_results.append(result)
        
        # 排序并返回top-k
        fused_results.sort(key=lambda x: x.score, reverse=True)
        return fused_results[:top_k]
    
    def _weighted_fusion(self, results1, results2, top_k):
        """加权融合"""
        # 创建文档ID到分数的映射
        score_map = {}
        
        # 归一化分数
        max_score1 = max([r.score for r in results1]) if results1 else 1.0
        max_score2 = max([r.score for r in results2]) if results2 else 1.0
        
        # 处理第一个结果列表
        for result in results1:
            doc_id = result.id
            normalized_score = result.score / max_score1
            score_map[doc_id] = {
                'vector_score': normalized_score,
                'keyword_score': 0,
                'content': result.content
            }
        
        # 处理第二个结果列表
        for result in results2:
            doc_id = result.id
            normalized_score = result.score / max_score2
            
            if doc_id in score_map:
                score_map[doc_id]['keyword_score'] = normalized_score
            else:
                score_map[doc_id] = {
                    'vector_score': 0,
                    'keyword_score': normalized_score,
                    'content': result.content
                }
        
        # 计算加权分数
        fused_results = []
        for doc_id, scores in score_map.items():
            fused_score = (
                self.vector_weight * scores['vector_score'] +
                self.keyword_weight * scores['keyword_score']
            )
            
            result = SearchResult(
                id=doc_id,
                content=scores['content'],
                score=fused_score,
                metadata={
                    'fusion_strategy': 'weighted',
                    'vector_score': scores['vector_score'],
                    'keyword_score': scores['keyword_score'],
                    'weights': {'vector': self.vector_weight, 'keyword': self.keyword_weight}
                }
            )
            fused_results.append(result)
        
        # 排序并返回top-k
        fused_results.sort(key=lambda x: x.score, reverse=True)
        return fused_results[:top_k]
```

### 3. 性能优化

**缓存优化**:
```python
from functools import lru_cache
import time

class CachedRetriever(BaseRetriever):
    """带缓存的检索器"""
    
    def __init__(self, retriever: BaseRetriever, config=None):
        super().__init__(config)
        self.retriever = retriever
        self.config = config or {}
        
        # 缓存配置
        cache_config = self.config.get('cache', {})
        self.cache_enabled = cache_config.get('enabled', True)
        self.cache_ttl = cache_config.get('ttl', 3600)  # 秒
        self.max_cache_size = cache_config.get('size', 1000)
        
        # 初始化缓存
        self.cache = {}
        self.cache_timestamps = {}
    
    def retrieve(self, query: str, top_k: int = 5) -> List[SearchResult]:
        """带缓存的检索"""
        if not self.cache_enabled:
            return self.retriever.retrieve(query, top_k)
        
        # 生成缓存键
        cache_key = self._generate_cache_key(query, top_k)
        
        # 检查缓存
        if cache_key in self.cache:
            cache_entry = self.cache[cache_key]
            cache_time = self.cache_timestamps[cache_key]
            
            # 检查是否过期
            if time.time() - cache_time < self.cache_ttl:
                logger.debug(f"缓存命中: {query}")
                return cache_entry
        
        # 缓存未命中，执行检索
        logger.debug(f"缓存未命中: {query}")
        results = self.retriever.retrieve(query, top_k)
        
        # 更新缓存
        self._update_cache(cache_key, results)
        
        return results
    
    def _generate_cache_key(self, query: str, top_k: int) -> str:
        """生成缓存键"""
        # 使用查询内容和参数的哈希作为键
        import hashlib
        key_data = f"{query}_{top_k}_{self.retriever.__class__.__name__}"
        return hashlib.md5(key_data.encode('utf-8')).hexdigest()
    
    def _update_cache(self, key: str, results: List[SearchResult]):
        """更新缓存"""
        # 清理过期缓存
        self._cleanup_expired_cache()
        
        # 如果缓存已满，移除最旧的条目
        if len(self.cache) >= self.max_cache_size:
            oldest_key = min(self.cache_timestamps, key=self.cache_timestamps.get)
            del self.cache[oldest_key]
            del self.cache_timestamps[oldest_key]
        
        # 添加新缓存条目
        self.cache[key] = results
        self.cache_timestamps[key] = time.time()
    
    def _cleanup_expired_cache(self):
        """清理过期缓存"""
        current_time = time.time()
        expired_keys = [
            key for key, timestamp in self.cache_timestamps.items()
            if current_time - timestamp >= self.cache_ttl
        ]
        
        for key in expired_keys:
            del self.cache[key]
            del self.cache_timestamps[key]
        
        if expired_keys:
            logger.debug(f"清理了 {len(expired_keys)} 个过期缓存条目")
```

---

## 常见问题

### Q1: 检索结果不相关怎么办？

**可能原因和解决方案**:
1. **编码器质量**: 尝试使用更好的编码器模型
2. **向量数据库索引**: 确保向量数据库索引构建正确
3. **查询预处理**: 优化查询预处理流程
4. **相似度阈值**: 调整相似度阈值过滤不相关结果
5. **启用重排序**: 使用重排序提高结果相关性

**调试步骤**:
1. 检查查询编码是否正确
2. 验证向量数据库中的文档向量
3. 分析相似度分数分布
4. 查看 top-k 结果的详细内容

### Q2: 检索速度慢怎么办？

**性能优化建议**:
1. **批处理**: 使用批处理检索减少编码次数
2. **缓存**: 启用查询结果缓存
3.