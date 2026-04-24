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

Vector Store 模块是文档 RAG 系统的向量存储组件，负责存储和管理文档的向量表示。该模块提供标准化的向量数据库接口，支持向量的存储、检索和删除操作，是 RAG 系统中检索功能的核心基础。

### 主要功能

1. **向量存储**: 高效存储大规模向量数据
2. **相似度搜索**: 基于向量相似度的快速检索
3. **元数据管理**: 存储和检索文档的元数据信息
4. **持久化存储**: 数据持久化到磁盘，支持重启恢复
5. **ID 管理**: 支持查询已存储的文档 ID，便于增量更新

### 架构设计

```
┌──────────────────────────────────────────────────────┐
│                  BaseVectorStore                      │
│                    (抽象基类)                          │
│                                                       │
│  + initialize()          初始化数据库连接              │
│  + add()                 添加文档向量                  │
│  + search()              搜索相似文档                  │
│  + delete()              删除文档                      │
│  + get_stats()           获取统计信息                  │
│  + get_existing_ids()    获取已存储ID列表              │
└──────────────────────────────────────────────────────┘
                        ▲
                        │ 继承
┌──────────────────────────────────────────────────────┐
│                   ChromaStore                         │
│                                                       │
│  基于 Chroma 向量数据库的实现                          │
│  支持 HNSW 索引、多种距离度量                          │
└──────────────────────────────────────────────────────┘
```

---

## 文件结构

```
src/vector_stores/
├── __init__.py              # 模块导出
├── base.py                  # 基类和接口定义
└── chroma_store.py          # Chroma向量数据库实现
```

**模块导出** (`__init__.py`):

```python
from .base import BaseVectorStore
from .chroma_store import ChromaStore

__all__ = [
    "BaseVectorStore",
    "ChromaStore",
]
```

---

## 核心类与接口

### 1. SearchResult (搜索结果类)

定义向量搜索返回的结果结构：

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
        self.id = id
        self.content = content
        self.score = score
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（支持JSON序列化）"""
        return {
            'id': self.id,
            'content': self.content,
            'score': self.score,
            'metadata': self.metadata,
        }
```

### 2. BaseVectorStore (抽象基类)

所有向量数据库的基类，定义统一的向量存储接口：

```python
class BaseVectorStore(ABC):
    """向量数据库基类"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化向量数据库

        Args:
            config: 配置字典
        """
        self.config = config or {}
        self.is_initialized = False

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
        添加文档

        Args:
            ids: 文档ID列表
            embeddings: Embedding向量，形状为 (N, D)
            contents: 文档内容列表
            metadatas: 元数据列表
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def delete(self, ids: List[str]):
        """
        删除文档

        Args:
            ids: 文档ID列表
        """
        pass

    def get_existing_ids(self) -> List[str]:
        """
        获取向量数据库中所有已存储的文档ID

        Returns:
            已存储的ID列表（默认返回空列表，子类可覆盖）
        """
        return []

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """
        获取数据库统计信息

        Returns:
            统计信息字典
        """
        pass
```

### 3. ChromaStore (Chroma向量数据库实现)

基于 Chroma 向量数据库的实现：

```python
class ChromaStore(BaseVectorStore):
    """Chroma向量数据库"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化Chroma存储

        Args:
            config: 配置字典，支持两种结构：
                直接配置:
                    - persist_directory: 持久化目录
                    - collection_name: 集合名称
                    - hnsw_space: 距离度量 (cosine/l2/ip)
                    - hnsw_construction_ef: HNSW构建参数
                    - hnsw_search_ef: HNSW搜索参数
                    - hnsw_M: HNSW参数M
                嵌套配置（适配 configs.yaml 结构）:
                    - vector_store.chroma.persist_directory
                    - vector_store.chroma.collection_name
                    - ...
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
        query_embedding: np.ndarray,
        top_k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """搜索相似文档"""

    def delete(self, ids: List[str]):
        """删除文档"""

    def get_existing_ids(self) -> List[str]:
        """获取所有已存储的文档ID"""

    def get_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
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

### 3. 距离度量与分数转换

Chroma 支持多种距离度量方式，代码中实现了对应的分数转换逻辑：

#### 3.1 余弦相似度 (cosine)
```
distance ∈ [0, 2]
similarity = 1 - distance / 2  →  similarity ∈ [0, 1]
```
- **特点**: 衡量向量方向相似性，忽略向量长度
- **适用场景**: 文本嵌入向量，语义相似度计算

#### 3.2 欧氏距离 (l2)
```
distance ∈ [0, ∞)
similarity = exp(-distance)  →  similarity ∈ (0, 1]
```
- **特点**: 衡量向量空间中的实际距离
- **适用场景**: 图像嵌入向量，空间距离计算

#### 3.3 内积 (ip)
```
similarity = distance  (直接使用)
```
- **特点**: 简单的点积相似度
- **适用场景**: 特定嵌入模型，需要自定义相似度计算

### 4. 配置读取机制

`ChromaStore` 的 `__init__` 方法支持两种配置结构，以兼容直接配置和 `configs.yaml` 嵌套配置：

```python
# 1. 直接配置（扁平结构）
config = {
    "persist_directory": "./chroma_db",
    "collection_name": "my_collection",
    "hnsw_space": "cosine",
}

# 2. 嵌套配置（适配 configs.yaml 结构）
config = {
    "vector_store": {
        "chroma": {
            "persist_directory": "./chroma_db",
            "collection_name": "my_collection",
            "hnsw_space": "cosine",
        }
    }
}
```

读取优先级：优先读取 `config['vector_store']['chroma']`，如果不存在则回退到 `config` 本身。

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

**初始化流程**:
1. 检查是否已初始化，避免重复连接
2. 创建 `PersistentClient`，连接到持久化目录
3. 尝试获取已存在的集合（`get_collection`）
4. 如果集合不存在，则使用 HNSW 参数创建新集合（`create_collection`）
5. 标记初始化状态为 `True`

### 2. 添加文档向量

```python
def add(
    self,
    ids: List[str],
    embeddings: np.ndarray,
    contents: List[str],
    metadatas: Optional[List[Dict[str, Any]]] = None
):
    """添加文档"""
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
```

**添加流程**:
1. 检查初始化状态，未初始化则自动初始化
2. 将 `np.ndarray` 格式的 embeddings 转为 `list` 格式
3. 直接调用 Chroma 的 `collection.add()` 方法进行批量添加
4. 支持空元数据（传入 `None` 时 Chroma 会自动处理）

### 3. 相似度搜索

```python
def search(
    self,
    query_embedding: np.ndarray,
    top_k: int = 5,
    filter_dict: Optional[Dict[str, Any]] = None
) -> List[SearchResult]:
    """搜索相似文档"""
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
        distance = results['distances'][0][i] if 'distances' in results else 0.0

        # 根据距离度量类型转换分数
        if self.hnsw_space == 'cosine':
            similarity = 1 - distance / 2
        elif self.hnsw_space == 'l2':
            similarity = np.exp(-distance)
        else:
            similarity = distance

        result = SearchResult(
            id=results['ids'][0][i],
            content=results['documents'][0][i],
            score=float(similarity),
            metadata=results['metadatas'][0][i] if 'metadatas' in results else {}
        )
        search_results.append(result)

    # 按相似度降序排序
    search_results.sort(key=lambda x: x.score, reverse=True)

    return search_results
```

**搜索流程**:
1. 检查初始化状态，未初始化则自动初始化
2. 将查询向量转为 `list` 格式
3. 如果是二维数组（批量查询格式），自动取第一个向量
4. 调用 Chroma 的 `collection.query()` 方法执行搜索
5. 支持通过 `filter_dict` 参数传入元数据过滤条件（`where` 子句）
6. 对每个结果进行距离到相似度的转换
7. 按相似度降序排序后返回

### 4. 删除操作

```python
def delete(self, ids: List[str]):
    """删除文档"""
    if not self.is_initialized:
        self.initialize()

    self.collection.delete(ids=ids)
```

**删除流程**:
1. 检查初始化状态，未初始化则自动初始化
2. 调用 Chroma 的 `collection.delete()` 方法，根据 ID 列表删除文档

### 5. 获取已存储的 ID 列表

```python
def get_existing_ids(self) -> List[str]:
    """获取向量数据库中所有已存储的文档ID"""
    if not self.is_initialized:
        self.initialize()
    try:
        result = self.collection.get()
        return result.get('ids', []) if result else []
    except Exception:
        return []
```

**用途**: 在增量更新时，检查哪些文档已存在于向量数据库中，避免重复添加。

**返回值**: `List[str]` - 所有已存储的文档 ID 列表，失败时返回空列表。

### 6. 统计信息

```python
def get_stats(self) -> Dict[str, Any]:
    """获取数据库统计信息"""
    if not self.is_initialized:
        self.initialize()

    count = self.collection.count()

    return {
        'collection_name': self.collection_name,
        'document_count': count,
        'persist_directory': self.persist_directory,
    }
```

**返回值**:
- `collection_name`: 集合名称
- `document_count`: 文档数量
- `persist_directory`: 持久化目录路径

---

## 配置参数

### 1. 基础配置

在 `src/configs/default_config.yaml` 或自定义 `config.yaml` 中配置：

```yaml
vector_store:
  # 向量数据库类型: chroma (目前仅支持Chroma)
  type: "chroma"

  chroma:
    # 存储配置
    persist_directory: "./chroma_db"    # 持久化目录
    collection_name: "doc_rag_collection"  # 集合名称

    # HNSW索引配置
    hnsw_space: "cosine"               # 距离度量: cosine/l2/ip
    hnsw_construction_ef: 128          # 构建时的搜索范围
    hnsw_search_ef: 64                 # 搜索时的搜索范围
    hnsw_M: 16                         # 每个节点的最大连接数
```

### 2. 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `type` | `chroma` | 向量数据库类型 |
| `chroma.persist_directory` | `./chroma_db` | 数据持久化目录 |
| `chroma.collection_name` | `doc_rag_collection` | 集合名称 |
| `chroma.hnsw_space` | `cosine` | 距离度量方式 |
| `chroma.hnsw_construction_ef` | `128` | HNSW 构建参数，越大索引质量越高 |
| `chroma.hnsw_search_ef` | `64` | HNSW 搜索参数，越大召回率越高 |
| `chroma.hnsw_M` | `16` | HNSW 每个节点的最大连接数 |

### 3. 距离度量配置示例

#### 余弦相似度（推荐用于文本）
```yaml
vector_store:
  chroma:
    hnsw_space: "cosine"
```

#### 欧氏距离
```yaml
vector_store:
  chroma:
    hnsw_space: "l2"
```

#### 内积相似度
```yaml
vector_store:
  chroma:
    hnsw_space: "ip"
```

---

## 使用示例

### 1. 基本使用 - 扁平配置

```python
from src.vector_stores import ChromaStore
import numpy as np

# 初始化向量数据库（扁平配置）
config = {
    "persist_directory": "./chroma_db",
    "collection_name": "my_collection",
    "hnsw_space": "cosine",
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
results = vector_store.search(query_vector, top_k=3)

# 处理结果
print(f"找到 {len(results)} 个相关文档:")
for i, result in enumerate(results):
    print(f"{i+1}. ID: {result.id}, 分数: {result.score:.3f}")
    print(f"   内容: {result.content[:50]}...")
    print(f"   元数据: {result.metadata}")

# 转换为字典
result_dict = results[0].to_dict()
```

### 2. 使用嵌套配置（适配 configs.yaml）

```python
from src.vector_stores import ChromaStore
from src.configs import ConfigManager

# 通过配置管理器读取配置
config_manager = ConfigManager(config_path="./config.yaml")
config = config_manager.config

# 初始化向量数据库（嵌套配置，自动适配）
vector_store = ChromaStore(config)

# 添加文档
vector_store.add(
    ids=["doc_001"],
    embeddings=np.random.randn(1, 768),
    contents=["示例文档内容"],
    metadatas=[{"source": "example.pdf"}]
)
```

### 3. 带过滤条件的搜索

```python
from src.vector_stores import ChromaStore
import numpy as np

vector_store = ChromaStore()

# 搜索时使用元数据过滤
query_vector = np.random.randn(768)
results = vector_store.search(
    query_embedding=query_vector,
    top_k=5,
    filter_dict={"source": "report.pdf"}  # 只搜索来自report.pdf的文档
)

for result in results:
    print(f"ID: {result.id}, 分数: {result.score:.3f}")
```

### 4. 数据库管理操作

```python
from src.vector_stores import ChromaStore

vector_store = ChromaStore()

# 获取统计信息
stats = vector_store.get_stats()
print("数据库统计信息:")
for key, value in stats.items():
    print(f"  {key}: {value}")

# 获取已存储的ID列表
existing_ids = vector_store.get_existing_ids()
print(f"已存储 {len(existing_ids)} 个文档")

# 删除文档
if existing_ids:
    vector_store.delete(existing_ids[:2])
    print("已删除前2个文档")
```

### 5. 增量更新场景

```python
from src.vector_stores import ChromaStore
import numpy as np

vector_store = ChromaStore()

# 获取已存在的文档ID
existing_ids = set(vector_store.get_existing_ids())

# 准备新文档
new_ids = ["doc_001", "doc_002", "doc_003"]

# 过滤出尚未存储的文档
ids_to_add = [id for id in new_ids if id not in existing_ids]

if ids_to_add:
    embeddings = np.random.randn(len(ids_to_add), 768)
    contents = [f"文档 {id} 的内容" for id in ids_to_add]

    vector_store.add(
        ids=ids_to_add,
        embeddings=embeddings,
        contents=contents
    )
    print(f"新增 {len(ids_to_add)} 个文档")
else:
    print("所有文档已存在，无需添加")
```

---

## 扩展开发

### 1. 添加新的向量数据库支持

**步骤 1**: 创建新的向量数据库类，继承 `BaseVectorStore`

```python
from src.vector_stores.base import BaseVectorStore, SearchResult
import numpy as np
from typing import List, Dict, Any, Optional

class CustomVectorStore(BaseVectorStore):
    """自定义向量数据库"""

    def __init__(self, config=None):
        super().__init__(config)
        self.config = config or {}

        # 自定义存储结构
        self.vectors = {}      # id -> vector
        self.contents = {}     # id -> content
        self.metadatas = {}    # id -> metadata

    def initialize(self):
        """初始化"""
        self.is_initialized = True

    def add(
        self,
        ids: List[str],
        embeddings: np.ndarray,
        contents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None
    ):
        """添加文档"""
        if not self.is_initialized:
            self.initialize()

        for i, doc_id in enumerate(ids):
            self.vectors[doc_id] = embeddings[i] if isinstance(embeddings, np.ndarray) else np.array(embeddings[i])
            self.contents[doc_id] = contents[i]
            self.metadatas[doc_id] = metadatas[i] if metadatas else {}

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """搜索相似文档"""
        if not self.is_initialized:
            self.initialize()

        # 计算余弦相似度
        similarities = []
        query_vec = np.array(query_embedding)
        query_norm = np.linalg.norm(query_vec)

        for doc_id, vector in self.vectors.items():
            # 应用过滤条件
            if filter_dict:
                metadata = self.metadatas.get(doc_id, {})
                if not all(metadata.get(k) == v for k, v in filter_dict.items()):
                    continue

            vec = np.array(vector)
            dot = np.dot(query_vec, vec)
            norm = np.linalg.norm(vec)
            similarity = float(dot / (query_norm * norm)) if query_norm > 0 and norm > 0 else 0.0
            similarities.append((doc_id, similarity))

        # 排序取 top-k
        similarities.sort(key=lambda x: x[1], reverse=True)
        results = []
        for doc_id, score in similarities[:top_k]:
            results.append(SearchResult(
                id=doc_id,
                content=self.contents.get(doc_id, ""),
                score=score,
                metadata=self.metadatas.get(doc_id, {})
            ))
        return results

    def delete(self, ids: List[str]):
        """删除文档"""
        for doc_id in ids:
            self.vectors.pop(doc_id, None)
            self.contents.pop(doc_id, None)
            self.metadatas.pop(doc_id, None)

    def get_existing_ids(self) -> List[str]:
        """获取所有已存储的文档ID"""
        return list(self.vectors.keys())

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'document_count': len(self.vectors),
            'store_type': 'in_memory',
        }
```

**步骤 2**: 在 `__init__.py` 中注册新类

```python
from .base import BaseVectorStore
from .chroma_store import ChromaStore
from .custom_store import CustomVectorStore  # 新增

__all__ = [
    "BaseVectorStore",
    "ChromaStore",
    "CustomVectorStore",  # 新增
]
```

**步骤 3**: 更新配置支持

```yaml
vector_store:
  type: "custom"  # 新的向量数据库类型
```

### 2. 实现注意事项

- **ID 唯一性**: 确保传入的 ID 唯一，否则 Chroma 会覆盖已有数据
- **向量维度**: 同一集合中的所有向量维度必须一致
- **批量性能**: 建议每次添加 100-1000 条数据以获得最佳性能
- **错误处理**: `get_existing_ids()` 方法内部已包含异常捕获，不会因查询失败而中断流程

---

## 版本历史

| 版本 | 日期 | 修改内容 |
|------|------|----------|
| 1.0.0 | 2024-01 | 初始版本，基于 Chroma 实现基础向量存储功能 |
| 1.1.0 | 2024-06 | 新增 `get_existing_ids()` 和 `get_stats()` 方法，支持 `filter_dict` 过滤 |

---

**最后更新**: 2026-04-24
