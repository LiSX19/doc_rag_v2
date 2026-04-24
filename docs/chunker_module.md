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
- 支持基于 LangChain 的递归分块策略
- 提供中文优化的分隔符列表
- 实现分块后处理（过滤短块、合并相邻短块）
- 管理分块数据库，支持增量更新
- 集成 OutputManager 实现分块结果的持久化保存

### 分块流程

```
清洗后的文本
    │
    ├─> 1. 文本分块
    │      ├─ RecursiveChunker（基于 LangChain RecursiveCharacterTextSplitter）
    │      │    按分隔符层级递归分割
    │      └─ 返回 TextChunk 列表
    │
    ├─> 2. 后处理
    │      ├─ 过滤过短的分块
    │      ├─ 合并相邻的短分块
    │      └─ 返回处理后的分块列表
    │
    ├─> 3. (可选) 保存分块结果文件
    │      └─ OutputManager.save_chunks() → outputs/chunks/{filename}.chunks.json
    │
    └─> 4. 存储到数据库
           ├─ 计算文件哈希
           ├─ 存储分块记录（含 content_hash）
           └─ 支持增量更新检查
```

---

## 文件结构

```
src/chunkers/
├── __init__.py              # 模块导出
├── base.py                  # 基础分块器抽象类 & TextChunk
├── recursive_chunker.py     # 递归分块器实现（依赖 langchain_text_splitters）
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
│ - 基于 LangChain RecursiveCharacterTextSplitter              │
│ - 中文优化分隔符列表                                          │
│ - 支持重叠分块                                                │
│ - 集成 OutputManager 保存分块结果                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 核心类与接口

### 1. TextChunk (base.py)

文本分块数据类（普通类，非 dataclass）。

```python
class TextChunk:
    def __init__(
        self,
        content: str,                     # 块内容
        index: int,                       # 块索引
        metadata: Optional[Dict] = None,  # 元数据
        start_pos: int = 0,              # 在原文中的起始位置
        end_pos: int = 0                 # 在原文中的结束位置
    )

    def to_dict(self) -> Dict[str, Any]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TextChunk'
```

### 2. BaseChunker (base.py)

所有分块器的抽象基类。

```python
class BaseChunker(ABC):
    def __init__(self, config: Optional[Dict[str, Any]] = None)

    @abstractmethod
    def split(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[TextChunk]

    def split_batch(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None
    ) -> List[List[TextChunk]]
```

**`split_batch`**：批量分割文本，内部遍历调用 `split()` 方法。

### 3. RecursiveChunker (recursive_chunker.py)

递归分块器实现，基于 LangChain 的 `RecursiveCharacterTextSplitter`。

```python
class RecursiveChunker(BaseChunker):
    def __init__(self, config: Optional[Dict[str, Any]] = None)

    def split(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[TextChunk]

    def split_and_save(
        self,
        text: str,
        filename: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[TextChunk]

    def _post_process(self, chunks: List[TextChunk]) -> List[TextChunk]
```

**`split_and_save`**：分割文本并通过 `OutputManager.save_chunks()` 保存分块结果为 JSON 文件。

### 4. ChunkRecord (chunk_manager.py)

分块记录数据类，用于数据库存储。

```python
class ChunkRecord:
    def __init__(
        self,
        chunk_id: str,                    # 分块唯一ID
        content: str,                     # 分块内容
        source_file: str,                 # 源文件路径
        chunk_index: int,                 # 分块在文件中的索引
        start_pos: int = 0,              # 在原文中的起始位置
        end_pos: int = 0,                # 在原文中的结束位置
        metadata: Optional[Dict] = None,
        created_at: Optional[str] = None,
        content_hash: Optional[str] = None  # 内容哈希值（自动计算）
    )

    def to_dict(self) -> Dict[str, Any]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChunkRecord'

    def compute_hash(self) -> str  # 基于 MD5 计算内容哈希
```

### 5. FileChunkRecord (chunk_manager.py)

文件分块记录数据类。

```python
class FileChunkRecord:
    def __init__(
        self,
        file_path: str,                   # 文件路径
        file_hash: str,                   # 文件内容哈希值
        chunk_ids: List[str],             # 该文件对应的分块ID列表
        processed_at: Optional[str] = None,
        metadata: Optional[Dict] = None
    )

    def to_dict(self) -> Dict[str, Any]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FileChunkRecord'
```

### 6. ChunkDatabase (chunk_manager.py)

分块数据库，JSON 文件存储。

```python
class ChunkDatabase:
    def __init__(self, db_path: Union[str, Path])

    def add_chunks(self, chunks: List[ChunkRecord], file_record: FileChunkRecord)

    def get_chunks_by_file(self, file_path: str) -> List[ChunkRecord]

    def get_file_record(self, file_path: str) -> Optional[FileChunkRecord]

    def delete_file_chunks(self, file_path: str) -> bool

    def check_file_hash(self, file_path: str, current_hash: str) -> bool

    def get_all_file_paths(self) -> Set[str]

    def get_all_chunks(self) -> List[ChunkRecord]

    def get_stats(self) -> Dict[str, Any]

    def update_chunks(self, chunks: List[ChunkRecord])

    def delete_chunks_by_ids(self, chunk_ids: List[str])
```

**新增方法说明：**

| 方法 | 说明 |
|------|------|
| `get_all_file_paths()` | 获取所有已记录的文件路径集合 |
| `get_all_chunks()` | 获取所有分块记录 |
| `update_chunks(chunks)` | 更新分块记录（用于标记重复分块等场景） |
| `delete_chunks_by_ids(ids)` | 按 ID 列表删除分块，同时更新关联的文件记录 |

### 7. ChunkManager (chunk_manager.py)

分块管理器，负责分块的存储和增量更新，内部持有 `ChunkDatabase` 实例。

```python
class ChunkManager:
    def __init__(self, config: Optional[Dict[str, Any]] = None)

    def compute_file_hash(self, file_path: Union[str, Path], algorithm: str = 'md5') -> str

    def compute_content_hash(self, content: str, algorithm: str = 'md5') -> str

    def check_file_processed(
        self,
        file_path: Union[str, Path],
        content: Optional[str] = None
    ) -> Tuple[bool, str]

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

---

## 分块策略

### 递归分块 (RecursiveChunker)

递归分块器基于 LangChain 的 `RecursiveCharacterTextSplitter` 实现，按分隔符层级递归分割文本，优先使用高级别分隔符，如果分块仍然过大，则使用低级别分隔符继续分割。

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
  ├─> 传入 LangChain RecursiveCharacterTextSplitter
  │      ├─ 按 separators 列表递归分割
  │      ├─ 每个片段 <= chunk_size → 保留
  │      └─ 片段 > chunk_size → 使用下一级分隔符继续分割
  │
  ├─> 后处理 (_post_process)
  │      ├─ 过滤过短分块（默认 < 20 字符）
  │      └─ 合并相邻的短分块
  │
  └─> 重新编号并返回 TextChunk 列表
```

#### 重叠分块

相邻分块之间可以设置重叠区域，确保语义连续性：

```
分块1: [内容A + 内容B]
分块2: [内容B + 内容C]  (内容B是重叠部分)
分块3: [内容C + 内容D]  (内容C是重叠部分)
```

重叠由 `chunk_overlap` 参数控制，实际分割由 `RecursiveCharacterTextSplitter` 自动处理。

---

## 分块管理器

### 数据库结构

分块数据库使用 JSON 文件存储，包含三个主要部分：

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
      "created_at": "2024-01-15T12:00:00",
      "content_hash": "md5_of_content"
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
  ├─> 1.