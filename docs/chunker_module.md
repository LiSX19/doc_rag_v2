# Chunker 模块详细说明文档

## 目录
1. [模块概述](#模块概述)
2. [文件结构](#文件结构)
3. [核心类与接口](#核心类与接口)
4. [分块策略](#分块策略)
5. [分块管理器](#分块管理器)
6. [输入与输出](#输入与输出)
7. [参数配置](#参数配置)
8. [使用示例](#使用示例)
9. [扩展开发](#扩展开发)

---

## 模块概述

Chunker 模块是文档 RAG 系统的文本分块组件，负责：
- 将长文本分割成适合 Embedding 的文本块
- 支持多种分块策略（递归分块、Token分块等）
- 提供中文优化的分隔符列表
- 实现分块后处理（过滤短块、合并相邻块）
- 管理分块数据库，支持增量更新

### 分块流程

```
清洗后的文本
    │
    ├─> 1. 文本分块
    │      ├─ 递归分块（按分隔符层级分割）
    │      └─ 返回 TextChunk 列表
    │
    ├─> 2. 后处理
    │      ├─ 过滤过短的分块
    │      ├─ 合并相邻的短分块
    │      └─ 返回处理后的分块列表
    │
    └─> 3. 存储到数据库
           ├─ 计算文件哈希
           ├─ 存储分块记录
           └─ 支持增量更新检查
```

---

## 文件结构

```
src/chunkers/
├── __init__.py              # 模块导出
├── base.py                  # 基础分块器抽象类
├── recursive_chunker.py     # 递归分块器实现
└── chunk_manager.py         # 分块管理器（数据库操作）
```

### 文件关系图

```
┌─────────────────────────────────────────────────────────────┐
│                    ChunkManager (分块管理器)                  │
│                   - 分块存储                                  │
│                   - 增量更新检查                               │
│                   - 数据库管理                                 │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ ChunkDatabase│ │ ChunkRecord  │ │FileChunkRecord│
│ (JSON数据库)  │ │ (分块记录)   │ │ (文件记录)    │
└──────┬────────┘ └──────────────┘ └──────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│                    具体分块器实现                            │
├─────────────────────────────────────────────────────────────┤
│ RecursiveChunker (递归分块器)                                │
│ - 按分隔符层级递归分割                                        │
│ - 中文优化分隔符列表                                          │
│ - 支持重叠分块                                                │
└─────────────────────────────────────────────────────────────┘
```

---

## 核心类与接口

### 1. BaseChunker (base.py)

所有分块器的抽象基类。

```python
class BaseChunker(ABC):
    def __init__(self, config: Optional[Dict[str, Any]] = None)
    
    @abstractmethod
    def split(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[TextChunk]
    
    def split_and_save(self, text: str, filename: str, metadata: Optional[Dict[str, Any]] = None) -> List[TextChunk]
```

### 2. TextChunk (base.py)

文本分块数据类。

```python
@dataclass
class TextChunk:
    index: int              # 分块索引
    content: str            # 分块内容
    start_pos: int          # 在原文中的起始位置
    end_pos: int            # 在原文中的结束位置
    metadata: Dict[str, Any] # 元数据
```

### 3. RecursiveChunker (recursive_chunker.py)

递归分块器实现。

```python
class RecursiveChunker(BaseChunker):
    def __init__(self, config: Optional[Dict[str, Any]] = None)
    
    def split(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[TextChunk]
    
    def _post_process(self, chunks: List[TextChunk]) -> List[TextChunk]
```

### 4. ChunkManager (chunk_manager.py)

分块管理器，负责分块的存储和增量更新。

```python
class ChunkManager:
    def __init__(self, config: Optional[Dict[str, Any]] = None)
    
    def compute_file_hash(self, file_path: Union[str, Path], algorithm: str = 'md5') -> str
    
    def compute_content_hash(self, content: str, algorithm: str = 'md5') -> str
    
    def check_file_processed(self, file_path: Union[str, Path], content: Optional[str] = None) -> Tuple[bool, str]
    
    def store_chunks(
        self,
        file_path: Union[str, Path],
        chunks: List[Any],
        file_hash: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[ChunkRecord]
    
    def get_file_chunks(self, file_path: Union[str, Path]) -> List[ChunkRecord]
    
    def get_stats(self) -> Dict[str, Any]
```

### 5. ChunkDatabase (chunk_manager.py)

分块数据库，JSON文件存储。

```python
class ChunkDatabase:
    def __init__(self, db_path: Union[str, Path])
    
    def add_chunks(self, chunks: List[ChunkRecord], file_record: FileChunkRecord)
    
    def get_chunks_by_file(self, file_path: str) -> List[ChunkRecord]
    
    def get_file_record(self, file_path: str) -> Optional[FileChunkRecord]
    
    def delete_file_chunks(self, file_path: str) -> bool
    
    def check_file_hash(self, file_path: str, current_hash: str) -> bool
    
    def get_stats(self) -> Dict[str, Any]
```

### 6. ChunkRecord (chunk_manager.py)

分块记录数据类。

```python
class ChunkRecord:
    def __init__(
        self,
        chunk_id: str,           # 分块唯一ID
        content: str,            # 分块内容
        source_file: str,        # 源文件路径
        chunk_index: int,        # 分块在文件中的索引
        start_pos: int = 0,      # 在原文中的起始位置
        end_pos: int = 0,        # 在原文中的结束位置
        metadata: Optional[Dict[str, Any]] = None,
        created_at: Optional[str] = None
    )
    
    def to_dict(self) -> Dict[str, Any]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChunkRecord'
    
    def compute_hash(self) -> str
```

---

## 分块策略

### 递归分块 (RecursiveChunker)

递归分块器按分隔符层级递归分割文本，优先使用高级别分隔符，如果分块仍然过大，则使用低级别分隔符继续分割。

#### 中文优化分隔符列表

```python
separators = [
    "\n\n",  # 段落分隔
    "\n",    # 换行
    "。",     # 句号
    "；",    # 分号
    "，",    # 逗号
    " ",     # 空格
    ""       # 字符
]
```

#### 分块流程

```
文本
  │
  ├─> 尝试用 "\n\n" 分割
  │      ├─ 每个片段 <= chunk_size → 保留
  │      └─ 片段 > chunk_size → 继续用 "\n" 分割
  │
  ├─> 尝试用 "\n" 分割
  │      ├─ 每个片段 <= chunk_size → 保留
  │      └─ 片段 > chunk_size → 继续用 "。" 分割
  │
  ├─> 尝试用 "。" 分割
  │      └─ ... 继续递归
  │
  └─> 最后用字符分割（强制分块）
```

#### 重叠分块

相邻分块之间可以设置重叠区域，确保语义连续性：

```
分块1: [内容A + 内容B]
分块2: [内容B + 内容C]  (内容B是重叠部分)
分块3: [内容C + 内容D]  (内容C是重叠部分)
```

---

## 分块管理器

### 数据库结构

分块数据库使用 JSON 文件存储，包含两个主要部分：

```json
{
  "chunks": [
    {
      "chunk_id": "/path/to/file.pdf#0",
      "content": "分块内容...",
      "source_file": "/path/to/file.pdf",
      "chunk_index": 0,
      "start_pos": 0,
      "end_pos": 500,
      "metadata": {...},
      "created_at": "2024-01-15T12:00:00"
    }
  ],
  "files": [
    {
      "file_path": "/path/to/file.pdf",
      "file_hash": "md5_hash_value",
      "chunk_ids": ["/path/to/file.pdf#0", "/path/to/file.pdf#1"],
      "processed_at": "2024-01-15T12:00:00",
      "metadata": {...}
    }
  ],
  "updated_at": "2024-01-15T12:00:00"
}
```

### 增量更新流程

```
处理文件
  │
  ├─> 1. 计算文件哈希
  │
  ├─> 2. 检查数据库
  │      ├─ 文件存在且哈希匹配 → 跳过处理
  │      └─ 文件不存在或哈希不匹配 → 继续处理
  │
  ├─> 3. 删除旧分块记录（如果存在）
  │
  ├─> 4. 执行分块
  │
  └─> 5. 存储新分块记录
```

---

## 输入与输出

### 输入

**文本内容：**
- `str`: 清洗后的文本内容

**配置参数：**
```python
config = {
    'chunker': {
        'strategy': 'recursive',           # 分块策略
        'chunk_size': 500,                  # 分块大小
        'chunk_overlap': 50,                # 分块重叠长度
        'separators': [                     # 分隔符列表
            '\n\n', '\n', '。', '；', '，', ' ', ''
        ],
        'post_process': {
            'filter_short_chunks': True,    # 过滤短块
            'min_chunk_length': 20,         # 最小分块长度
            'merge_adjacent_short': True,   # 合并相邻短块
        },
        'db_path': './cache/chunks_db.json' # 数据库路径
    }
}
```

### 输出

**TextChunk 对象：**
```python
TextChunk(
    index=0,                    # 分块索引
    content="分块文本内容",      # 分块内容
    start_pos=0,                # 起始位置
    end_pos=500,                # 结束位置
    metadata={                  # 元数据
        'source': 'doc.pdf',
        'chunk_index': 0
    }
)
```

**分块记录 (ChunkRecord)：**
```python
{
    'chunk_id': '/path/to/file.pdf#0',
    'content': '分块内容...',
    'source_file': '/path/to/file.pdf',
    'chunk_index': 0,
    'start_pos': 0,
    'end_pos': 500,
    'metadata': {...},
    'created_at': '2024-01-15T12:00:00'
}
```

---

## 参数配置

### 完整配置示例

```yaml
# configs.yaml
chunker:
  # 分块策略
  strategy: "recursive"
  
  # 分块大小
  chunk_size: 500
  
  # 分块重叠长度
  chunk_overlap: 50
  
  # 分隔符列表（中文优化）
  separators:
    - "\n\n"  # 段落
    - "\n"    # 换行
    - "。"     # 句号
    - "；"    # 分号
    - "，"    # 逗号
    - " "     # 空格
    - ""      # 字符
  
  # 后处理配置
  post_process:
    filter_short_chunks: true
    min_chunk_length: 20
    merge_adjacent_short: true
  
  # 数据库配置
  db_path: "./cache/chunks_db.json"
```

### 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `strategy` | string | "recursive" | 分块策略，目前仅支持 recursive |
| `chunk_size` | int | 500 | 每个分块的最大字符数（100-2000） |
| `chunk_overlap` | int | 50 | 相邻分块之间的重叠字符数（0-200） |
| `separators` | list | [...] | 分块分隔符列表，按优先级排序 |
| `post_process.filter_short_chunks` | bool | true | 是否过滤过短的分块 |
| `post_process.min_chunk_length` | int | 20 | 最小分块长度阈值 |
| `post_process.merge_adjacent_short` | bool | true | 是否合并相邻的短分块 |
| `db_path` | string | "./cache/chunks_db.json" | 分块数据库文件路径 |

---

## 使用示例

### 基本使用

```python
from src.chunkers import RecursiveChunker

# 创建分块器
chunker = RecursiveChunker()

# 分块文本
text = "这是第一段。这是第二段。这是第三段。"
chunks = chunker.split(text)

for chunk in chunks:
    print(f"[{chunk.index}] {chunk.content}")
```

### 带元数据的分块

```python
chunks = chunker.split(
    text,
    metadata={'source': 'document.pdf', 'page': 1}
)
```

### 使用分块管理器

```python
from src.chunkers import ChunkManager

# 创建分块管理器
manager = ChunkManager(config)

# 检查文件是否已处理
is_processed, file_hash = manager.check_file_processed('/path/to/file.pdf')

if not is_processed:
    # 分块文本
    chunks = chunker.split(text)
    
    # 存储分块
    records = manager.store_chunks(
        file_path='/path/to/file.pdf',
        chunks=chunks,
        file_hash=file_hash,
        metadata={'processed_at': '2024-01-15'}
    )
```

### 获取文件分块

```python
# 获取指定文件的所有分块
chunks = manager.get_file_chunks('/path/to/file.pdf')

for chunk in chunks:
    print(f"[{chunk.chunk_index}] {chunk.content[:50]}...")
```

### 获取统计信息

```python
stats = manager.get_stats()
print(f"总分块数: {stats['total_chunks']}")
print(f"总文件数: {stats['total_files']}")
```

---

## 扩展开发

### 添加新的分块策略

```python
# src/chunkers/token_chunker.py
from typing import List, Optional, Dict, Any
from .base import BaseChunker, TextChunk

class TokenChunker(BaseChunker):
    """基于Token数量的分块器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.max_tokens = self.config.get('max_tokens', 256)
        self.tokenizer = self._load_tokenizer()
    
    def split(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[TextChunk]:
        """按Token数量分块"""
        tokens = self.tokenizer.encode(text)
        chunks = []
        
        for i in range(0, len(tokens), self.max_tokens):
            token_chunk = tokens[i:i + self.max_tokens]
            content = self.tokenizer.decode(token_chunk)
            
            chunk = TextChunk(
                index=len(chunks),
                content=content,
                start_pos=i,
                end_pos=min(i + self.max_tokens, len(tokens)),
                metadata=metadata or {}
            )
            chunks.append(chunk)
        
        return chunks
    
    def _load_tokenizer(self):
        # 加载分词器
        from transformers import AutoTokenizer
        return AutoTokenizer.from_pretrained('bert-base-chinese')
```

### 注册到模块

```python
# src/chunkers/__init__.py
from .token_chunker import TokenChunker

__all__ = [
    # ... 其他导出
    "TokenChunker",
]
```

### 在配置中添加

```yaml
# configs.yaml
chunker:
  strategy: "token"  # 使用新的分块策略
  
  token:
    max_tokens: 256
    model_name: "bert-base-chinese"
```

---

## 注意事项

1. **分块大小选择**：
   - 太小（<300）：语义信息不足，检索效果差
   - 太大（>800）：包含过多无关信息，影响精度
   - 推荐：500-600字符

2. **重叠长度选择**：
   - 太小（<30）：语义断裂
   - 太大（>100）：冗余信息过多
   - 推荐：50-100字符

3. **分隔符优先级**：
   - 确保分隔符按从粗到细的顺序排列
   - 中文文档建议保留中文标点

4. **数据库文件**：
   - 定期清理数据库文件，避免过大
   - 备份重要数据

5. **增量更新**：
   - 文件内容修改后会重新分块
   - 文件名修改会被视为新文件
