# Encoder 模块详细说明文档

## 目录
1. [模块概述](#模块概述)
2. [文件结构](#文件结构)
3. [核心类与接口](#核心类与接口)
4. [编码器类型](#编码器类型)
5. [编码管理器](#编码管理器)
6. [配置参数](#配置参数)
7. [使用示例](#使用示例)
8. [扩展开发](#扩展开发)

---

## 模块概述

Encoder 模块是文档 RAG 系统的向量编码组件，负责将文本分块转换为向量表示。该模块统一了原先的 Embedder 和 Encoder 功能，提供多种编码策略：

- **稠密向量编码 (Dense Encoding)**: 使用预训练模型（如 BGE）生成高维稠密向量
- **稀疏向量编码 (Sparse Encoding)**: 使用 BM25/TF-IDF 算法生成稀疏向量
- **混合编码 (Hybrid Encoding)**: 结合稠密和稀疏向量的混合表示

### 主要功能

1. **统一编码接口**: 为不同类型的编码器提供一致的 API
2. **编码缓存**: 支持增量编码，避免重复计算
3. **批量编码**: 高效处理大规模文本分块
4. **元数据管理**: 记录编码过程中的元数据信息
5. **结果持久化**: 支持将编码结果保存为 `.npy` 文件
6. **与分块数据库集成**: 直接从 `ChunkDatabase` 读取分块并编码

### 编码流程

```
文本分块 (TextChunk)
    │
    ├─> 1. 编码器选择
    │      ├─ 根据配置选择编码器类型 (dense/sparse/hybrid)
    │      └─ 实例化对应的编码器 (懒加载)
    │
    ├─> 2. 编码计算
    │      ├─ 稠密编码: 使用 SentenceTransformer 模型
    │      ├─ 稀疏编码: 使用 BM25/TF-IDF 算法
    │      └─ 混合编码: 结合两种编码结果
    │
    ├─> 3. 结果封装
    │      ├─ 封装为 EncodedVector 对象
    │      ├─ 包含原始文本、向量和元数据
    │      └─ 支持 to_dict() / from_dict() 序列化
    │
    ├─> 4. 缓存管理
    │      ├─ 计算内容哈希 (MD5)
    │      ├─ 检查缓存命中
    │      ├─ 存储新的编码结果到数据库
    │      └─ 保存稠密向量为 .npy、稀疏向量为 .json
    │
    └─> 5. 结果导出
           ├─ 保存为 .npy 文件（稠密向量数组）
           ├─ 附带 .meta.json 元数据
           └─ 向量存储模块（ChromaStore）持久化
```

---

## 文件结构

```
src/encoders/
├── __init__.py              # 模块导出
├── base.py                  # 基类 EncodedVector、BaseEncoder
├── dense_encoder.py         # 稠密向量编码器 (BGE/BERT)
├── sparse_encoder.py        # 稀疏向量编码器 (BM25 / TF-IDF)
├── hybrid_encoder.py        # 混合编码器 (稠密 + 稀疏)
└── encoder_manager.py       # 编码管理器、EncodingRecord、EncodingDatabase
```

---

## 核心类与接口

### 1. BaseEncoder (抽象基类)

所有编码器的基类，定义统一的编码接口：

```python
class BaseEncoder(ABC):
    """编码器基类"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.is_initialized = False
    
    @abstractmethod
    def initialize(self):
        """初始化编码器（加载模型等）"""
        pass
    
    @abstractmethod
    def encode(self, text: str, chunk_id: Optional[str] = None) -> EncodedVector:
        """编码单个文本"""
        pass
    
    @abstractmethod
    def encode_batch(
        self, texts: List[str], chunk_ids: Optional[List[str]] = None
    ) -> List[EncodedVector]:
        """批量编码文本"""
        pass
    
    @property
    @abstractmethod
    def dimension(self) -> int:
        """返回向量维度"""
        pass
    
    @property
    @abstractmethod
    def vector_type(self) -> str:
        """返回向量类型 ('dense', 'sparse', 'hybrid')"""
        pass
    
    def encode_chunks(self, chunks: List[Any]) -> List[EncodedVector]:
        """编码分块对象列表（支持 ChunkRecord 和 dict）"""
```

### 2. EncodedVector (数据类)

统一表示编码结果的数据结构：

```python
@dataclass
class EncodedVector:
    """编码向量数据类"""
    
    chunk_id: str                                  # 分块唯一ID
    content: str                                   # 原始文本内容
    dense_vector: Optional[np.ndarray] = None      # 稠密向量
    sparse_vector: Optional[Dict[int, float]] = None  # 稀疏向量 {索引: 权重}
    metadata: Optional[Dict[str, Any]] = None      # 元数据
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（稠密向量转为 list）"""
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EncodedVector':
        """从字典创建实例（list 转回 ndarray）"""
    
    @property
    def has_dense(self) -> bool:
        """是否有稠密向量"""
    
    @property
    def has_sparse(self) -> bool:
        """是否有稀疏向量"""
    
    @property
    def is_hybrid(self) -> bool:
        """是否是混合向量（同时有稠密和稀疏）"""
```

### 3. EncodingRecord (编码记录)

记录单个分块的编码历史，用于增量缓存：

```python
class EncodingRecord:
    """编码记录"""
    
    chunk_id: str                   # 分块唯一ID
    content_hash: str               # 内容哈希 (MD5)
    dense_vector_path: Optional[str]  # 稠密向量 .npy 文件路径
    sparse_vector_path: Optional[str]  # 稀疏向量 .json 文件路径
    metadata: Dict[str, Any]        # 元数据
    encoded_at: str                 # 编码时间戳
```

### 4. EncodingDatabase (编码数据库)

管理编码记录的持久化存储：

```python
class EncodingDatabase:
    """编码结果数据库（JSON 文件存储）"""
    
    def __init__(self, db_path: Union[str, Path]):
        """加载或创建编码数据库"""
    
    def add_record(self, record: EncodingRecord):
        """添加单条编码记录"""
    
    def add_records(self, records: List[EncodingRecord]):
        """批量添加编码记录"""
    
    def get_record(self, chunk_id: str) -> Optional[EncodingRecord]:
        """获取编码记录"""
    
    def check_content_hash(self, chunk_id: str, content_hash: str) -> bool:
        """检查内容哈希是否匹配（判断是否需重新编码）"""
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息（总记录数、数据库路径）"""
```

### 5. EncoderManager (编码管理器)

管理编码器的创建、配置和批量操作：

```python
class EncoderManager:
    """编码管理器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Args:
            config: 配置字典，包含:
                - encoder.type: 编码器类型 ('dense', 'sparse', 'hybrid')
                - encoder.cache_dir: 缓存目录 (默认: ./cache/encodings)
                - encoder.incremental: 是否启用增量编码 (默认: true)
        """
    
    @property
    def encoder(self) -> BaseEncoder:
        """获取实际编码器实例（懒加载，首次访问时自动创建）"""
    
    def initialize(self):
        """初始化编码器（懒加载触发）"""
    
    def fit(self, texts: List[str]):
        """拟合编码器（稀疏/混合编码器需先拟合）"""
    
    def encode_chunks(
        self, chunks: List[Union[ChunkRecord, Dict[str, Any]]],
        use_cache: bool = True
    ) -> List[EncodedVector]:
        """编码分块列表（支持缓存）"""
    
    def encode_from_database(
        self, chunk_db: ChunkDatabase, use_cache: bool = True
    ) -> List[EncodedVector]:
        """从分块数据库编码所有分块（自动拟合稀疏编码器）"""
    
    def save_embeddings_to_npy(
        self, encoded_vectors: List[EncodedVector],
        output_path: Optional[Union[str, Path]] = None
    ) -> Path:
        """保存稠密向量为 .npy 文件（附带 .meta.json 元数据）"""
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
```

---

## 编码器类型

### 1. DenseEncoder (稠密向量编码器)

使用预训练模型生成稠密向量：

**支持模型**:
- `BAAI/bge-small-zh-v1.5` (默认)
- `BAAI/bge-base-zh-v1.5` (更高精度)
- `BAAI/bge-large-zh-v1.5`
- 其他 SentenceTransformer 兼容模型

**主要特性**:
- 支持本地模型路径
- 自动设备选择 (CPU/GPU)，支持 `auto` / `cpu` / `cuda`
- 向量归一化 (`normalize_embeddings=True`)
- 批处理优化 (`batch_size` 可配置)
- 指令前缀增强（BGE 模型推荐 `use_instruction: true`）
- 提供 `encode_and_save()` 快捷方法：编码后直接保存 `.npy` 文件

**配置示例**:
```yaml
encoder:
  type: "dense"
  dense:
    model_name: "BAAI/bge-small-zh-v1.5"
    model_path: null        # 本地模型路径（优先使用 model_name）
    device: "auto"          # auto/cpu/cuda
    normalize: true
    batch_size: 32
    max_seq_length: 512
    instruction: "为这个句子生成表示以用于检索相关文章："
    use_instruction: true
```

### 2. SparseEncoder (稀疏向量编码器)

默认使用 BM25 算法（`SparseEncoder = BM25Encoder`），同时提供 TF-IDF 实现。

#### 2.1 BM25 编码器
- 基于 Okapi BM25 算法
- 支持中英文混合分词（正则提取）
- 可配置参数 (k1, b)
- 需要先调用 `fit()` 拟合文档集合

#### 2.2 TF-IDF 编码器
- 基于 sklearn 的 TfidfVectorizer
- 支持 n-gram (默认 1-2 gram)
- 特征选择和过滤 (max_features, min_df, max_df)
- 需要先调用 `fit()` 拟合文档集合

```python
# 选择方式
from src.encoders.sparse_encoder import BM25Encoder, TFIDFEncoder
# 默认别名
SparseEncoder = BM25Encoder
```

**配置示例**:
```yaml
encoder:
  type: "sparse"
  sparse:
    # BM25 配置
    bm25:
      k1: 1.5              # 文档长度调节参数
      b: 0.75              # 文档长度归一化参数
      max_features: 50000  # 最大特征数
      min_df: 1            # 最小文档频率
      max_df: 0.95         # 最大文档频率

    # TF-IDF 配置
    tfidf:
      max_features: 50000
      min_df: 1
      max_df: 0.95
      ngram_range: [1, 2]  # n-gram范围
```

### 3. HybridEncoder (混合编码器)

结合稠密和稀疏向量的优势：

**主要特性**:
- 可配置权重比例 (dense_weight, sparse_weight)，自动归一化
- 支持不同的稀疏算法 (`sparse_type`: `bm25` / `tfidf`)
- 独立的子编码器配置 (`dense_config`, `sparse_config`)
- 提供 `compute_similarity()` 方法计算两个混合向量的加权相似度
- 子编码器懒加载

**相似度计算**:
```python
# 综合相似度 = dense_weight * 余弦相似度 + sparse_weight * 点积归一化
def compute_similarity(self, vec1: EncodedVector, vec2: EncodedVector) -> float:
    total_similarity = 0.0
    if vec1.has_dense and vec2.has_dense:
        dense_sim = cosine_similarity(vec1.dense_vector, vec2.dense_vector)
        total_similarity += self.dense_weight * dense_sim
    if vec1.has_sparse and vec2.has_sparse:
        sparse_sim = sparse_similarity(vec1.sparse_vector, vec2.sparse_vector)
        total_similarity += self.sparse_weight * sparse_sim
    return total_similarity
```

**配置示例**:
```yaml
encoder:
  type: "hybrid"
  hybrid:
    dense_weight: 0.7      # 稠密向量权重
    sparse_weight: 0.3     # 稀疏向量权重
    sparse_type: "bm25"    # bm25 / tfidf
    dense_config: {}       # 覆盖稠密编码器配置
    sparse_config: {}      # 覆盖稀疏编码器配置
```

---

## 编码管理器

### 1. 增量编码

支持增量更新，避免重复编码：

```python
# 启用增量编码（默认）
encoder_manager = EncoderManager(config)
# 编码文本分块（自动检查缓存）
encoded_vectors = encoder_manager.encode_chunks(chunks, use_cache=True)
```

**增量编码流程**:
1. 计算文本内容 MD5 哈希值
2. 查询 `EncodingDatabase` 中该 `chunk_id` 的记录
3. 如果缓存命中且内容哈希匹配，从 `.npy` / `.json` 加载缓存的向量
4. 如果缓存未命中或内容已变更，执行编码并存储结果

### 2. 编码缓存

缓存目录结构:
```
cache/encodings/
├── encoding_db.json              # 编码记录数据库
├── {chunk_id}_dense.npy          # 单个分块的稠密向量
└── {chunk_id}_sparse.json        # 单个分块的稀疏向量
```

**编码数据库结构** (`encoding_db.json`):
```json
{
  "records": [
    {
      "chunk_id": "文件路径#哈希值",
      "content_hash": "md5哈希值",
      "dense_vector_path": "cache/encodings/xxx_dense.npy",
      "sparse_vector_path": "cache/encodings/xxx_sparse.json",
      "metadata": {
        "vector_type": "dense",
        "model": "BAAI/bge-small-zh-v1.5"
      },
      "encoded_at": "2026-04-21T01:10:56.878852Z"
    }
  ],
  "updated_at": "2026-04-21T01:10:56.878852Z"
}
```

### 3. 批量编码优化

```python
# 批量编码（自动处理）
encoded_vectors = encoder_manager.encode_chunks(chunks, use_cache=True)
# 从分块数据库直接编码
encoded_vectors = encoder_manager.encode_from_database(chunk_db, use_cache=True)
```

**优化特性**:
- 自动批处理（由底层 SentenceTransformer 管理）
- 缓存命中跳过编码，只编码新/变更的分块
- 进度条（分块数 > 100 时自动显示）

### 4. 结果导出

```python
# 保存所有稠密向量为 .npy 文件
output_path = encoder_manager.save_embeddings_to_npy(encoded_vectors)
# 输出: outputs/embeddings/embeddings_20260421_110956.npy
# 附带: outputs/embeddings/embeddings_20260421_110956.meta.json
```

**元数据文件结构** (`embeddings_xxx.meta.json`):
```json
{
  "shape": [450, 512],
  "dtype": "float32",
  "count": 450,
  "encoder_type": "dense",
  "timestamp": "2026-04-21T01:10:56.878852Z"
}
```

---

## 配置参数

### 全局配置
```yaml
encoder:
  # 编码器类型: dense(稠密向量) / sparse(稀疏向量) / hybrid(混合)
  type: "dense"

  # 缓存配置
  cache_dir: "./cache/encodings"
  incremental: true           # 启用增量编码
```

### 稠密编码器配置
```yaml
encoder:
  dense:
    model_name: "BAAI/bge-small-zh-v1.5"
    model_path: null          # 本地模型路径（不为 null 时优先使用）
    device: "auto"            # auto/cpu/cuda
    normalize: true           # 向量归一化
    batch_size: 32            # 批处理大小
    max_seq_length: 512       # 最大序列长度
    instruction: "为这个句子生成表示以用于检索相关文章："
    use_instruction: true     # 是否添加指令前缀
```

### 稀疏编码器配置
```yaml
encoder:
  sparse:
    bm25:
      k1: 1.5                # BM25 词频饱和参数
      b: 0.75                # BM25 长度归一化参数
      max_features: 50000    # 最大词汇表大小
      min_df: 1              # 最小文档频率
      max_df: 0.95           # 最大文档频率

    tfidf:
      max_features: 50000
      min_df: 1
      max_df: 0.95
      ngram_range: [1, 2]    # n-gram范围
```

### 混合编码器配置
```yaml
encoder:
  hybrid:
    dense_weight: 0.7        # 稠密向量权重 (自动归一化)
    sparse_weight: 0.3       # 稀疏向量权重
    sparse_type: "bm25"      # bm25 / tfidf
    dense_config: {}         # 覆盖稠密编码器配置
    sparse_config: {}        # 覆盖稀疏编码器配置
```

---

## 使用示例

### 1. 基本使用

```python
from src.encoders import EncoderManager

# 初始化编码管理器
config = {
    "encoder": {
        "type": "dense",
        "cache_dir": "./cache/encodings"
    }
}
encoder_manager = EncoderManager(config)

# 批量编码文本（通过 .encoder 属性访问实际编码器）
texts = ["文档内容1", "文档内容2", "文档内容3"]
encoded_vectors = encoder_manager.encoder.encode_batch(texts)

# 处理编码结果
for vector in encoded_vectors:
    print(f"分块ID: {vector.chunk_id}")
    print(f"向量维度: {len(vector.dense_vector)}")
    print(f"元数据: {vector.metadata}")
```

### 2. 增量编码示例

```python
from src.encoders import EncoderManager
from src.chunkers.chunk_manager import ChunkRecord

# 初始化编码管理器（启用增量）
config = {
    "encoder": {
        "type": "dense",
        "incremental": True,
        "cache_dir": "./cache/encodings"
    }
}
manager = EncoderManager(config)

# 编码分块列表（自动使用缓存）
chunks = [
    ChunkRecord(chunk_id="doc1#hash1", content="文档内容1"),
    ChunkRecord(chunk_id="doc2#hash2", content="文档内容2"),
]
encoded_vectors = manager.encode_chunks(chunks, use_cache=True)

# 只有新内容或变更的内容会被编码
print(f"总共编码: {len(encoded_vectors)} 个向量")
```

### 3. 从分块数据库编码

```python
from src.encoders import EncoderManager
from src.chunkers.chunk_manager import ChunkDatabase

# 初始化
db = ChunkDatabase("./cache/chunks_db.json")
manager = EncoderManager(config)

# 直接从数据库编码所有分块
# 自动拟合稀疏编码器（如果类型为 sparse 或 hybrid）
encoded_vectors = manager.encode_from_database(db, use_cache=True)

# 导出为 .npy 文件
output_path = manager.save_embeddings_to_npy(encoded_vectors)
print(f"向量已保存到: {output_path}")
```

### 4. 混合编码示例

```python
from src.encoders import EncoderManager

config = {
    "encoder": {
        "type": "hybrid",
        "hybrid": {
            "dense_weight": 0.7,
            "sparse_weight": 0.3,
            "sparse_type": "bm25"
        }
    }
}
manager = EncoderManager(config)

# 拟合稀疏编码器
manager.fit(["训练文档1", "训练文档2"])

# 编码（通过 .encoder 属性访问 HybridEncoder 实例）
vectors = manager.encoder.encode_batch(["要编码的文档1", "要编码的文档2"])

for v in vectors:
    print(f"稠密向量维度: {len(v.dense_vector)}")
    print(f"稀疏向量非零项: {len(v.sparse_vector)}")
    print(f"是否混合: {v.is_hybrid}")

# 计算两个向量的混合相似度
similarity = manager.encoder.compute_similarity(vectors[0], vectors[1])
print(f"综合相似度: {similarity:.4f}")
```

### 5. 自定义编码器

```python
from src.encoders.base import BaseEncoder, EncodedVector
import numpy as np
from typing import List, Optional

class CustomEncoder(BaseEncoder):
    """自定义编码器示例"""

    def __init__(self, config=None):
        super().__init__(config)
        self._dim = 128

    def initialize(self):
        self.is_initialized = True

    def encode(self, text: str, chunk_id: Optional[str] = None) -> EncodedVector:
        vector = np.random.randn(self._dim).astype(np.float32)

        return EncodedVector(
            chunk_id=chunk_id or '',
            content=text,
            dense_vector=vector,
            metadata={"encoder": "custom"}
        )

    def encode_batch(
        self, texts: List[str], chunk_ids: Optional[List[str]] = None
    ) -> List[EncodedVector]:
        if chunk_ids is None:
            chunk_ids = [None] * len(texts)
        return [self.encode(t, cid) for t, cid in zip(texts, chunk_ids)]

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def vector_type(self) -> str:
        return 'dense'
```

---

## 扩展开发

### 1. 添加新的编码器类型

**步骤 1**: 创建新的编码器类，继承 `BaseEncoder`

```python
from src.encoders.base import BaseEncoder, EncodedVector

class NewEncoder(BaseEncoder):
    """新的编码器实现"""

    def __init__(self, config=None):
        super().__init__(config)

    def initialize(self):
        self.is_initialized = True

    def encode(self, text: str, chunk_id: Optional[str] = None) -> EncodedVector:
        # 编码逻辑
        pass

    def encode_batch(self, texts, chunk_ids=None):
        # 批量编码逻辑
        pass

    @property
    def dimension(self) -> int:
        return 256

    @property
    def vector_type(self) -> str:
        return 'dense'
```

**步骤 2**: 在 `EncoderManager` 中注册

```python
# encoder_manager.py 的 _create_encoder 方法
def _create_encoder(self) -> BaseEncoder:
    if self.encoder_type == 'dense':
        return DenseEncoder(self.config)
    elif self.encoder_type == 'sparse':
        return SparseEncoder(self.config)
    elif self.encoder_type == 'hybrid':
        return HybridEncoder(self.config)
    elif self.encoder_type == 'new':    # 新增
        return NewEncoder(self.config)
    else:
        raise ValueError(f"未知的编码器类型: {self.encoder_type}")
```

**步骤 3**: 更新配置文件

```yaml
encoder:
  type: "new"
  new:
    param1: value1
    param2: value2
```

**步骤 4**: 导出到 `__init__.py`

```python
from .new_encoder import NewEncoder

__all__ = [
    ...
    'NewEncoder',
]
```

### 2. 集成外部模型

**HuggingFace 模型**:

```python
from transformers import AutoTokenizer, AutoModel
import torch

class HuggingFaceEncoder(BaseEncoder):
    def __init__(self, config=None):
        super().__init__(config)
        self.model_name = config.get('model_name', 'bert-base-chinese')

    def initialize(self):
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModel.from_pretrained(self.model_name)
        self._dim = self.model.config.hidden_size
        self.is_initialized = True

    def encode(self, text: str, chunk_id: Optional[str] = None) -> EncodedVector:
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
        with torch.no_grad():
            outputs = self.model(**inputs)
        vector = outputs.last_hidden_state[:, 0, :].numpy().flatten()
        return EncodedVector(chunk_id=chunk_id or '', content=text, dense_vector=vector)
```

**OpenAI Embeddings**:

```python
from openai import OpenAI

class OpenAIEncoder(BaseEncoder):
    def __init__(self, config=None):
        super().__init__(config)
        self.api_key = config.get('api_key')
        self.model = config.get('model', 'text-embedding-3-small')
        self.client = OpenAI(api_key=self.api_key)

    def encode(self, text, chunk_id=None):
        resp = self.client.embeddings.create(model=self.model, input=text)
        vector = np.array(resp.data[0].embedding, dtype=np.float32)
        return EncodedVector(chunk_id=chunk_id or '', content=text, dense_vector=vector)
```

### 3. 优化编码性能

**内存优化**:
- 使用缓存避免重复编码
- 增量更新只处理变更的分块
- `.npy` 文件直接内存映射加载

**速度优化**:
- 增大 `batch_size` 利用 GPU 并行
- 使用更轻量的模型（bge-small 替代 bge-large）
- 启用向量归一化减少后续计算开销

**存储优化**:
- 编码缓存持久化到磁盘
- 支持从缓存恢复，无需重新编码

---

## 常见问题

### Q1: 如何选择编码器类型？

**推荐场景**:
- **稠密编码器** (`dense`): 通用场景，语义搜索，高质量检索
- **稀疏编码器** (`sparse`): 关键词搜索，快速检索，内存受限场景
- **混合编码器** (`hybrid`): 需要平衡语义和关键词搜索的场景

### Q2: 增量编码如何工作？

增量编码通过以下步骤工作：
1. 计算文本内容的 MD5 哈希值
2. 在 `EncodingDatabase` 中查询该 `chunk_id` 的记录
3. 如果找到匹配记录且内容哈希相同，从 `.npy` / `.json` 文件加载缓存的向量
4. 如果没有找到或内容哈希不同，执行编码并存储新记录
5. 记录包含内容哈希、编码时间、向量文件路径等

### Q3: 如何清理编码缓存？

```bash
# 删除整个缓存目录
rm -rf ./cache/encodings
```

```python
# 或在代码中删除
import shutil
shutil.rmtree("./cache/encodings", ignore_errors=True)
```

### Q4: 编码器性能如何优化？

1. **批处理大小**: 根据 GPU 内存调整 `batch_size`（默认 32）
2. **模型选择**: `bge-small-zh-v1.5`（轻量） vs `bge-base-zh-v1.5`（平衡） vs `bge-large-zh-v1.5`（高质量）
3. **缓存策略**: 启用 `incremental: true` 避免重复编码
4. **本地模型**: 设置 `model_path` 使用本地模型，避免网络下载

### Q5: 如何监控编码过程？

- 日志级别设置为 `INFO` 可查看编码进度
- 批量编码超过 100 条时自动显示进度条
- 通过 `encoder_manager.get_stats()` 获取编码统计信息
- 编码完成后可通过 `.meta.json` 查看结果汇总
