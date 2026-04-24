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

Deduper 模块是文档 RAG 系统的文本去重组件，负责检测和移除重复的文本分块。该模块提供多级去重功能，从精确匹配到语义相似度检测，确保向量数据库中存储的文本分块具有高质量和多样性。

### 主要功能

1. **多级去重算法**:
   - **哈希去重**: 精确内容匹配，移除完全相同的文本
   - **SimHash去重**: 近似内容检测，移除高度相似的文本
   - **Embedding去重**: 语义相似度检测，移除语义重复的文本

2. **灵活的去重策略**:
   - **测试模式**: 快速去重，使用哈希和 SimHash 算法
   - **生产模式**: 高质量去重，使用所有三级算法

3. **增量去重支持**:
   - 哈希表持久化，避免重复检测
   - 支持断点续传
   - 性能统计和报告生成

4. **重复处理策略**:
   - **保留第一个**: 保留首次出现的文本块
   - **合并内容**: 合并重复文本块的内容

### 去重流程

```
原始文本分块
    │
    ├─> 1. 哈希去重 (可选)
    │      ├─ 计算内容哈希值 (MD5)
    │      ├─ 检查哈希表
    │      ├─ 移除完全相同的文本
    │      └─ 记录哈希到持久化表
    │
    ├─> 2. SimHash去重 (可选)
    │      ├─ 计算 SimHash 指纹
    │      ├─ 比较汉明距离
    │      ├─ 移除高度相似的文本
    │      └─ 阈值: 3 (可配置)
    │
    ├─> 3. Embedding去重 (可选)
    │      ├─ 计算文本嵌入向量
    │      ├─ 计算余弦相似度
    │      ├─ 移除语义相似的文本
    │      └─ 阈值: 0.95 (可配置)
    │
    └─> 4. 结果处理
           ├─ 生成去重报告
           ├─ 更新统计信息
           └─ 返回唯一文本分块
```

---

## 文件结构

```
src/dedupers/
├── __init__.py              # 模块导出
├── base.py                  # 基类和接口定义
└── deduper.py               # 多级去重器实现
```

---

## 核心类与接口

### 1. BaseDeduper (抽象基类)

所有去重器的基类，定义统一的去重接口：

```python
class BaseDeduper(ABC):
    """去重器基类"""
    
    @abstractmethod
    def deduplicate(self, chunks: List[TextChunk], 
                   filename: Optional[str] = None) -> DedupResult:
        """去重文本块"""
        pass
    
    @abstractmethod
    def calculate_stats(self, original_count: int, 
                       final_count: int) -> Dict[str, Any]:
        """计算统计信息"""
        pass
    
    def _load_hash_table(self):
        """加载哈希表（用于增量去重）"""
    
    def _save_hash_table(self):
        """保存哈希表"""
```

### 2. DedupResult (去重结果类)

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
        # 初始化逻辑
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（支持JSON序列化）"""
    
    @property
    def kept_count(self) -> int:
        """保留的文本块数量"""
        return len(self.chunks)
    
    @property
    def removed_count(self) -> int:
        """移除的重复块数量"""
        return len(self.removed_chunks)
    
    @property
    def duplicate_group_count(self) -> int:
        """重复组数量"""
        return len(self.duplicate_groups)
```

### 3. Deduper (多级去重器)

实现多级去重算法的主要类：

```python
class Deduper(BaseDeduper):
    """多级去重器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化去重器
        
        Args:
            config: 配置字典，包含：
                - deduper.strategy: 去重策略 (test/production)
                - deduper.duplicate_strategy: 重复处理策略 (keep_first/merge)
                - deduper.test.use_hash: 测试模式是否使用哈希去重
                - deduper.test.use_simhash: 测试模式是否使用SimHash去重
                - deduper.test.simhash_threshold: SimHash阈值
                - deduper.production.*: 生产模式对应配置
        """
    
    def deduplicate(self, chunks: List[TextChunk], 
                   filename: Optional[str] = None) -> DedupResult:
        """执行多级去重"""
    
    def _hash_deduplicate(self, chunks: List[TextChunk]) -> Tuple[List[TextChunk], List[TextChunk]]:
        """哈希去重"""
    
    def _simhash_deduplicate(self, chunks: List[TextChunk]) -> Tuple[List[TextChunk], List[TextChunk]]:
        """SimHash去重"""
    
    def _embedding_deduplicate(self, chunks: List[TextChunk]) -> Tuple[List[TextChunk], List[TextChunk]]:
        """Embedding去重"""
```

---

## 去重算法

### 1. 哈希去重 (Hash Deduplication)

**算法原理**: 使用 MD5 哈希算法计算文本内容的唯一标识，通过比较哈希值检测完全相同的文本。

**适用场景**:
- 完全相同的文本内容
- 快速去重，计算成本低
- 精确匹配，无误判

**实现细节**:
```python
def _hash_deduplicate(self, chunks: List[TextChunk]) -> Tuple[List[TextChunk], List[TextChunk]]:
    """哈希去重"""
    unique_chunks = []
    removed_chunks = []
    seen_hashes = set(self.seen_hashes)  # 从持久化表加载的哈希
    
    for chunk in chunks:
        content_hash = hashlib.md5(chunk.content.encode('utf-8')).hexdigest()
        
        if content_hash in seen_hashes:
            # 发现重复，记录移除的块
            removed_chunks.append(chunk)
        else:
            # 唯一内容，添加到结果集
            unique_chunks.append(chunk)
            seen_hashes.add(content_hash)
    
    # 更新持久化哈希表
    self.seen_hashes.update(seen_hashes)
    
    return unique_chunks, removed_chunks
```

**性能特点**:
- 时间复杂度: O(n)
- 空间复杂度: O(n)（哈希表存储）
- 准确率: 100%（完全匹配）

### 2. SimHash 去重 (SimHash Deduplication)

**算法原理**: 使用 SimHash 算法生成文本的指纹，通过比较汉明距离检测相似文本。

**适用场景**:
- 高度相似的文本（修改少量字符）
- 近似去重，容忍微小差异
- 计算成本中等

**实现细节**:
```python
def _simhash_deduplicate(self, chunks: List[TextChunk]) -> Tuple[List[TextChunk], List[TextChunk]]:
    """SimHash去重"""
    unique_chunks = []
    removed_chunks = []
    seen_fingerprints = []
    
    for chunk in chunks:
        # 计算SimHash指纹
        fingerprint = Simhash(chunk.content)
        
        # 检查是否与已有指纹相似
        is_duplicate = False
        for seen_fp in seen_fingerprints:
            distance = fingerprint.distance(seen_fp)
            if distance <= self.simhash_threshold:
                is_duplicate = True
                break
        
        if is_duplicate:
            removed_chunks.append(chunk)
        else:
            unique_chunks.append(chunk)
            seen_fingerprints.append(fingerprint)
    
    return unique_chunks, removed_chunks
```

**参数说明**:
- `simhash_threshold`: 汉明距离阈值
  - 默认值: 3
  - 范围: 0-64（64位SimHash）
  - 值越小越严格，值越大越宽松

**性能特点**:
- 时间复杂度: O(n²)（最坏情况）
- 空间复杂度: O(n)（指纹存储）
- 准确率: 可配置，依赖阈值设置

### 3. Embedding 去重 (Embedding Deduplication)

**算法原理**: 使用文本嵌入向量计算语义相似度，通过余弦相似度检测语义重复的文本。

**适用场景**:
- 语义相似的文本（表达相同意思的不同表述）
- 高质量去重，理解文本语义
- 计算成本较高（需要编码模型）

**实现细节**:
```python
def _embedding_deduplicate(self, chunks: List[TextChunk]) -> Tuple[List[TextChunk], List[TextChunk]]:
    """Embedding去重"""
    unique_chunks = []
    removed_chunks = []
    
    # 批量计算嵌入向量
    texts = [chunk.content for chunk in chunks]
    embeddings = self.encoder.encode_batch(texts)
    
    # 相似度矩阵计算
    for i, (chunk, embedding_i) in enumerate(zip(chunks, embeddings)):
        is_duplicate = False
        
        for j, (unique_chunk, embedding_j) in enumerate(zip(unique_chunks, embeddings[:len(unique_chunks)])):
            # 计算余弦相似度
            similarity = cosine_similarity(
                embedding_i.dense_vector.reshape(1, -1),
                embedding_j.dense_vector.reshape(1, -1)
            )[0][0]
            
            if similarity >= self.embedding_threshold:
                is_duplicate = True
                break
        
        if is_duplicate:
            removed_chunks.append(chunk)
        else:
            unique_chunks.append(chunk)
    
    return unique_chunks, removed_chunks
```

**参数说明**:
- `embedding_threshold`: 余弦相似度阈值
  - 默认值: 0.95
  - 范围: 0.0-1.0
  - 值越大越严格，值越小越宽松

**性能特点**:
- 时间复杂度: O(n²)（最坏情况，加上编码时间）
- 空间复杂度: O(n×d)（d为向量维度）
- 准确率: 依赖编码模型质量和阈值设置

---

## 去重策略

### 1. 测试模式 (Test Strategy)

**设计目标**: 快速去重，适用于开发和测试环境

**配置特点**:
- 启用哈希去重和 SimHash 去重
- 禁用 Embedding 去重（减少计算成本）
- 宽松的阈值设置
- 最小化处理时间

**配置示例**:
```yaml
deduper:
  strategy: "test"
  duplicate_strategy: "keep_first"
  
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

**配置特点**:
- 启用所有三级去重算法
- 严格的阈值设置
- 详细的统计报告
- 支持增量更新

**配置示例**:
```yaml
deduper:
  strategy: "production"
  duplicate_strategy: "keep_first"
  
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

#### 3.1 保留第一个 (keep_first)

**策略描述**: 保留首次出现的文本块，移除后续重复块

**优点**:
- 保持原始顺序
- 简单直观
- 处理速度快

**缺点**:
- 可能保留质量较低的版本

#### 3.2 合并内容 (merge)

**策略描述**: 合并重复文本块的内容

**实现方式**:
- 连接重复文本块的内容
- 移除重复部分
- 生成合并后的文本

**优点**:
- 保留所有信息
- 可能提高文本质量

**缺点**:
- 实现复杂
- 可能破坏文本结构
- 处理速度慢

---

## 配置参数

### 全局配置
```yaml
deduper:
  # 去重策略: test（测试环境）/ production（生产环境）
  strategy: "test"
  
  # 重复块处理策略: keep_first（保留第一个）/ merge（合并内容）
  duplicate_strategy: "keep_first"
  
  # 哈希表持久化路径（用于增量去重）
  hash_table_path: "./cache/dedup_hash_table.json"
```

### 测试模式配置
```yaml
deduper:
  strategy: "test"
  
  test:
    use_hash: true          # 是否使用哈希去重
    use_simhash: true       # 是否使用SimHash去重
    use_embedding: false    # 测试模式通常禁用Embedding去重
    simhash_threshold: 3    # SimHash汉明距离阈值
```

### 生产模式配置
```yaml
deduper:
  strategy: "production"
  
  production:
    use_hash: true          # 是否使用哈希去重
    use_simhash: true       # 是否使用SimHash去重
    use_embedding: true     # 是否使用Embedding去重
    simhash_threshold: 3    # SimHash汉明距离阈值
    embedding_threshold: 0.95  # Embedding相似度阈值
```

### 高级配置
```yaml
deduper:
  # 增量去重配置
  incremental:
    enabled: true           # 是否启用增量去重
    hash_table_ttl: 30      # 哈希表生存时间（天）
    cleanup_interval: 7     # 清理间隔（天）
  
  # 性能优化配置
  performance:
    batch_size: 100         # 批处理大小
    parallel_processing: false  # 是否启用并行处理
    max_workers: 2          # 最大工作线程数
  
  # 报告生成配置
  reporting:
    generate_report: true   # 是否生成去重报告
    report_format: "json"   # 报告格式 (json/csv)
    save_removed_chunks: false  # 是否保存被移除的块
```

---

## 使用示例

### 1. 基本使用
```python
from src.dedupers import Deduper
from src.chunkers import TextChunk

# 初始化去重器（默认测试模式）
deduper = Deduper()

# 创建文本分块示例
chunks = [
    TextChunk(content="这是第一个文本块", chunk_id="chunk1"),
    TextChunk(content="这是第二个文本块", chunk_id="chunk2"),
    TextChunk(content="这是第一个文本块", chunk_id="chunk3"),  # 完全重复
    TextChunk(content="这是第一个文本块，有点不同", chunk_id="chunk4"),  # 相似但不完全相同
]

# 执行去重
result = deduper.deduplicate(chunks)

print(f"原始数量: {len(chunks)}")
print(f"保留数量: {result.kept_count}")
print(f"移除数量: {result.removed_count}")
print(f"重复组数量: {result.duplicate_group_count}")
```

### 2. 生产模式使用
```python
from src.dedupers import Deduper

# 配置生产模式去重器
config = {
    "deduper": {
        "strategy": "production",
        "duplicate_strategy": "keep_first",
        "production": {
            "use_hash": True,
            "use_simhash": True,
            "use_embedding": True,
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
print(f"哈希去重移除: {stats.get('hash_removed', 0)}")
print(f"SimHash去重移除: {stats.get('simhash_removed', 0)}")
print(f"Embedding去重移除: {stats.get('embedding_removed', 0)}")
```

### 3. 增量去重示例
```python
from src.dedupers import Deduper
from src.utils import FileUtils

# 配置增量去重
config = {
    "deduper": {
        "strategy": "production",
        "hash_table_path": "./cache/my_hash_table.json"
    }
}

# 初始化去重器
deduper = Deduper(config)

# 第一次处理（构建哈希表）
chunks_batch1 = [...]  # 第一批文本块
result1 = deduper.deduplicate(chunks_batch1)
deduper._save_hash_table()  # 保存哈希表

# 第二次处理（使用已有的哈希表）
chunks_batch2 = [...]  # 第二批文本块
result2 = deduper.deduplicate(chunks_batch2)

# 第二批处理时会自动加载之前保存的哈希表
print(f"第一批移除重复: {result1.removed_count}")
print(f"第二批移除重复: {result2.removed_count}")
```

### 4. 生成去重报告
```python
from src.dedupers import Deduper
import json

# 初始化去重器
deduper = Deduper()

# 执行去重
result = deduper.deduplicate(chunks)

# 生成JSON报告
report = result.to_dict()
with open("dedup_report.json", "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

# 生成详细统计报告
detailed_stats = {
    "summary": {
        "original_count": len(chunks),
        "kept_count": result.kept_count,
        "removed_count": result.removed_count,
        "dedup_rate": f"{(result.removed_count / len(chunks) * 100):.2f}%"
    },
    "algorithm_stats": result.stats,
    "duplicate_groups": result.duplicate_groups
}

print("去重报告已生成:")
print(f"  原始数量: {detailed_stats['summary']['original_count']}")
print(f"  保留数量: {detailed_stats['summary']['kept_count']}")
print(f"  移除数量: {detailed_stats['summary']['removed_count']}")
print(f"  去重率: {detailed_stats['summary']['dedup_rate']}")
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
    
    def deduplicate(self, chunks: List[TextChunk], 
                   filename: Optional[str] = None) -> DedupResult:
        """自定义去重逻辑"""
        unique_chunks = []
        removed_chunks = []
        duplicate_groups = []
        
        # 自定义去重算法
        for i, chunk in enumerate(chunks):
            is_duplicate = False
            
            # 检查是否与已保留的块重复
            for j, unique_chunk in enumerate(unique_chunks):
                if self._are_similar(chunk.content, unique_chunk.content):
                    is_duplicate = True
                    removed_chunks.append(chunk)
                    
                    # 记录重复组
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
        
        # 计算统计信息
        stats = self.calculate_stats(len(chunks), len(unique_chunks))
        stats["custom_algorithm"] = "自定义相似度检测"
        
        return DedupResult(unique_chunks, removed_chunks, duplicate_groups, stats)
    
    def _are_similar(self, text1: str, text2: str) -> bool:
        """自定义相似度检测"""
        # 实现自定义相似度算法
        # 例如: Jaccard相似度、编辑距离等
        return len(text1) > 0 and len(text2) > 0 and text1[0] == text2[0]  # 简化示例
    
    def calculate_stats(self, original_count: int, final_count: int) -> Dict[str, Any]:
        """计算统计信息"""
        return {
            "original_count": original_count,
            "final_count": final_count,
            "removed_count": original_count - final_count,
            "dedup_rate": (original_count - final_count) / original_count if original_count > 0 else 0,
            "custom_threshold": self.custom_threshold
        }
```

---

## 扩展开发

### 1. 添加新的去重算法

**步骤 1**: 创建新的去重算法方法
```python
class EnhancedDeduper(Deduper):
    """增强去重器，添加新算法"""
    
    def __init__(self, config=None):
        super().__init__(config)
        self.use_jaccard = config.get("use_jaccard", False) if config else False
        self.jaccard_threshold = config.get("jaccard_threshold", 0.8) if config else 0.8
    
    def deduplicate(self, chunks: List[TextChunk], 
                   filename: Optional[str] = None) -> DedupResult:
        """重写去重方法，添加Jaccard去重"""
        
        # 先执行基类的多级去重
        result = super().deduplicate(chunks, filename)
        
        # 如果需要，执行Jaccard去重
        if self.use_jaccard:
            result = self._jaccard_deduplicate(result.chunks)
        
        return result
    
    def _jaccard_deduplicate(self, chunks: List[TextChunk]) -> DedupResult:
        """Jaccard相似度去重"""
        unique_chunks = []
        removed_chunks = []
        
        for chunk in chunks:
            is_duplicate = False
            
            for unique_chunk in unique_chunks:
                # 计算Jaccard相似度
                similarity = self._jaccard_similarity(
                    chunk.content, 
                    unique_chunk.content
                )
                
                if similarity >= self.jaccard_threshold:
                    is_duplicate = True
                    removed_chunks.append(chunk)
                    break
            
            if not is_duplicate:
                unique_chunks.append(chunk)
        
        return DedupResult(
            unique_chunks, 
            removed_chunks, 
            [],  # 简化示例，不计算重复组
            {"jaccard_removed": len(removed_chunks)}
        )
    
    def _jaccard_similarity(self, text1: str, text2: str) -> float:
        """计算Jaccard相似度"""
        set1 = set(text1.split())
        set2 = set(text2.split())
        
        if not set1 and not set2:
            return 1.0
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
```

**步骤 2**: 更新配置支持
```yaml
deduper:
  strategy: "enhanced"
  
  enhanced:
    use_hash: true
    use_simhash: true
    use_embedding: false
    use_jaccard: true
    jaccard_threshold: 0.8
    simhash_threshold: 3
```

### 2. 优化去重性能

**批处理优化**:
```python
def _batch_simhash_deduplicate(self, chunks: List[TextChunk], 
                              batch_size: int = 100) -> Tuple[List[TextChunk], List[TextChunk]]:
    """批处理SimHash去重"""
    unique_chunks = []
    removed_chunks = []
    
    # 分批处理
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        
        # 批量计算SimHash
        fingerprints = [Simhash(chunk.content) for chunk in batch]
        
        # 批量比较
        for j, (chunk, fingerprint) in enumerate(zip(batch, fingerprints)):
            is_duplicate = False
            
            # 与已保留的块比较
            for k, (unique_chunk, unique_fp) in enumerate(zip(unique_chunks, self.unique_fingerprints)):
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

**并行处理优化**:
```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def _parallel_deduplicate(self, chunks: List[TextChunk]) -> DedupResult:
    """并行去重"""
    # 将文本块分片
    num_slices = min(self.max_workers, len(chunks))
    slice_size = len(chunks) // num_slices
    slices = [chunks[i:i + slice_size] for i in range(0, len(chunks), slice_size)]
    
    unique_chunks = []
    removed_chunks = []
    
    with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
        # 提交并行任务
        future_to_slice = {
            executor.submit(self._deduplicate_slice, slice): slice 
            for slice in slices
        }
        
        # 收集结果
        for future in as_completed(future_to_slice):
            slice_unique, slice_removed = future.result()
            unique_chunks.extend(slice_unique)
            removed_chunks.extend(slice_removed)
    
    return DedupResult(unique_chunks, removed_chunks, [], {})
```

### 3. 集成外部库

**集成 MinHash 算法**:
```python
from datasketch import MinHash, MinHashLSH

class MinHashDeduper(BaseDeduper):
    """MinHash去重器"""
    
    def __init__(self, config=None):
        super().__init__(config)
        self.threshold = config.get("threshold", 0.8) if config else 0.8
        self.num_perm = config.get("num_perm", 128) if config else 128
        self.lsh = MinHashLSH(threshold=self.threshold, num_perm=self.num_perm)
    
    def deduplicate(self, chunks: List[TextChunk], 
                   filename: Optional[str] = None) -> DedupResult:
        """MinHash去重"""
        unique_chunks = []
        removed_chunks = []
        
        for i, chunk in enumerate(chunks):
            # 创建MinHash
            m = MinHash(num_perm=self.num_perm)
            for word in chunk.content.split():
                m.update(word.encode('utf-8'))
            
            # 查询LSH
            result = self.lsh.query(m)
            
            if result:
                # 发现重复
                removed_chunks.append(chunk)
            else:
                # 唯一内容
                unique_chunks.append(chunk)
                # 插入到LSH
                self.lsh.insert(f"chunk_{i}", m)
        
        return DedupResult(unique_chunks, removed_chunks, [], {})
```

---

## 常见问题

### Q1: 如何选择去重策略？

**推荐选择**:
- **测试/开发环境**: 使用测试模式，快速验证
- **生产环境**: 使用生产模式，确保质量
- **大量文档初步处理**: 先使用测试模式快速去重，再用生产模式精细处理
- **高质量要求场景**: 启用所有三级算法

### Q2: 去重阈值如何设置？

**阈值设置指南**:
- **SimHash阈值**: 
  - 严格: 1-2（只移除几乎相同的文本）
  - 适中: 3（默认值，移除高度相似的文本）
  - 宽松: 4-5（移除相似度较高的文本）
  
- **Embedding阈值**:
  - 严格: 0.97-0.99（只移除语义几乎相同的文本）
  - 适中: 0.95（默认值，移除语义高度相似的文本）
  - 宽松: 0.90-0.94（移除语义相似的文本）

### Q3: 增量去重如何工作？

**工作原理**:
1. 首次处理时，计算文本哈希并存储到哈希表
2. 后续处理时，加载已有的哈希表
3. 对新文本计算哈希，与哈希表比较
4. 发现重复则跳过，新文本则添加到哈希表
5. 定期清理过期的哈希表记录

### Q4: 去重性能如何优化？

**性能优化建议**:
1. **批处理**: 调整 `batch_size` 参数
2. **并行处理**: 启用 `parallel_processing`（CPU密集型任务）
3. **算法选择**: 根据需求选择合适的算法组合
4. **缓存优化**: 合理设置哈希表生存时间
5. **内存管理**: 监控内存使用，避免内存溢出

### Q5: 如何处理误判？

**误判处理策略**:
1. **调整阈值**: 根据实际效果调整相似度阈值
2. **白名单机制**: 添加不应被去重的文本
3. **人工审核**: 对疑似重复的文本进行人工确认
4. **多轮去重**: 使用不同算法进行多轮去重，降低误判率

---

## 版本历史

### v1.0.0 (初始版本)
- 实现多级去重算法（哈希、SimHash、Embedding）
- 支持测试和生产两种策略
- 实现增量去重和哈希表持久化
- 提供详细的统计报告

### v1.1.0 (计划功能)
- 支持更多去重算法（MinHash、Jaccard等）
- 实现并行去重处理
- 添加误判纠正机制
- 优化内存使用和性能

---

## 相关链接

- [SimHash 算法详解](https://en.wikipedia.org/wiki/SimHash)
- [MinHash 算法原理](https://en.wikipedia.org/wiki/MinHash)
- [Jaccard 相似度系数](https://en.wikipedia.org/wiki/Jaccard_index)
- [余弦相似度计算](https://en.wikipedia.org/wiki/Cosine_similarity)
