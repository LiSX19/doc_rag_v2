# Deduper 模块详细说明文档

## 目录
1. [模块概述](#模块概述)
2. [文件结构](#文件结构)
3. [核心类与接口](#核心类与接口)
4. [去重算法](#去重算法)
5. [去重策略](#去重策略)
6. [配置参数](#配置参数)
7. [使用示例](#使用示例)
8. [扩展开发](#扩展开发)

---

## 模块概述

Deduper 模块是文档 RAG 系统的文本去重组件，负责检测和移除重复的文本分块。该模块提供多级去重功能，从精确匹配到近似相似度检测，确保向量数据库中存储的文本分块具有高质量和多样性。

### 主要功能

1. **多级去重算法**:
   - **哈希去重**: 精确内容匹配，移除完全相同的文本（基于 MD5 哈希）
   - **SimHash去重**: 近似内容检测，移除高度相似的文本（基于字符 trigram 特征）
   - **Embedding去重**: 语义相似度检测（**预留接口，暂未实现**）

2. **灵活的去重策略**:
   - **测试模式**: 快速去重，使用哈希和 SimHash 算法
   - **生产模式**: 高质量去重，使用所有三级算法（Embedding 为 TODO 状态）

3. **增量去重支持**:
   - 哈希表 JSON 文件持久化，避免重复检测
   - 启动时自动加载已有哈希表，处理完成后自动保存
   - 支持断点续传（哈希表持久化到 `./cache/dedup_hash_table.json`）

4. **去重报告输出**:
   - 通过 `OutputManager` 自动保存去重报告到 `outputs/dedup/` 目录
   - 包含去重策略、数量统计、重复组等信息

### 去重流程

```
原始文本分块
    │
    ├─> 1. 哈希去重 (可选)
    │      ├─ 计算内容哈希值 (MD5，通过 FileUtils.calculate_content_hash)
    │      ├─ 检查持久化哈希表 (self.seen_hashes)
    │      ├─ 移除完全相同的文本
    │      └─ 记录新哈希到持久化表
    │
    ├─> 2. SimHash去重 (可选)
    │      ├─ 提取字符 trigram 特征（滑动窗口 3 字符）
    │      ├─ 计算 SimHash 指纹（64位）
    │      ├─ 比较汉明距离
    │      ├─ 移除高度相似的文本
    │      └─ 阈值: 3 (可配置)
    │
    ├─> 3. Embedding去重 (可选) ⚠️ TODO
    │      ├─ 预留接口，尚未实现
    │      └─ 当前直接返回原列表（无去重效果）
    │
    └─> 4. 结果处理
           ├─ 构建重复组信息
           ├─ 通过 OutputManager 保存去重报告 (dedup_report.json)
           ├─ 保存哈希表到持久化文件
           ├─ 更新统计信息
           └─ 返回唯一文本分块
```

---

## 文件结构

```
src/dedupers/
├── __init__.py              # 模块导出 (BaseDeduper, Deduper)
├── base.py                  # 基类 (BaseDeduper) 和数据类 (DedupResult)
└── deduper.py               # 多级去重器实现 (Deduper)
```

---

## 核心类与接口

### 1. DedupResult (去重结果数据类)

封装去重操作的结果：

```python
class DedupResult:
    """去重结果类"""
    
    def __init__(
        self,
        chunks: List[TextChunk],          # 保留的文本块
        removed_chunks: List[TextChunk],   # 移除的重复文本块
        duplicate_groups: List[List[int]], # 重复组（每组包含重复块的索引）
        stats: Optional[Dict[str, Any]] = None  # 统计信息
    ):
        self.chunks = chunks
        self.removed_chunks = removed_chunks
        self.duplicate_groups = duplicate_groups
        self.stats = stats or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（支持JSON序列化）"""
        return {
            'kept_count': len(self.chunks),
            'removed_count': len(self.removed_chunks),
            'duplicate_groups': self.duplicate_groups,
            'stats': self.stats,
        }
```

**属性说明**:
- `chunks` - 保留的文本块列表
- `removed_chunks` - 被移除的重复文本块列表
- `duplicate_groups` - 重复组信息（每组包含相似块的索引）
- `stats` - 统计信息字典
- `kept_count` / `removed_count` / `duplicate_group_count` — 通过 `to_dict()` 或直接访问 `len()` 获取

### 2. BaseDeduper (抽象基类)

所有去重器的基类，定义统一的去重接口：

```python
class BaseDeduper(ABC):
    """去重器基类"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
    
    @abstractmethod
    def deduplicate(self, chunks: List[TextChunk]) -> DedupResult:
        """去重文本块"""
        pass
    
    def calculate_stats(self, original_count: int, kept_count: int) -> Dict[str, Any]:
        """计算统计信息"""
        removed_count = original_count - kept_count
        dedup_rate = removed_count / original_count if original_count > 0 else 0
        return {
            'original_count': original_count,
            'kept_count': kept_count,
            'removed_count': removed_count,
            'dedup_rate': round(dedup_rate, 4),
        }
```

### 3. Deduper (多级去重器)

多级去重算法的主要实现类：

```python
class Deduper(BaseDeduper):
    """多级去重器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化去重器
        
        Args:
            config: 配置字典，读取路径 deduper.X：
                - deduper.strategy: 去重策略 (test/production)
                - deduper.test.use_hash: 测试模式使用哈希去重
                - deduper.test.use_simhash: 测试模式使用SimHash去重
                - deduper.test.simhash_threshold: SimHash阈值
                - deduper.production.use_hash
                - deduper.production.use_simhash
                - deduper.production.use_embedding
                - deduper.production.simhash_threshold
                - deduper.production.embedding_threshold
                - deduper.hash_table_path: 哈希表持久化路径
        """
    
    def deduplicate(self, chunks: List[TextChunk],
                   filename: Optional[str] = None) -> DedupResult:
        """执行多级去重"""
    
    def _hash_deduplicate(self, chunks: List[TextChunk]) -> Tuple[List[TextChunk], List[TextChunk]]:
        """哈希去重（使用持久化哈希表）"""
    
    def _simhash_deduplicate(self, chunks: List[TextChunk]) -> Tuple[List[TextChunk], List[TextChunk]]:
        """SimHash去重（基于字符 trigram 特征）"""
    
    def _embedding_deduplicate(self, chunks: List[TextChunk]) -> Tuple[List[TextChunk], List[TextChunk]]:
        """Embedding去重（预留接口，暂未实现）"""
    
    def _build_duplicate_groups(self, original_count, kept_chunks, removed_chunks) -> List[List[int]]:
        """构建重复组信息"""
    
    def _is_similar(self, chunk1: TextChunk, chunk2: TextChunk) -> bool:
        """检查两个块是否相似（基于前100字符）"""
    
    def _load_hash_table(self) -> None:
        """加载持久化哈希表（从JSON文件）"""
    
    def _save_hash_table(self) -> None:
        """保存哈希表到JSON文件"""
```

---

## 去重算法

### 1. 哈希去重 (Hash Deduplication)

**算法原理**: 使用 MD5 哈希算法计算文本内容的唯一标识，通过比较哈希值检测完全相同的文本。

**实际实现**:
- 优先使用 `chunk.content_hash` 属性（如果存在）
- 否则通过 `FileUtils.calculate_content_hash(chunk.content, 'md5')` 计算
- 使用持久化哈希表 `self.seen_hashes`（从JSON文件加载，处理完后保存）

**适用场景**:
- 完全相同的文本内容
- 快速去重，计算成本低
- 精确匹配，无误判

**实现细节**:
```python
def _hash_deduplicate(self, chunks: List[TextChunk]) -> Tuple[List[TextChunk], List[TextChunk]]:
    """哈希去重（使用持久化哈希表）"""
    kept = []
    removed = []
    
    for chunk in chunks:
        # 使用已有的content_hash属性，如果没有则计算
        if hasattr(chunk, 'content_hash') and chunk.content_hash:
            content_hash = chunk.content_hash
        else:
            content_hash = FileUtils.calculate_content_hash(chunk.content, 'md5')
        
        if content_hash in self.seen_hashes:
            removed.append(chunk)
        else:
            self.seen_hashes.add(content_hash)
            kept.append(chunk)
    
    return kept, removed
```

**性能特点**:
- 时间复杂度: O(n)
- 空间复杂度: O(n)（哈希表存储）
- 准确率: 100%（完全匹配）

### 2. SimHash 去重 (SimHash Deduplication)

**算法原理**: 使用字符 trigram（连续3字符）作为特征，通过 SimHash 算法生成64位指纹，比较汉明距离检测相似文本。

**适用场景**:
- 高度相似的文本（修改少量字符）
- 近似去重，容忍微小差异
- 计算成本中等

**实现细节**:
```python
def _simhash_deduplicate(self, chunks: List[TextChunk]) -> Tuple[List[TextChunk], List[TextChunk]]:
    """SimHash去重"""
    # 提取字符 trigram 作为特征
    features = [chunk.content[i:i+3] for i in range(len(chunk.content)-2)]
    simhash = Simhash(features)
    
    # 比较汉明距离
    distance = simhashes[i].distance(simhashes[j])
    if distance <= self.simhash_threshold:
        is_duplicate = True
```

**特征提取说明**:
- 使用滑动窗口提取连续3字符片段作为 SimHash 特征
- 例如文本 "hello" 的特征为 `["hel", "ell", "llo"]`
- 相比直接对整个字符串计算哈希，trigram 特征能更好地捕获局部文本相似性

**参数说明**:
- `simhash_threshold`: 汉明距离阈值
  - 默认值: 3
  - 范围: 0-64（64位SimHash）
  - 值越小越严格，值越大越宽松

**性能特点**:
- 时间复杂度: O(n²)（最坏情况，与已保留块逐个比较）
- 空间复杂度: O(n)（指纹存储）
- 内置进度显示：每处理 500 个块输出一次计算进度，每 200 次比较输出一次去重进度

### 3. Embedding 去重 (Embedding Deduplication) ⚠️ TODO

**当前状态**: 预留接口，**尚未实现**。

```python
def _embedding_deduplicate(self, chunks: List[TextChunk]) -> Tuple[List[TextChunk], List[TextChunk]]:
    """Embedding去重（需要外部提供embeddings）"""
    # TODO: 实现基于Embedding的去重
    # 这需要先计算所有块的embedding，然后计算相似度
    # 暂时返回原样
    return chunks, []
```

**计划实现方式**:
- 批量计算文本嵌入向量（使用 Encoder 模块）
- 计算余弦相似度矩阵
- 移除语义相似的文本（超过阈值）

---

## 去重策略

### 1. 测试模式 (Test Strategy)

**设计目标**: 快速去重，适用于开发和测试环境

**默认配置**:
- 哈希去重: ✅ 启用 (use_hash=True)
- SimHash 去重: ✅ 启用 (use_simhash=True)
- Embedding 去重: ❌ 禁用 (use_embedding=False)
- SimHash 阈值: 3

**配置示例**:
```yaml
deduper:
  strategy: "test"
  test:
    use_hash: true
    use_simhash: true
    simhash_threshold: 3
```

**适用场景**:
- 开发环境测试
- 快速原型验证
- 大量文档的初步去重

### 2. 生产模式 (Production Strategy)

**设计目标**: 高质量去重，适用于生产环境

**默认配置**:
- 哈希去重: ✅ 启用 (use_hash=True)
- SimHash 去重: ✅ 启用 (use_simhash=True)
- Embedding 去重: ✅ 启用（**实际为 TODO 暂未生效**）
- SimHash 阈值: 3
- Embedding 阈值: 0.95

**配置示例**:
```yaml
deduper:
  strategy: "production"
  production:
    use_hash: true
    use_simhash: true
    use_embedding: true
    simhash_threshold: 3
    embedding_threshold: 0.95
```

**适用场景**:
- 生产环境部署
- 高质量文档处理
- 需要精确去重的应用

### 3. 重复处理策略

**当前状态**: `duplicate_strategy` 配置项已被读取，但去重逻辑始终采用"保留第一个"（keep_first）策略。合并（merge）策略尚未实现。

- **keep_first**: 保留首次出现的文本块，移除后续重复块（默认且当前唯一行为）
- **merge**: 已预留配置项，尚未实现

---

## 配置参数

### 完整配置
```yaml
deduper:
  # 去重策略: test（测试环境）/ production（生产环境）
  strategy: "test"
  
  # 重复块处理策略（已预留，当前仅支持 keep_first）
  duplicate_strategy: "keep_first"
  
  # 哈希表持久化路径（用于增量去重）
  hash_table_path: "./cache/dedup_hash_table.json"
  
  # 测试模式配置
  test:
    use_hash: true          # 是否使用哈希去重
    use_simhash: true       # 是否使用SimHash去重
    simhash_threshold: 3    # SimHash汉明距离阈值
  
  # 生产模式配置
  production:
    use_hash: true          # 是否使用哈希去重
    use_simhash: true       # 是否使用SimHash去重
    use_embedding: true     # 是否使用Embedding去重（⚠️ TODO）
    simhash_threshold: 3    # SimHash汉明距离阈值
    embedding_threshold: 0.95  # Embedding相似度阈值（⚠️ TODO，暂未使用）
```

### 配置读取逻辑

```python
deduper_config = self.config.get('deduper', self.config)
self.strategy = deduper_config.get('strategy', 'test')

if self.strategy == 'test':
    test_config = deduper_config.get('test', {})
    self.use_hash = test_config.get('use_hash', True)
    self.use_simhash = test_config.get('use_simhash', True)
    self.use_embedding = False  # 测试模式固定禁用
    self.simhash_threshold = test_config.get('simhash_threshold', 3)
else:  # production
    prod_config = deduper_config.get('production', {})
    self.use_hash = prod_config.get('use_hash', True)
    self.use_simhash = prod_config.get('use_simhash', True)
    self.use_embedding = prod_config.get('use_embedding', True)
    self.simhash_threshold = prod_config.get('simhash_threshold', 3)
    self.embedding_threshold = prod_config.get('embedding_threshold', 0.95)
```

---

## 使用示例

### 1. 基本使用（默认测试模式）
```python
from src.dedupers import Deduper
from src.chunkers import TextChunk

# 初始化去重器（默认测试模式）
deduper = Deduper()

# 创建文本分块示例
chunks = [
    TextChunk(content="这是第一个文本块"),
    TextChunk(content="这是第二个文本块"),
    TextChunk(content="这是第一个文本块"),     # 完全重复
    TextChunk(content="这是第一个文本块，有点不同"),  # 相似
]

# 执行去重
result = deduper.deduplicate(chunks)

print(f"原始数量: {len(chunks)}")
print(f"保留数量: {len(result.chunks)}")
print(f"移除数量: {len(result.removed_chunks)}")
print(f"重复组数量: {len(result.duplicate_groups)}")
print(f"统计信息: {result.stats}")
```

### 2. 生产模式使用
```python
from src.dedupers import Deduper

# 配置生产模式去重器
config = {
    "deduper": {
        "strategy": "production",
        "production": {
            "use_hash": True,
            "use_simhash": True,
            "use_embedding": True,  # ⚠️ TODO，暂时不会生效
            "simhash_threshold": 3,
            "embedding_threshold": 0.95
        }
    }
}

# 初始化去重器
deduper = Deduper(config)

# 执行去重
result = deduper.deduplicate(chunks)

# 查看详细统计
stats = result.stats
print(f"原始数量: {stats.get('original_count', 0)}")
print(f"保留数量: {stats.get('kept_count', 0)}")
print(f"移除数量: {stats.get('removed_count', 0)}")
print(f"去重率: {stats.get('dedup_rate', 0):.2%}")
```

### 3. 增量去重示例
```python
from src.dedupers import Deduper

# 配置增量去重
config = {
    "deduper": {
        "strategy": "production",
        "hash_table_path": "./cache/my_hash_table.json"
    }
}

# 初始化去重器（自动加载已有的哈希表）
deduper = Deduper(config)

# 第一次处理
chunks_batch1 = [...]
result1 = deduper.deduplicate(chunks_batch1)
# 处理完成后自动保存哈希表

# 第二次处理（复用同一个实例，哈希表已在内存中）
chunks_batch2 = [...]
result2 = deduper.deduplicate(chunks_batch2)
# 已知的重复文本会被自动过滤

print(f"第一批移除重复: {len(result1.removed_chunks)}")
print(f"第二批移除重复: {len(result2.removed_chunks)}")
```

### 4. 查看去重结果
```python
from src.dedupers import Deduper
import json

deduper = Deduper()
result = deduper.deduplicate(chunks)

# 使用 to_dict() 方法
report = result.to_dict()
print(json.dumps(report, ensure_ascii=False, indent=2))

# 输出示例
# {
#     "kept_count": 3,
#     "removed_count": 1,
#     "duplicate_groups": [...],
#     "stats": {
#         "original_count": 4,
#         "kept_count": 3,
#         "removed_count": 1,
#         "dedup_rate": 0.25
#     }
# }
```

### 5. 自定义去重器
```python
from src.dedupers.base import BaseDeduper, DedupResult
from src.chunkers import TextChunk

class CustomDeduper(BaseDeduper):
    """自定义去重器示例"""
    
    def __init__(self, config=None):
        super().__init__(config)
        self.custom_threshold = config.get("custom_threshold", 0.8) if config else 0.8
    
    def deduplicate(self, chunks: List[TextChunk]) -> DedupResult:
        """自定义去重逻辑"""
        unique_chunks = []
        removed_chunks = []
        duplicate_groups = []
        
        for i, chunk in enumerate(chunks):
            is_duplicate = False
            
            for j, unique_chunk in enumerate(unique_chunks):
                if self._are_similar(chunk.content, unique_chunk.content):
                    is_duplicate = True
                    removed_chunks.append(chunk)
                    
                    found_group = False
                    for group in duplicate_groups:
                        if j in group:
                            group.append(i)
                            found_group = True
                            break
                    
                    if not found_group:
                        duplicate_groups.append([j, i])
                    
                    break
            
            if not is_duplicate:
                unique_chunks.append(chunk)
        
        stats = self.calculate_stats(len(chunks), len(unique_chunks))
        stats["custom_algorithm"] = "自定义相似度检测"
        
        return DedupResult(unique_chunks, removed_chunks, duplicate_groups, stats)
    
    def _are_similar(self, text1: str, text2: str) -> bool:
        """自定义相似度检测"""
        return len(text1) > 0 and len(text2) > 0 and text1[0] == text2[0]
```

### 6. 去重报告文件
```python
# deduplicate() 执行后会自动保存去重报告
# 位置: outputs/dedup/{filename}.dedup_report.json
#
# 报告格式:
{
    "filename": "example.pdf",
    "strategy": "test",
    "original_count": 50,
    "unique_count": 45,
    "removed_count": 5,
    "stats": {
        "original_count": 50,
        "kept_count": 45,
        "removed_count": 5,
        "dedup_rate": 0.1
    },
    "duplicate_groups": [...]
}
```

---

## 扩展开发

### 1. 实现 Embedding 去重

当前 `_embedding_deduplicate` 为 TODO 状态，需要以下步骤完成：

```python
from sklearn.metrics.pairwise import cosine_similarity

def _embedding_deduplicate(self, chunks: List[TextChunk]) -> Tuple[List[TextChunk], List[TextChunk]]:
    """Embedding去重"""
    from src.encoders import EncoderManager
    
    encoder = EncoderManager(self.config)
    
    # 批量计算嵌入向量
    texts = [chunk.content for chunk in chunks]
    embeddings = encoder.encode_batch(texts)
    
    kept = []
    removed = []
    
    for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
        is_duplicate = False
        
        for j, kept_emb in enumerate(kept_embeddings):
            similarity = cosine_similarity(
                emb.reshape(1, -1),
                kept_emb.reshape(1, -1)
            )[0][0]
            
            if similarity >= self.embedding_threshold:
                is_duplicate = True
                break
        
        if is_duplicate:
            removed.append(chunk)
        else:
            kept.append(chunk)
            kept_embeddings.append(emb)
    
    return kept, removed
```

### 2. 添加新的去重算法

**步骤**: 继承 `Deduper`，添加新的去重方法

```python
class EnhancedDeduper(Deduper):
    """增强去重器，添加Jaccard去重"""
    
    def __init__(self, config=None):
        super().__init__(config)
        self.use_jaccard = config.get("use_jaccard", False) if config else False
        self.jaccard_threshold = config.get("jaccard_threshold", 0.8) if config else 0.8
    
    def deduplicate(self, chunks: List[TextChunk],
                   filename: Optional[str] = None) -> DedupResult:
        # 先执行基类的多级去重
        result = super().deduplicate(chunks, filename)
        
        # 如果需要，执行Jaccard去重
        if self.use_jaccard:
            result = self._jaccard_deduplicate(result.chunks)
        
        return result
    
    def _jaccard_similarity(self, text1: str, text2: str) -> float:
        set1 = set(text1.split())
        set2 = set(text2.split())
        if not set1 and not set2:
            return 1.0
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0
```

### 3. 实现合并 (merge) 重复处理策略

当前仅支持 `keep_first`，如果需要 `merge` 策略，需要在 `deduplicate` 方法中加入：

```python
if self.duplicate_strategy == 'merge':
    # 合并重复块内容
    merged = []
    merged_indices = set()
    for i, kept in enumerate(chunks):
        if i in merged_indices:
            continue
        for j, removed in enumerate(removed_chunks):
            if self._is_similar(kept, removed):
                kept.content = kept.content + "\n" + removed.content
                merged_indices.add(j)
```

### 4. 优化去重性能

**批处理SimHash去重**:
```python
def _batch_simhash_deduplicate(self, chunks: List[TextChunk],
                              batch_size: int = 100) -> Tuple[List[TextChunk], List[TextChunk]]:
    """批处理SimHash去重"""
    unique_chunks = []
    removed_chunks = []
    
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        fingerprints = []
        
        for chunk in batch:
            features = [chunk.content[i:i+3] for i in range(len(chunk.content)-2)]
            fingerprints.append(Simhash(features))
        
        for j, (chunk, fingerprint) in enumerate(zip(batch, fingerprints)):
            is_duplicate = False
            for k, unique_fp in enumerate(self.unique_fingerprints):
                distance = fingerprint.distance(unique_fp)
                if distance <= self.simhash_threshold:
                    is_duplicate = True
                    break
            
            if is_duplicate:
                removed_chunks.append(chunk)
            else:
                unique_chunks.append(chunk)
                self.unique_fingerprints.append(fingerprint)
    
    return unique_chunks, removed_chunks
```

### 5. 集成外部库（MinHash 示例）

```python
from datasketch import MinHash, MinHashLSH

class MinHashDeduper(BaseDeduper):
    """MinHash去重器"""
    
    def __init__(self, config=None):
        super().__init__(config)
        self.threshold = config.get("threshold", 0.8) if config else 0.8
        self.num_perm = config.get("num_perm", 128) if config else 128
        self.lsh = MinHashLSH(threshold=self.threshold, num_perm=self.num_perm)
    
    def deduplicate(self, chunks: List[TextChunk]) -> DedupResult:
        unique_chunks = []
        removed_chunks = []
        
        for i, chunk in enumerate(chunks):
            m = MinHash(num_perm=self.num_perm)
            for word in chunk.content.split():
                m.update(word.encode('utf-8'))
            
            result = self.lsh.query(m)
            
            if result:
                removed_chunks.append(chunk)
            else:
                unique_chunks.append(chunk)
                self.lsh.insert(f"chunk_{i}", m)
        
        return DedupResult(unique_chunks, removed_chunks, [], {})
```

---

## 常见问题

### Q1: 如何选择去重策略？

**推荐选择**:
- **测试/开发环境**: 使用测试模式（`test`），快速验证
- **生产环境**: 使用生产模式（`production`），提升去重质量
- **注意**: 当前两种模式的实际区别仅在于 `use_embedding` 开关，Embedding 去重尚未实现

### Q2: 去重阈值如何设置？

**SimHash阈值设置指南**:
- 严格: 1-2（只移除几乎相同的文本）
- 适中: 3（默认值，移除高度相似的文本）
- 宽松: 4-5（移除相似度较高的文本）

**Embedding阈值**（预留，尚未启用）:
- 严格: 0.97-0.99
- 适中: 0.95
- 宽松: 0.90-0.94

### Q3: 增量去重如何工作？

**工作原理**:
1. 初始化时，`__init__` 自动调用 `_load_hash_table()` 加载已有哈希表
2. 处理时，哈希去重步骤使用 `self.seen_hashes` 判断重复
3. 处理完成后，`deduplicate` 自动调用 `_save_hash_table()` 持久化哈希表
4. 哈希表以 JSON 格式存储，默认位置 `./cache/dedup_hash_table.json`
5. 保存失败不影响主流程（仅记录 warning 日志）

### Q4: Embedding 去重何时实现？

当前 `_embedding_deduplicate` 方法为纯桩代码（`return chunks, []`），没有任何去重效果。

**实现前提**:
- 需要引入 Encoder 模块依赖（`from src.encoders import EncoderManager`）
- 需要批量计算文本嵌入向量
- 需要计算余弦相似度矩阵
- 建议在 Encoder 模块稳定后实现

### Q5: 去重性能如何优化？

**性能优化建议**:
1. **SimHash 特征计算**: 当前每次重新计算 trigram 特征，可缓存已计算的 SimHash
2. **比较优化**: 当前为 O(n²) 全量比较，可引入索引结构优化
3. **批处理**: 对大文件可分批处理 SimHash 计算
4. **哈希表**: 哈希去重为 O(n)，性能最优，建议始终开启

### Q6: 如何查看去重结果？

有三种方式获取去重结果：
1. **代码中**: 访问 `result.chunks`、`result.removed_chunks`、`result.stats`
2. **序列化**: 调用 `result.to_dict()` 获取字典
3. **报告文件**: `deduplicate` 自动保存 JSON 报告到 `outputs/dedup/` 目录

---

## 版本历史

### v1.0.0 (当前版本)
- 实现多级去重框架（哈希、SimHash）
- 支持测试和生产两种策略
- 实现增量去重和哈希表 JSON 持久化
- 提供统计信息和去重报告输出
- SimHash 基于字符 trigram 特征
- 哈希去重支持 `chunk.content_hash` 属性优先
- 内置进度显示（SimHash 计算和比较）

### 待实现功能
- [ ] Embedding 去重（`_embedding_deduplicate` TODO）
- [ ] 合并策略（`duplicate_strategy: merge`）
- [ ] 并行去重处理
- [ ] MinHash/Jaccard 等更多去重算法
- [ ] Embedding 阈值可调

---

## 相关链接

- [SimHash 算法详解](https://en.wikipedia.org/wiki/SimHash)
- [MinHash 算法原理](https://en.wikipedia.org/wiki/MinHash)
- [Jaccard 相似度系数](https://en.wikipedia.org/wiki/Jaccard_index)
- [余弦相似度计算](https://en.wikipedia.org/wiki/Cosine_similarity)
