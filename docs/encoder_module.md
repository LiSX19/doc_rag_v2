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
5. **向后兼容**: 兼容原先 Embedder 模块的接口

### 编码流程

```
文本分块 (TextChunk)
    │
    ├─> 1. 编码器选择
    │      ├─ 根据配置选择编码器类型 (dense/sparse/hybrid)
    │      └─ 实例化对应的编码器
    │
    ├─> 2. 编码计算
    │      ├─ 稠密编码: 使用 SentenceTransformer 模型
    │      ├─ 稀疏编码: 使用 BM25/TF-IDF 算法
    │      └─ 混合编码: 结合两种编码结果
    │
    ├─> 3. 结果封装
    │      ├─ 封装为 EncodedVector 对象
    │      ├─ 包含原始文本、向量和元数据
    │      └─ 支持序列化存储
    │
    └─> 4. 缓存管理
           ├─ 计算内容哈希
           ├─ 检查缓存命中
           └─ 存储新的编码结果
```

---

## 文件结构

```
src/encoders/
├── __init__.py              # 模块导出
├── base.py                  # 基类和接口定义
├── dense_encoder.py         # 稠密向量编码器
├── sparse_encoder.py        # 稀疏向量编码器 (BM25/TF-IDF)
├── hybrid_encoder.py        # 混合编码器
└── encoder_manager.py       # 编码管理器
```

---

## 核心类与接口

### 1. BaseEncoder (抽象基类)

所有编码器的基类，定义统一的编码接口：

```python
class BaseEncoder(ABC):
    """编码器基类"""
    
    @abstractmethod
    def initialize(self):
        """初始化编码器（加载模型等）"""
        pass
    
    @abstractmethod
    def encode(self, text: str, chunk_id: str = "") -> EncodedVector:
        """编码单个文本"""
        pass
    
    @abstractmethod
    def encode_batch(self, texts: List[str], chunk_ids: List[str] = None) -> List[EncodedVector]:
        """批量编码文本"""
        pass
    
    @property
    @abstractmethod
    def dimension(self) -> int:
        """返回向量维度"""
        pass
```

### 2. EncodedVector (数据类)

统一表示编码结果的数据结构：

```python
@dataclass
class EncodedVector:
    """编码向量数据类"""
    
    chunk_id: str                    # 分块唯一ID
    content: str                     # 原始文本内容
    dense_vector: Optional[np.ndarray] = None      # 稠密向量
    sparse_vector: Optional[Dict[int, float]] = None  # 稀疏向量 (索引:权重)
    metadata: Optional[Dict[str, Any]] = None      # 元数据
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（支持JSON序列化）"""
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EncodedVector':
        """从字典创建实例"""
```

### 3. EncoderManager (编码管理器)

管理编码器的创建、配置和批量操作：

```python
class EncoderManager:
    """编码管理器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化编码管理器
        
        Args:
            config: 配置字典，包含:
                - encoder.type: 编码器类型 ('dense', 'sparse', 'hybrid')
                - encoder.cache_dir: 缓存目录
                - encoder.incremental: 是否启用增量编码
        """
    
    def encode_batch(self, texts: List[str], chunk_ids: List[str] = None,
                    use_cache: bool = True) -> List[EncodedVector]:
        """批量编码文本（支持缓存）"""
    
    def encode_chunks(self, chunks: List[Any], use_cache: bool = True) -> List[EncodedVector]:
        """编码文本分块（兼容TextChunk和字符串）"""
    
    def fit(self, texts: List[str]):
        """拟合编码器（用于稀疏编码器）"""
```

---

## 编码器类型

### 1. DenseEncoder (稠密向量编码器)

使用预训练模型生成稠密向量：

**支持模型**:
- BAAI/bge-small-zh-v1.5 (默认)
- BAAI/bge-large-zh-v1.5
- 其他 SentenceTransformer 兼容模型

**主要特性**:
- 支持本地模型路径
- 自动设备选择 (CPU/GPU)
- 向量归一化
- 批处理优化
- 指令前缀增强（BGE模型）

**配置示例**:
```yaml
encoder:
  type: "dense"
  dense:
    model_name: "BAAI/bge-small-zh-v1.5"
    model_path: null  # 本地模型路径（优先使用）
    device: "auto"    # auto/cpu/cuda
    normalize: true
    batch_size: 32
    max_seq_length: 512
    instruction: "为这个句子生成表示以用于检索相关文章："
    use_instruction: true
```

### 2. SparseEncoder (稀疏向量编码器)

支持两种稀疏编码算法：

#### 2.1 BM25 编码器
- 基于 Okapi BM25 算法
- 支持中文分词
- 可配置参数 (k1, b)

#### 2.2 TF-IDF 编码器
- 基于 TF-IDF 算法
- 支持 n-gram (1-2 gram)
- 特征选择和过滤

**配置示例**:
```yaml
encoder:
  type: "sparse"
  sparse:
    # BM25 配置
    bm25:
      k1: 1.5
      b: 0.75
      max_features: 50000
      min_df: 1
      max_df: 0.95
    
    # TF-IDF 配置
    tfidf:
      max_features: 50000
      min_df: 1
      max_df: 0.95
      ngram_range: [1, 2]
```

### 3. HybridEncoder (混合编码器)

结合稠密和稀疏向量的优势：

**主要特性**:
- 可配置权重比例 (dense_weight, sparse_weight)
- 支持不同的稀疏算法 (BM25/TF-IDF)
- 独立的子编码器配置

**配置示例**:
```yaml
encoder:
  type: "hybrid"
  hybrid:
    dense_weight: 0.7
    sparse_weight: 0.3
    sparse_type: "bm25"  # bm25 / tfidf
    dense_config: {}      # 继承全局dense配置
    sparse_config: {}     # 继承全局sparse配置
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
1. 计算文本内容哈希值
2. 查询缓存数据库
3. 如果缓存命中，加载缓存的向量
4. 如果缓存未命中，执行编码并存储结果

### 2. 编码缓存

使用 JSON 数据库存储编码结果：

```python
class EncodingDatabase:
    """编码结果数据库"""
    
    def get_record(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """获取编码记录"""
    
    def save_record(self, chunk_id: str, content_hash: str, 
                   vector_data: Dict[str, Any]) -> bool:
        """保存编码记录"""
    
    def cleanup_old_records(self, max_age_days: int = 30):
        """清理旧记录"""
```

**缓存数据结构**:
```json
{
  "chunk_id": "文件路径#哈希值",
  "content_hash": "md5哈希值",
  "encoded_at": "时间戳",
  "vector_type": "dense/sparse/hybrid",
  "vector_data": {
    "dense_vector": [...],
    "sparse_vector": {...}
  },
  "metadata": {...}
}
```

### 3. 批量编码优化

针对大规模文本分块的优化策略：

```python
# 批量编码（自动分批次）
encoded_vectors = encoder_manager.encode_batch(
    texts=texts,
    chunk_ids=chunk_ids,
    use_cache=True,
    batch_size=32
)
```

**优化特性**:
- 自动批处理（根据内存限制）
- 并行编码支持
- 进度监控
- 错误重试机制

---

## 配置参数

### 全局配置
```yaml
encoder:
  # 编码器类型: dense(稠密向量) / sparse(稀疏向量) / hybrid(混合)
  type: "dense"
  
  # 缓存配置
  cache_dir: "./cache/encodings"
  incremental: true
```

### 稠密编码器配置
```yaml
encoder:
  type: "dense"
  dense:
    model_name: "BAAI/bge-small-zh-v1.5"
    model_path: null        # 本地模型路径
    device: "auto"          # auto/cpu/cuda
    normalize: true         # 向量归一化
    batch_size: 32          # 批处理大小
    max_seq_length: 512     # 最大序列长度
    instruction: "为这个句子生成表示以用于检索相关文章："  # BGE指令
    use_instruction: true   # 是否使用指令
```

### 稀疏编码器配置
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

### 混合编码器配置
```yaml
encoder:
  type: "hybrid"
  hybrid:
    dense_weight: 0.7      # 稠密向量权重
    sparse_weight: 0.3     # 稀疏向量权重
    sparse_type: "bm25"    # bm25 / tfidf
    dense_config: {}       # 稠密编码器配置（继承全局）
    sparse_config: {}      # 稀疏编码器配置（继承全局）
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

# 批量编码文本
texts = ["文档内容1", "文档内容2", "文档内容3"]
encoded_vectors = encoder_manager.encode_batch(texts)

# 处理编码结果
for vector in encoded_vectors:
    print(f"分块ID: {vector.chunk_id}")
    print(f"向量维度: {len(vector.dense_vector)}")
    print(f"元数据: {vector.metadata}")
```

### 2. 增量编码示例
```python
from src.encoders import EncoderManager
from src.chunkers import TextChunk

# 初始化编码管理器（启用增量）
config = {
    "encoder": {
        "type": "dense",
        "incremental": True,
        "cache_dir": "./cache/encodings"
    }
}
encoder_manager = EncoderManager(config)

# 编码文本分块（自动使用缓存）
chunks = [
    TextChunk(content="文档内容1", chunk_id="doc1#hash1"),
    TextChunk(content="文档内容2", chunk_id="doc2#hash2"),
    TextChunk(content="更新的文档内容1", chunk_id="doc1#hash3"),  # 内容已更新
]

encoded_vectors = encoder_manager.encode_chunks(chunks, use_cache=True)

# 只有更新的内容会被重新编码
print(f"总共编码: {len(encoded_vectors)} 个向量")
```

### 3. 混合编码示例
```python
from src.encoders import EncoderManager

# 配置混合编码器
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

# 初始化编码管理器
encoder_manager = EncoderManager(config)

# 拟合稀疏编码器（需要训练数据）
training_texts = ["训练文档1", "训练文档2", "训练文档3"]
encoder_manager.fit(training_texts)

# 编码新文本
texts = ["要编码的文档1", "要编码的文档2"]
encoded_vectors = encoder_manager.encode_batch(texts)

# 处理混合编码结果
for vector in encoded_vectors:
    print(f"稠密向量维度: {len(vector.dense_vector)}")
    print(f"稀疏向量非零元素: {len(vector.sparse_vector)}")
```

### 4. 自定义编码器
```python
from src.encoders.base import BaseEncoder, EncodedVector
import numpy as np

class CustomEncoder(BaseEncoder):
    """自定义编码器示例"""
    
    def __init__(self, config=None):
        self.config = config or {}
        self.dimension = 128  # 自定义维度
        
    def initialize(self):
        """初始化自定义模型"""
        # 加载自定义模型
        pass
    
    def encode(self, text: str, chunk_id: str = "") -> EncodedVector:
        """编码单个文本"""
        # 生成自定义向量
        custom_vector = np.random.randn(self.dimension)
        
        return EncodedVector(
            chunk_id=chunk_id,
            content=text,
            dense_vector=custom_vector,
            metadata={"encoder": "custom"}
        )
    
    def encode_batch(self, texts: List[str], chunk_ids: List[str] = None) -> List[EncodedVector]:
        """批量编码"""
        if chunk_ids is None:
            chunk_ids = [str(i) for i in range(len(texts))]
        
        results = []
        for text, chunk_id in zip(texts, chunk_ids):
            results.append(self.encode(text, chunk_id))
        
        return results
```

---

## 扩展开发

### 1. 添加新的编码器类型

**步骤 1**: 创建新的编码器类
```python
from src.encoders.base import BaseEncoder, EncodedVector

class NewEncoder(BaseEncoder):
    """新的编码器实现"""
    
    def __init__(self, config=None):
        super().__init__(config)
        # 初始化配置
    
    def initialize(self):
        # 初始化逻辑
        pass
    
    def encode(self, text: str, chunk_id: str = "") -> EncodedVector:
        # 编码逻辑
        pass
    
    def encode_batch(self, texts: List[str], chunk_ids: List[str] = None) -> List[EncodedVector]:
        # 批量编码逻辑
        pass
    
    @property
    def dimension(self) -> int:
        return 256  # 返回向量维度
```

**步骤 2**: 在 EncoderManager 中注册
```python
# 修改 encoder_manager.py 中的 _create_encoder 方法
def _create_encoder(self) -> BaseEncoder:
    if self.encoder_type == 'dense':
        return DenseEncoder(self.config)
    elif self.encoder_type == 'sparse':
        return SparseEncoder(self.config)
    elif self.encoder_type == 'hybrid':
        return HybridEncoder(self.config)
    elif self.encoder_type == 'new':  # 新增类型
        return NewEncoder(self.config)
    else:
        raise ValueError(f"未知的编码器类型: {self.encoder_type}")
```

**步骤 3**: 更新配置文件支持
```yaml
encoder:
  type: "new"  # 新的编码器类型
  new:
    # 新编码器的配置参数
    param1: value1
    param2: value2
```

### 2. 优化编码性能

**内存优化**:
- 实现流式编码接口
- 支持大型批处理的内存分页
- 自动清理临时缓存

**速度优化**:
- 实现异步编码接口
- 支持 GPU 并行计算
- 优化批处理调度算法

**存储优化**:
- 实现向量压缩存储
- 支持增量更新索引
- 优化缓存淘汰策略

### 3. 集成外部模型

**支持 HuggingFace 模型**:
```python
from transformers import AutoTokenizer, AutoModel
import torch

class HuggingFaceEncoder(BaseEncoder):
    """HuggingFace 模型编码器"""
    
    def __init__(self, config=None):
        super().__init__(config)
        self.model_name = config.get('model_name', 'bert-base-chinese')
        self.tokenizer = None
        self.model = None
    
    def initialize(self):
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModel.from_pretrained(self.model_name)
    
    def encode(self, text: str, chunk_id: str = "") -> EncodedVector:
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, padding=True)
        with torch.no_grad():
            outputs = self.model(**inputs)
        
        # 取 [CLS] 向量作为文本表示
        embeddings = outputs.last_hidden_state[:, 0, :].numpy()
        
        return EncodedVector(
            chunk_id=chunk_id,
            content=text,
            dense_vector=embeddings.flatten(),
            metadata={"model": self.model_name}
        )
```

**支持 OpenAI Embeddings**:
```python
import openai

class OpenAIEncoder(BaseEncoder):
    """OpenAI Embeddings 编码器"""
    
    def __init__(self, config=None):
        super().__init__(config)
        self.api_key = config.get('api_key')
        self.model = config.get('model', 'text-embedding-ada-002')
        openai.api_key = self.api_key
    
    def encode(self, text: str, chunk_id: str = "") -> EncodedVector:
        response = openai.Embedding.create(
            model=self.model,
            input=text
        )
        
        embedding = response['data'][0]['embedding']
        
        return EncodedVector(
            chunk_id=chunk_id,
            content=text,
            dense_vector=np.array(embedding),
            metadata={"model": self.model, "api": "openai"}
        )
```

---

## 常见问题

### Q1: 如何选择编码器类型？

**推荐场景**:
- **稠密编码器**: 通用场景，语义搜索，高质量检索
- **稀疏编码器**: 关键词搜索，快速检索，内存受限场景
- **混合编码器**: 需要平衡语义和关键词搜索的场景

### Q2: 增量编码如何工作？

增量编码通过以下步骤工作：
1. 计算文本内容的 MD5 哈希值
2. 在缓存数据库中查询该哈希值
3. 如果找到匹配记录，加载缓存的向量
4. 如果没有找到，执行编码并存储新记录
5. 记录包含内容哈希、编码时间、向量数据等

### Q3: 如何清理编码缓存？

```python
# 手动清理旧记录
encoder_manager.db.cleanup_old_records(max_age_days=30)

# 删除整个缓存目录
import shutil
shutil.rmtree("./cache/encodings", ignore_errors=True)
```

### Q4: 编码器性能如何优化？

**性能优化建议**:
1. **批处理大小**: 根据 GPU 内存调整 `batch_size`
2. **模型选择**: 轻量级模型 vs 高质量模型
3. **缓存策略**: 合理设置缓存过期时间
4. **增量更新**: 启用增量编码避免重复计算

### Q5: 如何监控编码过程？

```python
import logging

# 启用详细日志
logging.basicConfig(level=logging.INFO)

# 在编码过程中记录进度
for i, vector in enumerate(encoded_vectors):
    if i % 100 == 0:
        print(f"已编码 {i}/{len(encoded_vectors)} 个向量")
```

---

## 版本历史

### v1.0.0 (初始版本)
- 统一编码器接口
- 支持稠密、稀疏、混合编码
- 实现增量编码和缓存
- 兼容原先 Embedder 模块

### v1.1.0 (计划功能)
- 支持更多预训练模型
- 实现异步编码接口
- 添加向量压缩存储
- 优化批处理性能

---

## 相关链接

- [SentenceTransformers 文档](https://www.sbert.net/)
- [BM25 算法详解](https://en.wikipedia.org/wiki/Okapi_BM25)
- [TF-IDF 算法详解](https://en.wikipedia.org/wiki/Tf%E2%80%93idf)
- [Chroma 向量数据库](https://docs.trychroma.com/)
