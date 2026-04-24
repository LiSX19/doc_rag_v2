# Vector Store 模块详细说明文档

## 目录
1. [模块概述](#模块概述)
2. [文件结构](#文件结构)
3. [核心类与接口](#核心类与接口)
4. [Chroma向量数据库](#chroma向量数据库)
5. [数据库操作](#数据库操作)
6. [配置参数](#配置参数)
7. [使用示例](#使用示例)
8. [扩展开发](#扩展开发)

---

## 模块概述

Vector Store 模块是文档 RAG 系统的向量存储组件，负责存储和管理文档的向量表示。该模块提供标准化的向量数据库接口，支持向量的存储、检索、更新和删除操作，是 RAG 系统中检索功能的核心基础。

### 主要功能

1. **向量存储**: 高效存储大规模向量数据
2. **相似度搜索**: 基于向量相似度的快速检索
3. **元数据管理**: 存储和检索文档的元数据信息
4. **索引管理**: 支持多种向量索引算法（如 HNSW）
5. **持久化存储**: 数据持久化到磁盘，支持重启恢复
6. **增量更新**: 支持向量的增量添加和更新

### 向量数据库工作流程

```
文档向量
    │
    ├─> 1. 向量预处理
    │      ├─ 向量归一化（确保单位长度）
    │      ├─ 维度验证
    │      └─ 数据类型转换
    │
    ├─> 2. 存储准备
    │      ├─ 生成唯一文档ID
    │      ├─ 准备元数据
    │      ├─ 批次组织（优化性能）
    │      └─ 索引构建准备
    │
    ├─> 3. 向量存储
    │      ├─ 连接向量数据库
    │      ├─ 创建或加载集合
    │      ├─ 批量插入向量
    │      └─ 更新索引
    │
    ├─> 4. 索引管理
    │      ├─ HNSW索引构建
    │      ├─ 索引优化
    │      ├─ 索引持久化
    │      └─ 索引参数调优
    │
    └─> 5. 检索准备
           ├─ 查询向量预处理
           ├─ 相似度计算配置
           ├─ 检索参数设置
           └─ 结果后处理准备
```

---

## 文件结构

```
src/vector_stores/
├── __init__.py              # 模块导出
├── base.py                  # 基类和接口定义
└── chroma_store.py          # Chroma向量数据库实现
```

---

## 核心类与接口

### 1. BaseVectorStore (抽象基类)

所有向量数据库的基类，定义统一的向量存储接口：

```python
class BaseVectorStore(ABC):
    """向量数据库基类"""
    
    @abstractmethod
    def initialize(self):
        """初始化数据库连接"""
        pass
    
    @abstractmethod
    def add(
        self,
        ids: List[str],
        embeddings: np.ndarray,
        contents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None
    ):
        """
        添加文档向量
        
        Args:
            ids: 文档ID列表
            embeddings: Embedding向量
            contents: 文档内容列表
            metadatas: 元数据列表
        """
        pass
    
    @abstractmethod
    def search(
        self,
        query_vector: np.ndarray,
        top_k: int = 5,
        threshold: Optional[float] = None
    ) -> List[SearchResult]:
        """
        搜索相似向量
        
        Args:
            query_vector: 查询向量
            top_k: 返回结果数量
            threshold: 相似度阈值
            
        Returns:
            搜索结果列表
        """
        pass
    
    @abstractmethod
    def delete(self, ids: List[str]):
        """删除文档"""
        pass
    
    @abstractmethod
    def count(self) -> int:
        """统计文档数量"""
        pass
    
    @abstractmethod
    def clear(self):
        """清空数据库"""
        pass
```

### 2. SearchResult (搜索结果类)

定义向量搜索返回的结果结构：

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
    
    @property
    def similarity(self) -> float:
        """相似度分数（别名）"""
        return self.score
    
    def get_document_info(self) -> Dict[str, Any]:
        """获取文档信息摘要"""
        return {
            "id": self.id,
            "content_preview": self.content[:100] + "..." if len(self.content) > 100 else self.content,
            "score": self.score,
            "metadata_keys": list(self.metadata.keys()) if self.metadata else []
        }
```

### 3. ChromaStore (Chroma向量数据库)

基于 Chroma 向量数据库的实现：

```python
class ChromaStore(BaseVectorStore):
    """Chroma向量数据库"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化Chroma存储
        
        Args:
            config: 配置字典，包含：
                - vector_store.chroma.persist_directory: 持久化目录
                - vector_store.chroma.collection_name: 集合名称
                - vector_store.chroma.hnsw_space: 距离度量 (cosine/l2/ip)
                - vector_store.chroma.hnsw_construction_ef: HNSW构建参数
                - vector_store.chroma.hnsw_search_ef: HNSW搜索参数
                - vector_store.chroma.hnsw_M: HNSW参数M
        """
    
    def initialize(self):
        """初始化数据库连接"""
    
    def add(
        self,
        ids: List[str],
        embeddings: np.ndarray,
        contents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None
    ):
        """添加文档向量"""
    
    def search(
        self,
        query_vector: np.ndarray,
        top_k: int = 5,
        threshold: Optional[float] = None
    ) -> List[SearchResult]:
        """搜索相似向量"""
    
    def delete(self, ids: List[str]):
        """删除文档"""
    
    def count(self) -> int:
        """统计文档数量"""
    
    def clear(self):
        """清空数据库"""
    
    def search_batch(
        self,
        query_vectors: np.ndarray,
        top_k: int = 5,
        threshold: Optional[float] = None
    ) -> List[List[SearchResult]]:
        """批量搜索"""
```

---

## Chroma向量数据库

### 1. Chroma 数据库简介

Chroma 是一个开源的向量数据库，专门为 AI 应用设计，具有以下特点：

**核心特性**:
- **轻量级**: 易于部署和使用
- **持久化**: 支持数据持久化到磁盘
- **高性能**: 基于 HNSW 索引的快速相似度搜索
- **可扩展**: 支持大规模向量存储
- **多语言支持**: Python、JavaScript 等客户端

**架构组件**:
1. **Client**: 数据库客户端，管理连接
2. **Collection**: 向量集合，类似关系数据库中的表
3. **Document**: 存储向量、内容和元数据的基本单元
4. **Index**: HNSW 索引，加速相似度搜索

### 2. HNSW 索引算法

HNSW (Hierarchical Navigable Small World) 是一种高效的近似最近邻搜索算法：

**算法原理**:
1. **层次结构**: 构建多层次的图结构，高层包含较少节点，用于快速导航
2. **小世界网络**: 每个节点连接少量邻居，但整个网络具有短路径特性
3. **贪婪搜索**: 从高层开始，逐层向下搜索，找到最近邻

**关键参数**:
- **M**: 每个节点的最大连接数，影响索引构建时间和搜索精度
- **efConstruction**: 构建时的搜索范围，影响索引质量
- **efSearch**: 搜索时的搜索范围，影响搜索精度和速度
- **space**: 距离度量空间（cosine/l2/ip）

**参数调优建议**:
- **高质量索引**: 提高 M 和 efConstruction，但会增加构建时间
- **快速搜索**: 降低 efSearch，但可能降低精度
- **平衡配置**: 根据数据规模和性能要求调整参数

### 3. 距离度量

Chroma 支持多种距离度量方式：

#### 3.1 余弦相似度 (cosine)
```
similarity = (A · B) / (||A|| × ||B||)
```
- **范围**: [-1, 1]，通常归一化到 [0, 1]
- **特点**: 衡量向量方向相似性，忽略向量长度
- **适用场景**: 文本嵌入向量，语义相似度计算

#### 3.2 欧氏距离 (l2)
```
distance = √Σ(Aᵢ - Bᵢ)²
```
- **范围**: [0, ∞)
- **特点**: 衡量向量空间中的实际距离
- **适用场景**: 图像嵌入向量，空间距离计算

#### 3.3 内积 (ip)
```
similarity = A · B
```
- **范围**: (-∞, ∞)
- **特点**: 简单的点积相似度
- **适用场景**: 特定嵌入模型，需要自定义相似度计算

### 4. 数据模型

#### 4.1 文档结构
```python
{
    "id": "doc_001",                    # 文档唯一ID
    "embedding": [0.1, 0.2, ..., 0.768], # 768维向量
    "content": "文档内容文本...",         # 原始文本内容
    "metadata": {                       # 元数据
        "source": "document.pdf",
        "page": 1,
        "chunk_index": 0,
        "timestamp": "2024-01-15T10:30:00Z"
    }
}
```

#### 4.2 集合结构
```python
{
    "name": "doc_rag_collection",       # 集合名称
    "metadata": {                       # 集合元数据
        "hnsw:space": "cosine",
        "hnsw:construction_ef": 128,
        "hnsw:search_ef": 64,
        "hnsw:M": 16,
        "description": "文档RAG系统向量集合",
        "created_at": "2024-01-15T10:30:00Z"
    },
    "count": 10000,                     # 文档数量
    "dimension": 768,                   # 向量维度
    "statistics": {                     # 统计信息
        "avg_vector_norm": 1.0,
        "min_similarity": 0.2,
        "max_similarity": 1.0
    }
}
```

---

## 数据库操作

### 1. 初始化与连接

```python
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
```

### 2. 添加文档向量

```python
def add(
    self,
    ids: List[str],
    embeddings: np.ndarray,
    contents: List[str],
    metadatas: Optional[List[Dict[str, Any]]] = None
):
    """添加文档向量"""
    if not self.is_initialized:
        self.initialize()
    
    # 数据验证
    self._validate_add_data(ids, embeddings, contents, metadatas)
    
    # 向量归一化（如果使用余弦相似度）
    if self.hnsw_space == 'cosine':
        embeddings = self._normalize_embeddings(embeddings)
    
    # 准备元数据
    if metadatas is None:
        metadatas = [{} for _ in range(len(ids))]
    
    # 确保embeddings是列表格式
    embedding_list = embeddings.tolist()
    
    # 批量添加（Chroma自动处理批量）
    self.collection.add(
        ids=ids,
        embeddings=embedding_list,
        documents=contents,
        metadatas=metadatas
    )
    
    logger.info(f"成功添加 {len(ids)} 个文档到向量数据库")
```

### 3. 相似度搜索

```python
def search(
    self,
    query_vector: np.ndarray,
    top_k: int = 5,
    threshold: Optional[float] = None
) -> List[SearchResult]:
    """搜索相似向量"""
    if not self.is_initialized:
        self.initialize()
    
    # 查询向量归一化
    if self.hnsw_space == 'cosine':
        query_vector = self._normalize_vector(query_vector)
    
    # 执行搜索
    results = self.collection.query(
        query_embeddings=[query_vector.tolist()],
        n_results=top_k * 2,  # 获取更多结果以供过滤
        include=["documents", "metadatas", "distances"]
    )
    
    # 处理搜索结果
    search_results = []
    if results['documents'] and results['documents'][0]:
        for i, (doc_id, content, distance, metadata) in enumerate(
            zip(
                results['ids'][0],
                results['documents'][0],
                results['distances'][0],
                results['metadatas'][0]
            )
        ):
            # 将距离转换为相似度分数
            score = self._distance_to_score(distance)
            
            # 应用阈值过滤
            if threshold is not None and score < threshold:
                continue
            
            # 创建搜索结果对象
            result = SearchResult(
                id=doc_id,
                content=content,
                score=score,
                metadata=metadata
            )
            search_results.append(result)
    
    # 按分数排序并返回top-k
    search_results.sort(key=lambda x: x.score, reverse=True)
    return search_results[:top_k]
```

### 4. 批量搜索

```python
def search_batch(
    self,
    query_vectors: np.ndarray,
    top_k: int = 5,
    threshold: Optional[float] = None
) -> List[List[SearchResult]]:
    """批量搜索"""
    if not self.is_initialized:
        self.initialize()
    
    # 查询向量归一化
    if self.hnsw_space == 'cosine':
        query_vectors = self._normalize_embeddings(query_vectors)
    
    # 执行批量搜索
    results = self.collection.query(
        query_embeddings=query_vectors.tolist(),
        n_results=top_k * 2,
        include=["documents", "metadatas", "distances"]
    )
    
    # 处理批量结果
    all_search_results = []
    for query_idx in range(len(query_vectors)):
        query_results = []
        
        if (results['documents'] and results['documents'][query_idx]):
            for i, (doc_id, content, distance, metadata) in enumerate(
                zip(
                    results['ids'][query_idx],
                    results['documents'][query_idx],
                    results['distances'][query_idx],
                    results['metadatas'][query_idx]
                )
            ):
                # 将距离转换为相似度分数
                score = self._distance_to_score(distance)
                
                # 应用阈值过滤
                if threshold is not None and score < threshold:
                    continue
                
                # 创建搜索结果对象
                result = SearchResult(
                    id=doc_id,
                    content=content,
                    score=score,
                    metadata=metadata
                )
                query_results.append(result)
        
        # 按分数排序并返回top-k
        query_results.sort(key=lambda x: x.score, reverse=True)
        all_search_results.append(query_results[:top_k])
    
    return all_search_results
```

### 5. 删除操作

```python
def delete(self, ids: List[str]):
    """删除文档"""
    if not self.is_initialized:
        self.initialize()
    
    if not ids:
        return
    
    # 执行删除
    self.collection.delete(ids=ids)
    logger.info(f"成功删除 {len(ids)} 个文档")
    
    # 可选：清理索引碎片
    if self.config.get('optimize_after_delete', False):
        self._optimize_index()

def _optimize_index(self):
    """优化索引（减少碎片）"""
    # Chroma 目前不直接提供索引优化接口
    # 可以通过重建集合或等待自动优化
    logger.info("索引优化建议：定期重建集合以获得最佳性能")
```

### 6. 统计与监控

```python
def count(self) -> int:
    """统计文档数量"""
    if not self.is_initialized:
        self.initialize()
    
    return self.collection.count()

def get_stats(self) -> Dict[str, Any]:
    """获取数据库统计信息"""
    if not self.is_initialized:
        self.initialize()
    
    count = self.collection.count()
    metadata = self.collection.metadata or {}
    
    return {
        "collection_name": self.collection_name,
        "document_count": count,
        "index_type": "HNSW",
        "distance_metric": metadata.get("hnsw:space", "cosine"),
        "index_params": {
            "M": metadata.get("hnsw:M", 16),
            "efConstruction": metadata.get("hnsw:construction_ef", 128),
            "efSearch": metadata.get("hnsw:search_ef", 64)
        },
        "persist_directory": self.persist_directory,
        "is_initialized": self.is_initialized
    }

def monitor_performance(self, num_queries: int = 100) -> Dict[str, float]:
    """监控性能指标"""
    # 生成测试查询
    test_queries = self._generate_test_queries(num_queries)
    
    import time
    latencies = []
    
    for query_vector in test_queries:
        start_time = time.time()
        self.search(query_vector, top_k=5)
        latency = time.time() - start_time
        latencies.append(latency)
    
    return {
        "avg_latency_ms": sum(latencies) / len(latencies) * 1000,
        "p95_latency_ms": sorted(latencies)[int(len(latencies) * 0.95)] * 1000,
        "p99_latency_ms": sorted(latencies)[int(len(latencies) * 0.99)] * 1000,
        "min_latency_ms": min(latencies) * 1000,
        "max_latency_ms": max(latencies) * 1000,
        "qps_estimated": 1.0 / (sum(latencies) / len(latencies))
    }
```

---

## 配置参数

### 1. 基础配置
```yaml
vector_store:
  # 向量数据库类型: chroma (目前仅支持Chroma)
  type: "chroma"
  
  # 通用配置
  dimension: 768                      # 向量维度（自动检测）
  normalize_vectors: true             # 是否归一化向量
  batch_size: 100                     # 批处理大小
```

### 2. Chroma特定配置
```yaml
vector_store:
  type: "chroma"
  
  chroma:
    # 存储配置
    persist_directory: "./chroma_db"  # 持久化目录
    collection_name: "doc_rag_collection"  # 集合名称
    
    # HNSW索引配置
    hnsw_space: "cosine"              # 距离度量: cosine/l2/ip
    hnsw_construction_ef: 128         # 构建时的搜索范围
    hnsw_search_ef: 64                # 搜索时的搜索范围
    hnsw_M: 16                        # 每个节点的最大连接数
    
    # 性能配置
    batch_size: 100                   # 批处理大小
    auto_flush: true                  # 是否自动刷新
    flush_interval: 60                # 刷新间隔（秒）
    
    # 持久化配置
    persist_interval: 300             # 持久化间隔（秒）
    backup_enabled: true              # 是否启用备份
    backup_interval: 3600             # 备份间隔（秒）
```

### 3. 高级配置
```yaml
vector_store:
  type: "chroma"
  
  chroma:
    # 索引优化配置
    optimize:
      enabled: true                   # 是否启用索引优化
      rebuild_threshold: 0.3          # 重建阈值（碎片率）
      auto_rebuild: false             # 是否自动重建
      rebuild_interval: 86400         # 重建间隔（秒）
    
    # 缓存配置
    cache:
      enabled: true                   # 是否启用缓存
      size: 10000                     # 缓存大小
      ttl: 3600                       # 缓存生存时间（秒）
    
    # 监控配置
    monitoring:
      enabled: true                   # 是否启用监控
      metrics_interval: 60            # 指标收集间隔（秒）
      alert_thresholds:               # 告警阈值
        latency_ms: 100               # 延迟阈值（毫秒）
        error_rate: 0.01              # 错误率阈值
        memory_mb: 1024               # 内存阈值（MB）
```

### 4. 距离度量配置示例

#### 余弦相似度配置（推荐用于文本）
```yaml
vector_store:
  chroma:
    hnsw_space: "cosine"
    normalize_vectors: true           # 必须为true
    # 其他参数...
```

#### 欧氏距离配置
```yaml
vector_store:
  chroma:
    hnsw_space: "l2"
    normalize_vectors: false          # 通常为false
    # 其他参数...
```

#### 内积相似度配置
```yaml
vector_store:
  chroma:
    hnsw_space: "ip"
    normalize_vectors: false          # 通常为false
    # 其他参数...
```

---

## 使用示例

### 1. 基本使用
```python
from src.vector_stores import ChromaStore
import numpy as np

# 初始化向量数据库
config = {
    "vector_store": {
        "chroma": {
            "persist_directory": "./chroma_db",
            "collection_name": "my_collection",
            "hnsw_space": "cosine"
        }
    }
}

vector_store = ChromaStore(config)

# 准备数据
ids = ["doc_001", "doc_002", "doc_003"]
embeddings = np.random.randn(3, 768)  # 3个768维向量
contents = [
    "这是第一个文档的内容...",
    "这是第二个文档的内容...",
    "这是第三个文档的内容..."
]
metadatas = [
    {"source": "doc1.pdf", "page": 1},
    {"source": "doc2.pdf", "page": 2},
    {"source": "doc3.pdf", "page": 3}
]

# 添加文档
vector_store.add(ids, embeddings, contents, metadatas)

# 搜索相似文档
query_vector = np.random.randn(768)
results = vector_store.search(query_vector, top_k=3, threshold=0.5)

# 处理结果
print(f"找到 {len(results)} 个相关文档:")
for i, result in enumerate(results):
    print(f"{i+1}. ID: {result.id}, 分数: {result.score:.3f}")
    print(f"   内容: {result.content[:50]}...")
    print(f"   元数据: {result.metadata}")
```

### 2. 批量操作
```python
from src.vector_stores import ChromaStore
import numpy as np

# 初始化向量数据库
vector_store = ChromaStore()

# 批量添加文档
batch_size = 100
all_ids = []
all_embeddings = []
all_contents = []
all_metadatas = []

for i in range(10):  # 10个批次
    start_idx = i * batch_size
    end_idx = (i + 1) * batch_size
    
    # 准备批次数据
    batch_ids = [f"doc_{j}" for j in range(start_idx, end_idx)]
    batch_embeddings = np.random.randn(batch_size, 768)
    batch_contents = [f"文档 {j} 的内容..." for j in range(start_idx, end_idx)]
    batch_metadatas = [{"batch": i, "index": j % 10} for j in range(batch_size)]
    
    # 添加批次
    vector_store.add(batch_ids, batch_embeddings, batch_contents, batch_metadatas)
    
    # 收集数据用于后续测试
    all_ids.extend(batch_ids)
    all_embeddings.extend(batch_embeddings)
    all_contents.extend(batch_contents)
    all_metadatas.extend(batch_metadatas)

print(f"总共添加了 {len(all_ids)} 个文档")

# 批量搜索
query_vectors = np.random.randn(5, 768)  # 5个查询
all_results = vector_store.search_batch(query_vectors, top_k=3)

for i, results in enumerate(all_results):
    print(f"\n查询 {i+1} 的结果:")
    for j, result in enumerate(results):
        print(f"  {j+1}. {result.id} (分数: {result.score:.3f})")
```

### 3. 数据库管理
```python
from src.vector_stores import ChromaStore

# 初始化向量数据库
vector_store = ChromaStore()

# 获取统计信息
stats = vector_store.get_stats()
print("数据库统计信息:")
for key, value in stats.items():
    print(f"  {key}: {value}")

# 文档数量
count = vector_store.count()
print(f"文档总数: {count}")

# 性能监控
if count > 100:
    perf_stats = vector_store.monitor_performance(num_queries=50)
    print("\n性能指标:")
    for key, value in perf_stats.items():
        print(f"  {key}: {value:.2f}")

# 清理操作（示例）
if count > 10000:
    # 删除旧的文档（示例：删除ID以"old_"开头的文档）
    old_ids = [id for id in vector_store.get_all_ids() if id.startswith("old_")]
    if old_ids:
        print(f"准备删除 {len(old_ids)} 个旧文档")
        vector_store.delete(old_ids[:100])  # 分批删除
```

### 4. 自定义向量数据库
```python
from src.vector_stores.base import BaseVectorStore, SearchResult
import numpy as np
from typing import List, Dict, Any, Optional

class CustomVectorStore(BaseVectorStore):
    """自定义向量数据库示例"""
    
    def __init__(self, config=None):
        super().__init__(config)
        self.config = config or {}
        
        # 自定义存储结构
        self.vectors = {}      # id -> vector
        self.contents = {}     # id -> content
        self.metadatas = {}    # id -> metadata
        
        # 自定义索引
        self.index = self._build_index()
        
        logger.info("自定义向量数据库初始化完成")
    
    def _build_index(self):
        """构建自定义索引"""
        # 实现自定义索引结构
        # 例如：KD-Tree、Ball Tree、LSH等
        return {"type": "custom", "built": True}
    
    def initialize(self):
        """初始化（自定义逻辑）"""
        self.is_initialized = True
        logger.info("自定义向量数据库已初始化")
    
    def add(self, ids, embeddings, contents, metadatas=None):
        """添加文档（自定义实现）"""
        if not self.is_initialized:
            self.initialize()
        
        # 数据验证
        if len(ids) != len(embeddings) != len(contents):
            raise ValueError("ids、embeddings和contents长度必须一致")
        
        if metadatas is None:
            metadatas = [{} for _ in ids]
        
        # 存储数据
        for i, doc_id in enumerate(ids):
            self.vectors[doc_id] = embeddings[i]
            self.contents[doc_id] = contents[i]
            self.metadatas[doc_id] = metadatas[i]
        
        # 更新索引
        self._update_index(ids, embeddings)
        
        logger.info(f"添加了 {len(ids)} 个文档")
    
    def search(self, query_vector, top_k=5, threshold=None):
        """搜索相似向量（自定义实现）"""
        if not self.is_initialized:
            self.initialize()
        
        # 计算与所有向量的相似度
        similarities = []
        for doc_id, vector in self.vectors.items():
            # 计算余弦相似度
            similarity = self._cosine_similarity(query_vector, vector)
            
            # 应用阈值过滤
            if threshold is not None and similarity < threshold:
                continue
            
            similarities.append((doc_id, similarity))
        
        # 按相似度排序
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # 创建搜索结果
        results = []
        for doc_id, similarity in similarities[:top_k]:
            result = SearchResult(
                id=doc_id,
                content=self.contents[doc_id],
                score=similarity,
                metadata=self.metadatas[doc_id]
            )
            results.append(result)
        
        return results
    
    def _cosine_similarity(self, vec1, vec2):
        """计算余弦相似度"""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def delete(self, ids):
        """删除文档"""
        for doc_id in ids:
            if doc_id in self.vectors:
                del self.vectors[doc_id]
                del self.contents[doc_id]
                del self.metadatas[doc_id]
        
        # 更新索引
        self._update_index_after_delete(ids)
        
        logger.info(f"删除了 {len(ids)} 个文档")
    
    def count(self):
        """统计文档数量"""
        return len(self.vectors)
    
    def clear(self):
        """清空数据库"""
        self.vectors.clear()
        self.contents.clear()
        self.metadatas.clear()
        self.index = self._build_index()
        
        logger.info("数据库已清空")
```

### 5. 集成其他向量数据库
```python
import faiss
from src.vector_stores.base import BaseVectorStore, SearchResult

class FaissVectorStore(BaseVectorStore):
    """Faiss向量数据库集成"""
    
    def __init__(self, config=None):
        super().__init__(config)
        self.config = config or {}
        
        # Faiss配置
        self.dimension = self.config.get('dimension', 768)
        self.index_type = self.config.get('index_type', 'IVF')
        
        # 初始化Faiss索引
        self.index = self._create_faiss_index()
        self.id_to_index = {}  # 文档ID到Faiss索引的映射
        self.index_to_id = {}  # Faiss索引到文档ID的映射
        self.contents = {}     # 文档内容存储
        self.metadatas = {}    # 元数据存储
        
        logger.info(f"Faiss向量数据库初始化，维度: {self.dimension}, 索引类型: {self.index_type}")
    
    def _create_faiss_index(self):
        """创建Faiss索引"""
        if self.index_type == 'Flat':
            # 精确搜索，内存占用大
            index = faiss.IndexFlatIP(self.dimension)
        elif self.index_type == 'IVF':
            # 倒排文件，平衡精度和速度
            quantizer = faiss.IndexFlatIP(self.dimension)
            nlist = self.config.get('nlist', 100)  # 聚类中心数量
            index = faiss.IndexIVFFlat(quantizer, self.dimension, nlist, faiss.METRIC_INNER_PRODUCT)
            index.nprobe = self.config.get('nprobe', 10)  # 搜索的聚类中心数量
        elif self.index_type == 'HNSW':
            # 层次导航小世界图
            M = self.config.get('M', 16)  # 每个节点的连接数
            index = faiss.IndexHNSWFlat(self.dimension, M, faiss.METRIC_INNER_PRODUCT)
            index.hnsw.efConstruction = self.config.get('efConstruction', 40)
            index.hnsw.efSearch = self.config.get('efSearch', 16)
        else:
            raise ValueError(f"不支持的索引类型: {self.index_type}")
        
        return index
    
    def add(self, ids, embeddings, contents, metadatas=None):
        """添加文档到Faiss"""
        if not self.is_initialized:
            self.initialize()
        
        # 数据准备
        embeddings_np = np.array(embeddings).astype('float32')
        
        # 归一化向量（对于内积相似度）
        if self.index.metric_type == faiss.METRIC_INNER_PRODUCT:
            faiss.normalize_L2(embeddings_np)
        
        # 添加到Faiss索引
        start_idx = self.index.ntotal
        self.index.add(embeddings_np)
        
        # 更新映射
        for i, doc_id in enumerate(ids):
            idx = start_idx + i
            self.id_to_index[doc_id] = idx
            self.index_to_id[idx] = doc_id
            self.contents[doc_id] = contents[i]
            if metadatas:
                self.metadatas[doc_id] = metadatas[i]
            else:
                self.metadatas[doc_id] = {}
        
        # 训练索引（如果需要）
        if not self.index.is_trained and self.index_type != 'Flat':
            self.index.train(embeddings_np)
        
        logger.info(f"添加了 {len(ids)} 个文档到Faiss，总文档数: {self.index.ntotal}")
    
    def search(self, query_vector, top_k=5, threshold=None):
        """Faiss搜索"""
        if not self.is_initialized:
            self.initialize()
        
        # 准备查询向量
        query_np = np.array([query_vector]).astype('float32')
        
        # 归一化（对于内积相似度）
        if self.index.metric_type == faiss.METRIC_INNER_PRODUCT:
            faiss.normalize_L2(query_np)
        
        # 执行搜索
        distances, indices = self.index.search(query_np, top_k)
        
        # 处理结果
        results = []
        for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
            if idx == -1:  # Faiss返回-1表示没有足够的结果
                continue
            
            # 获取文档ID
            doc_id = self.index_to_id.get(idx)
            if not doc_id:
                continue
            
            # 将距离转换为相似度分数
            score = float(distance)
            
            # 应用阈值过滤
            if threshold is not None and score < threshold:
                continue
            
            # 创建搜索结果
            result = SearchResult(
                id=doc_id,
                content=self.contents[doc_id],
                score=score,
                metadata=self.metadatas[doc_id]
            )
            results.append(result)
        
        return results
```

---

## 扩展开发

### 1. 添加新的向量数据库支持

**步骤 1**: 创建新的向量数据库类
```python
from src.vector_stores.base import BaseVectorStore, SearchResult

class PineconeVectorStore(BaseVectorStore):
    """Pinecone向量数据库支持"""
    
    def __init__(self, config=None):
        super().__init__(config)
        self.config = config or {}
        
        # Pinecone配置
        pinecone_config = self.config.get('pinecone', {})
        self.api_key = pinecone_config.get('api_key')
        self.environment = pinecone_config.get('environment', 'us-west1-gcp')
        self.index_name = pinecone_config.get('index_name', 'doc-rag-index')
        
        # 初始化Pinecone客户端
        self._init_pinecone()
    
    def _init_pinecone(self):
        """初始化Pinecone"""
        import pinecone
        
        pinecone.init(
            api_key=self.api_key,
            environment=self.environment
        )
        
        # 获取或创建索引
        if self.index_name not in pinecone.list_indexes():
            # 创建新索引
            pinecone.create_index(
                name=self.index_name,
                dimension=self.config.get('dimension', 768),
                metric='cosine'
            )
        
        self.index = pinecone.Index(self.index_name)
        self.is_initialized = True
```

**步骤 2**: 实现核心接口
```python
class PineconeVectorStore(BaseVectorStore):
    # ... 初始化代码 ...
    
    def add(self, ids, embeddings, contents, metadatas=None):
        """添加文档到Pinecone"""
        if not self.is_initialized:
            self.initialize()
        
        # 准备数据
        vectors = []
        for i, (doc_id, embedding, content) in enumerate(zip(ids, embeddings, contents)):
            metadata = metadatas[i] if metadatas else {}
            metadata['content'] = content
            
            vectors.append((
                doc_id,
                embedding.tolist(),
                metadata
            ))
        
        # 批量上传
        self.index.upsert(vectors=vectors)
        
        logger.info(f"上传了 {len(ids)} 个文档到Pinecone")
    
    def search(self, query_vector, top_k=5, threshold=None):
        """Pinecone搜索"""
        if not self.is_initialized:
            self.initialize()
        
        # 执行搜索
        results = self.index.query(
            vector=query_vector.tolist(),
            top_k=top_k,
            include_metadata=True
        )
        
        # 处理结果
        search_results = []
        for match in results['matches']:
            score = match['score']
            
            # 应用阈值过滤
            if threshold is not None and score < threshold:
                continue
            
            # 创建搜索结果
            metadata = match['metadata']
            content = metadata.pop('content', '')
            
            result = SearchResult(
                id=match['id'],
                content=content,
                score=score,
                metadata=metadata
            )
            search_results.append(result)
        
        return search_results
```

**步骤 3**: 更新配置支持
```yaml
vector_store:
  type: "pinecone"  # 新的向量数据库类型
  
  pinecone:
    api_key: "your-pinecone-api-key"
    environment: "us-west1-gcp"
    index_name: "doc-rag-index"
    dimension: 768
    metric: "cosine"
```

### 2. 性能优化

**索引优化**:
```python
