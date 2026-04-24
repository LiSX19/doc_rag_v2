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
9. [集成方式](#集成方式)
10. [扩展开发](#扩展开发)

---

## 模块概述

Retriever 模块是文档 RAG 系统的检索组件，负责从向量数据库中检索与用户查询相关的文档片段。目前实现了基于稠密向量相似度的检索策略，并可选支持交叉编码器重排序以提高结果相关性。

### 主要功能

1. **向量检索**: 使用稠密向量编码器将查询转换为向量，在向量数据库中检索相似文档
2. **阈值过滤**: 基于相似度阈值过滤低质量结果
3. **重排序 (可选)**: 使用交叉编码器对初步检索结果进行重排序
4. **结果保存**: 支持将检索结果保存到文件
5. **批量检索**: 支持批量查询处理

### 当前状态

| 功能 | 状态 |
|------|------|
| 向量检索 (稠密) | ✅ 已实现 |
| 关键词检索 (BM25) | ❌ 未实现 |
| 混合检索 | ❌ 未实现 |
| 重排序 | ✅ 已实现 (可选) |
| 结果缓存 | ❌ 未实现 |
| 批量检索 | ✅ 已实现 (简单循环) |

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

### 1. SearchResult (搜索结果类)

定义在 `src/vector_stores/base.py`，是检索操作返回的数据结构：

```python
class SearchResult:
    """搜索结果类"""
    
    def __init__(
        self,
        id: str,                      # 文档唯一标识
        content: str,                 # 文档内容
        score: float,                 # 相似度分数
        metadata: Optional[Dict[str, Any]] = None  # 元数据
    ):
        ...
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（支持JSON序列化）"""
        return {
            'id': self.id,
            'content': self.content,
            'score': self.score,
            'metadata': self.metadata,
        }
```

### 2. BaseRetriever (抽象基类)

所有检索器的基类，定义统一的检索接口：

```python
class BaseRetriever(ABC):
    """检索器基类"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化检索器
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
    
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
        批量检索（默认实现为循环调用 retrieve）
        
        Args:
            queries: 查询文本列表
            top_k: 每个查询返回结果数量
            
        Returns:
            搜索结果列表的列表
        """
        return [self.retrieve(query, top_k) for query in queries]
```

### 3. VectorRetriever (向量检索器)

基于稠密向量相似度的检索器实现：

```python
class VectorRetriever(BaseRetriever):
    """向量检索器"""
    
    def __init__(
        self,
        embedder: BaseEncoder,
        vector_store: BaseVectorStore,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化向量检索器
        
        Args:
            embedder: 编码器（实际传入 DenseEncoder，调用其 embed() 方法）
            vector_store: 向量数据库
            config: 配置字典，包含：
                - retriever.top_k: 默认返回结果数量
                - retriever.filter.threshold: 相似度阈值
                - retriever.rerank.enabled: 是否启用重排序
                - retriever.rerank.model: 重排序模型
        """
    
    def retrieve(self, query: str, top_k: Optional[int] = None) -> List[SearchResult]:
        """执行向量检索"""
    
    def retrieve_and_save(
        self,
        query: str,
        filename: Optional[str] = None,
        top_k: Optional[int] = None
    ) -> List[SearchResult]:
        """检索并保存结果到文件"""
    
    def _rerank(self, query: str, results: List[SearchResult]) -> List[SearchResult]:
        """使用交叉编码器对搜索结果进行重排序"""
```

---

## 向量检索器

### 1. 向量检索原理

向量检索基于向量空间模型，将文本转换为高维向量，通过计算向量之间的相似度来度量文本之间的相关性。

**核心概念**:
- **查询编码**: 使用 `DenseEncoder.embed()` 将用户查询转换为稠密向量
- **向量相似度**: 计算查询向量与文档向量的余弦相似度（由向量数据库在搜索时计算）
- **相似度阈值**: 过滤低相似度的结果
- **Top-K 检索**: 返回相似度最高的 K 个结果

### 2. 检索流程详解

```
用户查询
    │
    ├─> 1. 查询编码
    │      └─ embedder.embed(query) → np.ndarray
    │
    ├─> 2. 向量搜索
    │      ├─ vector_store.search(query_embedding, top_k)
    │      ├─ 如果启用重排序，top_k 翻倍以获取更多候选结果
    │      └─ 返回 List[SearchResult]
    │
    ├─> 3. 阈值过滤
    │      └─ filter results by score >= threshold (默认 0.5)
    │
    ├─> 4. 重排序 (可选)
    │      ├─ CrossEncoder 对 (query, content) 对重新评分
    │      ├─ 替换原有分数为新分数
    │      └─ 按新分数降序排序
    │
    └─> 5. 限制结果数量
           └─ results[:top_k]
```

#### 步骤 1: 查询编码
```python
# 内部实现
query_embedding = self.embedder.embed(query)
# embed() 返回 np.ndarray，形状为 (1, dimension)
```

查询编码使用 `DenseEncoder.embed()` 方法，与构建知识库时使用的编码器保持一致，确保查询向量和文档向量在同一向量空间中。

#### 步骤 2: 向量搜索
```python
# 内部实现
results = self.vector_store.search(
    query_embedding=query_embedding,
    top_k=top_k * 2 if self.use_rerank else top_k
    # 如果重排序，多取一些候选结果
)
```

搜索由向量数据库（ChromaStore）的 `search()` 方法完成，返回包含 `SearchResult` 对象的列表。

#### 步骤 3: 阈值过滤
```python
# 内部实现
results = [r for r in results if r.score >= self.threshold]
```

默认阈值从配置读取（默认 0.5），只保留相似度不低于阈值的结果。

#### 步骤 4: 重排序
```python
def _rerank(self, query: str, results: List[SearchResult]) -> List[SearchResult]:
    """使用交叉编码器模型对搜索结果进行重排序"""
    try:
        if self._reranker_model is None:
            from sentence_transformers import CrossEncoder
            self._reranker_model = CrossEncoder(
                self.rerank_model,
                max_length=512,
                device='cpu',
            )

        pairs = [(query, r.content) for r in results]
        scores = self._reranker_model.predict(pairs)

        for r, score in zip(results, scores):
            r.score = float(score)

        return sorted(results, key=lambda x: x.score, reverse=True)

    except Exception as e:
        logger.warning(f"重排序失败，回退到原始分数排序: {e}")
        return sorted(results, key=lambda x: x.score, reverse=True)
```

重排序仅在 `self.use_rerank = True` 时执行，且仅在存在结果时触发。

### 3. 结果保存

```python
def retrieve_and_save(
    self,
    query: str,
    filename: Optional[str] = None,
    top_k: Optional[int] = None
) -> List[SearchResult]:
    """检索并保存结果"""
    results = self.retrieve(query, top_k)
    
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
```

保存的 JSON 文件包含查询原文、结果数量、时间戳和结果列表，默认保存在 `outputs/retrieval/` 目录。

---

## 重排序机制

### 1. 重排序原理

重排序 (Reranking) 是在初步检索后，使用更精确但计算成本更高的模型对结果进行重新评分和排序的过程。

**当前实现特点**:
- 使用 `sentence-transformers` 的 `CrossEncoder` 模型
- 直接替换原始相似度分数为重排序分数
- 仅在 CPU 上运行（device='cpu'）
- 不支持分数融合策略（仅替换模式）
- 如果重排序失败，回退到按原始分数排序

**重排序流程**:
```
初步检索结果 (top_k × 2)
    │
    ├─> 1. 加载 CrossEncoder 模型（延迟加载）
    │      └─ 首次使用时加载，之后复用
    │
    ├─> 2. 构建 (query, document) 对
    │      └─ pairs = [(query, r.content) for r in results]
    │
    ├─> 3. 模型预测
    │      └─ scores = self._reranker_model.predict(pairs)
    │
    ├─> 4. 替换分数
    │      └─ r.score = float(score)
    │
    └─> 5. 重新排序
           └─ sorted(results, key=lambda x: x.score, reverse=True)
```

### 2. 重排序配置

```yaml
retriever:
  rerank:
    enabled: false                    # 默认关闭
    model: "BAAI/bge-reranker-base"  # 重排序模型
```

### 3. 重排序模型

| 模型 | 说明 |
|------|------|
| `BAAI/bge-reranker-base` | 默认模型，中英文通用 |

---

## 配置参数

### 1. 完整配置
```yaml
retriever:
  top_k: 5                          # 返回结果数量
  filter:
    threshold: 0.5                  # 相似度阈值
  rerank:
    enabled: false                  # 是否启用重排序
    model: "BAAI/bge-reranker-base" # 重排序模型
```

### 2. 配置读取方式

```python
retriever_config = self.config.get('retriever', self.config)  # 兼容两种配置层级

self.top_k = retriever_config.get('top_k', 5)
self.threshold = retriever_config.get('filter', {}).get('threshold', 0.5)
self.use_rerank = retriever_config.get('rerank', {}).get('enabled', False)
self.rerank_model = retriever_config.get('rerank', {}).get('model', 'BAAI/bge-reranker-base')
```

### 3. 输出控制

检索结果保存受 `OutputManager` 输出模式控制：

| 输出模式 | 是否保存检索结果 |
|---------|----------------|
| `test` | ✅ 保存 |
| `production` | 取决于配置 |
| `minimal` | ❌ 不保存 |
| `custom` | 通过 `stages.retrieval` 控制 |

---

## 使用示例

### 1. 基本使用

```python
from src.retrievers import VectorRetriever
from src.encoders import DenseEncoder
from src.vector_stores import ChromaStore

# 初始化编码器
encoder = DenseEncoder(config)
encoder.initialize()

# 初始化向量数据库
vector_store = ChromaStore(config)
vector_store.initialize()

# 初始化检索器
retriever = VectorRetriever(
    embedder=encoder,
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

retriever = VectorRetriever(embedder, vector_store, config)

# 批量查询
queries = [
    "什么是机器学习？",
    "深度学习与机器学习的区别",
    "监督学习有哪些方法"
]

# 批量检索（默认实现为循环调用 retrieve）
all_results = retriever.retrieve_batch(queries, top_k=3)

for i, (query, results) in enumerate(zip(queries, all_results)):
    print(f"\n查询 {i+1}: {query}")
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
            "model": "BAAI/bge-reranker-base"
        }
    }
}

retriever = VectorRetriever(embedder, vector_store, config)

query = "神经网络的基本原理"
results = retriever.retrieve(query, top_k=5)

print("重排序后的结果:")
for i, result in enumerate(results):
    print(f"{i+1}. 分数: {result.score:.3f}")
    print(f"   内容: {result.content[:80]}...")
```

### 4. 检索并保存结果

```python
from src.retrievers import VectorRetriever

retriever = VectorRetriever(embedder, vector_store, config)

query = "人工智能的发展历史"
results = retriever.retrieve_and_save(
    query=query,
    filename="ai_history_retrieval",  # 可选，默认使用查询哈希
    top_k=5
)
# 结果保存到 outputs/retrieval/{filename}.json
```

### 5. 通过 PipelineManager 使用

```python
from src.pipeline_manager import PipelineManager
from src.configs import ConfigManager

config = ConfigManager(config_path="./config.yaml")
pipeline = PipelineManager(config)

# 执行检索（内部自动初始化检索器）
result = pipeline.retrieve(
    query="什么是机器学习？",
    top_k=5,
    threshold=0.5  # 可选，覆盖默认阈值
)

if result['status'] == 'success':
    for r in result['results']:
        print(f"分数: {r['score']:.3f} | 来源: {r['metadata'].get('source', '未知')}")
        print(f"内容: {r['content'][:200]}...")
```

### 6. 通过 CLI 使用

```bash
# 基本检索
python -m src.main retrieve --query "什么是机器学习？"

# 指定返回数量和阈值
python -m src.main retrieve -q "机器学习" -k 10 -t 0.3

# JSON 格式输出
python -m src.main retrieve -q "机器学习" --output-format json

# 不保存结果
python -m src.main retrieve -q "机器学习" --no-save
```

---

## 集成方式

### 1. PipelineManager 中的集成

检索器在 `PipelineManager` 中以属性方式懒加载：

```python
@property
def retriever(self):
    """获取检索器"""
    if self._retriever is None:
        from src.retrievers import VectorRetriever
        self._retriever = VectorRetriever(
            embedder=self.embedder,       # DenseEncoder 实例
            vector_store=self.vector_store, # ChromaStore 实例
            config=self.config.get_all()
        )
    return self._retriever
```

### 2. PipelineManager.retrieve() 方法

```python
def retrieve(self, query, top_k=5, threshold=None):
    # 检查向量数据库是否有数据
    if not self.check_vector_store():
        return {'status': 'error', 'message': '向量数据库为空'}
    
    # 执行检索
    results = self.retriever.retrieve(query, top_k=top_k)
    
    # 应用阈值过滤（额外的外层阈值过滤）
    if threshold:
        results = [r for r in results if r.score >= threshold]
    
    # 格式化返回
    return {
        'status': 'success',
        'query': query,
        'total_results': len(results),
        'results': [
            {
                'content': r.content,
                'score': float(r.score),
                'metadata': r.metadata
            }
            for r in results
        ]
    }
```

### 3. 数据流

```
build 阶段:
  文件 → Loader → Cleaner → Chunker → Deduper → Encoder → VectorStore
                                                              ↓
                                                     Chroma 数据库

retrieve 阶段:
  查询 → PipelineManager.retrieve()
          ├─ VectorRetriever.retrieve()
          │     ├─ embedder.embed(query) → 向量
          │     ├─ vector_store.search() → 结果
          │     ├─ 阈值过滤
          │     └─ 重排序 (可选)
          └─ 额外阈值过滤 (如果指定)
```

---

## 扩展开发

### 1. 支持新的编码器接口

如果使用新的编码器类型，确保编码器实现了 `embed()` 方法（接受字符串返回 `np.ndarray`），或修改 `VectorRetriever` 中的编码调用方式。

### 2. 添加新的检索算法

**步骤 1**: 创建新的检索器类

```python
from src.retrievers.base import BaseRetriever, SearchResult
from typing import List, Optional, Dict, Any

class CustomRetriever(BaseRetriever):
    """自定义检索器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        # 初始化自定义组件
    
    def retrieve(self, query: str, top_k: int = 5) -> List[SearchResult]:
        # 实现自定义检索逻辑
        pass
```

**步骤 2**: 在 `__init__.py` 中导出

```python
from .base import BaseRetriever
from .vector_retriever import VectorRetriever
from .custom_retriever import CustomRetriever  # 新增

__all__ = [
    "BaseRetriever",
    "VectorRetriever",
    "CustomRetriever",
]
```

**步骤 3**: 在 `PipelineManager` 中添加属性（可选）

### 3. 自定义重排序

可以通过重写 `_rerank` 方法来实现自定义重排序策略：

```python
class CustomRerankRetriever(VectorRetriever):
    """自定义重排序的向量检索器"""
    
    def _rerank(self, query: str, results: List[SearchResult]) -> List[SearchResult]:
        # 实现自定义重排序逻辑
        # 例如：融合原始分数和重排序分数
        reranked = super()._rerank(query, results)
        
        # 加权融合（示例）
        alpha = 0.7
        for r in reranked:
            original_score = r.metadata.get('original_score', r.score)
            r.score = alpha * r.score + (1 - alpha) * original_score
        
        return sorted(reranked, key=lambda x: x.score, reverse=True)
```

### 4. 添加混合检索（规划中）

混合检索需要同时实现向量检索和关键词检索，然后进行结果融合。当前版本尚未实现，这是未来的扩展方向。

---

## 常见问题

### Q1: 检索结果不相关怎么办？

**可能原因和解决方案**:
1. **编码器模型**: 默认使用 BAAI/bge-small-zh-v1.5，可尝试更大的模型如 `BAAI/bge-base-zh-v1.5`
2. **向量数据库**: 确保向量数据库已正确构建（运行 `build` 命令）
3. **相似度阈值**: 降低阈值以获取更多候选结果
4. **启用重排序**: 设置 `rerank.enabled: true` 使用交叉编码器提高相关性
5. **文档质量**: 检查文档加载和清洗是否正常，低质量文档会影响检索效果

### Q2: 检索速度慢怎么办？

**性能优化建议**:
1. **向量数据库配置**: 调整 Chroma 的 HNSW 参数（如 ef_search）
2. **减少结果数量**: 降低 `top_k` 值
3. **禁用重排序**: 重排序会增加显著延迟
4. **批量检索**: 使用 `retrieve_batch` 减少多次调用的开销

### Q3: 如何查看检索结果详情？

1. 使用 `retrieve_and_save()` 方法将结果保存为 JSON 文件
2. 在 CLI 中使用 `--output-format json` 输出详细 JSON 结果
3. 检查保存的 `outputs/retrieval/` 目录下的 JSON 文件

---

## 版本历史

| 版本 | 日期 | 修改内容 |
|-----|------|---------|
| 1.0.0 | 2024-01 | 初始版本，实现 VectorRetriever |
| 1.0.0+ | 当前 | 集成到 PipelineManager，支持 DenseEncoder embed() 接口，完成检索结果保存 |
