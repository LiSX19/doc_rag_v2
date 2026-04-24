# Pipeline 模块详细说明文档

## 目录
1. [模块概述](#模块概述)
2. [文件结构](#文件结构)
3. [Pipeline执行器](#pipeline执行器)
4. [Pipeline阶段追踪器](#pipeline阶段追踪器)
5. [Pipeline管理器](#pipeline管理器)
6. [处理流程](#处理流程)
7. [断点续传机制](#断点续传机制)
8. [配置参数](#配置参数)
9. [使用示例](#使用示例)

---

## 模块概述

Pipeline 模块是文档 RAG 系统的核心协调组件，负责将各个独立的功能模块（加载、清洗、分块、去重、编码、存储等）串联起来，形成完整的文档处理流水线。

### 主要功能

1. **端到端流程协调**: 协调各模块按正确顺序执行文档处理任务
2. **增量更新支持**: 智能识别已处理/修改/新增文件，避免重复计算
3. **中断恢复（断点续传）**: 全局阶段追踪，支持从中断点恢复（去重、编码存储）
4. **分批编码+即时存储**: 向量化阶段分批次编码并即时写入数据库，中途中断不丢失
5. **进度追踪**: 实时显示处理进度和统计信息
6. **错误隔离**: 单个文件处理失败不影响整体流程

### Pipeline工作流程

```
原始文档 (Raw Documents)
    │
    ├─> 阶段1: 文件发现与筛选
    │      ├─ 扫描输入目录
    │      ├─ 文件格式过滤
    │      ├─ 增量检查（跳过已处理文件）
    │      └─ 文件优先级排序
    │
    ├─> 阶段2: 文件级处理（逐个文件）
    │      ├─ 1️⃣ 文档加载 (Loader)
    │      ├─ 2️⃣ 文本清洗 (Cleaner)
    │      └─ 3️⃣ 文本分块 (Chunker) → 存入分块数据库
    │
    ├─> 阶段3: 全局去重 (Deduper)
    │      ├─ 加载所有分块记录
    │      ├─ SimHash 近似去重
    │      └─ 删除重复分块
    │
    ├─> 阶段4: 向量编码+存储 (Encoder + Vector Store)
    │      ├─ 分批编码（每批32个分块）
    │      ├─ 即时存储到向量数据库
    │      └─ 断点续传：跳过已存储分块
    │
    └─> 阶段5: 结果汇总
           ├─ 统计信息输出
           ├─ 错误日志记录
           └─ 处理报告生成
```

---

## 文件结构

```
src/
├── pipeline.py                  # Pipeline执行器（核心流程执行）
├── pipeline_manager.py          # Pipeline管理器（高级接口和协调）
├── pipeline_stage_tracker.py    # Pipeline全局阶段追踪器（断点续传）
└── pipeline_utils.py            # Pipeline工具函数（统计信息打印）
```

---

## Pipeline执行器

### 1. `build_pipeline()` — 核心执行函数

接收待处理文件列表和所有模块实例，按阶段协调执行完整处理流程：

```python
def build_pipeline(
    files_to_process: List[Path],
    config: Dict[str, Any],
    task_file_manager,
    loader,
    cleaner,
    chunker,
    chunk_manager,
    deduper,
    encoder_manager,
    vector_store,
    output_manager,
    is_ocr: bool = False,
    pipeline_tracker: Optional[PipelineStageTracker] = None,
) -> Dict[str, Any]:
    """
    执行构建知识库的完整流程

    Args:
        files_to_process: 待处理文件列表
        config: 配置字典
        task_file_manager: 任务文件管理器
        loader: 文档加载器
        cleaner: 文本清洗器
        chunker: 文本分块器
        chunk_manager: 分块管理器
        deduper: 去重器
        encoder_manager: 编码管理器
        vector_store: 向量数据库
        output_manager: 输出管理器
        is_ocr: 是否使用OCR清洗
        pipeline_tracker: Pipeline 阶段追踪器（用于断点续传）

    Returns:
        处理统计信息
    """
```

### 2. 核心处理循环 — 阶段1（文件级处理）

```
for file_path in files_to_process:
    │
    ├─ _load_document()      ← 加载文档
    ├─ _clean_text()         ← 文本清洗
    ├─ _chunk_text()         ← 文本分块
    └─ _store_chunks()       ← 保存分块到数据库

单个文件失败 → 记录错误 → 继续下一个文件
```

- 每个文件独立处理，错误隔离
- 每个阶段失败都会记录详细错误（模块、原因、时间戳）
- 实时写入错误日志
- 处理完成后更新 `pipeline_tracker` 到 `STAGE_FILE_PROCESSING`

### 3. `_run_dedup_and_encode()` — 阶段2+3（去重+编码存储）

```python
def _run_dedup_and_encode(
    chunk_manager,
    deduper,
    encoder_manager,
    vector_store,
    stats: Dict[str, Any],
    pipeline_tracker: Optional[PipelineStageTracker] = None,
) -> Dict[str, Any]:
    """执行去重和编码存储阶段（可独立调用，用于中断恢复）"""
```

**关键特性**：
- **恢复智能检测**: 检查 `pipeline_tracker` 当前阶段，如果去重已完成（`STAGE_DEDUP` / `STAGE_ENCODE_STORE`），则跳过去重，直接从数据库统计唯一分块数
- **正常运行时**: 先全局去重，再编码存储

### 4. `_deduplicate_chunks()` — 全局去重

```python
def _deduplicate_chunks(chunk_manager, deduper, stats: Dict) -> Optional[Dict]:
```

执行流程：
1. 加载分块数据库中的所有记录
2. 将记录转换为 `TextChunk` 对象（含进度显示）
3. 调用 `deduper.deduplicate()` 执行 SimHash 近似去重
4. 删除重复分块
5. 返回去重统计（unique_chunks, removed_chunks）

### 5. `_encode_and_store()` — 分批编码存储（支持断点续传）

```python
def _encode_and_store(
    chunk_manager,
    encoder_manager,
    vector_store,
    stats: Dict,
    pipeline_tracker: Optional[PipelineStageTracker] = None,
) -> Optional[Dict]:
    """编码分块并分批存储到向量数据库（支持断点续传）"""
```

**关键特性**：

- **断点续传**: 调用 `vector_store.get_existing_ids()` 获取已存储的 chunk ID，跳过已编码分块
- **分批处理**: 每批 32 个分块，编码后立即 `vector_store.add()`
- **即时持久化**: 每批写入后更新 `pipeline_tracker` 进度，中断不丢失已完成批次
- **最终保存**: 所有批次完成后，保存完整编码结果到 `.npy` 文件

### 6. 辅助函数

```python
def _load_document(loader, file_path, config, progress) -> Optional[Dict]
def _save_loaded_document(output_manager, file_path, document)
def _clean_text(cleaner, document, file_path, is_ocr) -> Optional[str]
def _save_cleaned_document(output_manager, file_path, document, cleaned_text)
def _chunk_text(chunker, cleaned_text, document, file_path) -> Optional[List]
def _save_chunks(output_manager, file_path, chunks)
def _store_chunks(chunk_manager, file_path, chunks)
def _remove_duplicates_from_vector_store(vector_store, removed_chunks)
```

---

## Pipeline阶段追踪器

### 1. `PipelineStageTracker` — 全局阶段追踪

```python
class PipelineStageTracker:
    """Pipeline 全局阶段追踪器"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        # 持久化文件: ./cache/pipeline_stage.json

    def get_stage(self) -> str              # 获取当前阶段
    def get_stats(self) -> Dict[str, Any]   # 获取保存的统计信息
    def set_stage(self, stage, stats=None, batch_id='')  # 设置阶段并持久化
    def is_interrupted(self) -> bool        # 是否在全局阶段中断
    def has_dedup_done(self) -> bool        # 去重是否已完成
    def has_encode_done(self) -> bool       # 编码存储是否已完成
    def clear(self)                         # 重置为 IDLE
```

### 2. 阶段常量

| 常量 | 值 | 说明 |
|------|---|------|
| `STAGE_IDLE` | `'idle'` | 初始/已重置 |
| `STAGE_FILE_PROCESSING` | `'file_processing'` | 文件级处理完成 |
| `STAGE_DEDUP` | `'dedup'` | 全局去重完成 |
| `STAGE_ENCODE_STORE` | `'encode_store'` | 编码存储进行中（每批次更新） |
| `STAGE_COMPLETE` | `'complete'` | 全部完成 |

### 3. 持久化格式 (`pipeline_stage.json`)

```json
{
    "stage": "encode_store",
    "updated_at": "2026-04-24T15:02:52",
    "batch_id": "F:\\doc_rag\\data",
    "stats": {
        "total_files": 13,
        "loaded_files": 13,
        "cleaned_files": 13,
        "chunked_files": 12,
        "total_chunks": 427,
        "encoded_chunks": 64,
        "stored_chunks": 64
    }
}
```

---

## Pipeline管理器

### 1. `PipelineManager` — 高级接口

```python
class PipelineManager:
    """Pipeline管理器，协调各模块完成文档处理"""

    def __init__(self, config: ConfigManager):
        # 初始化配置、输出管理器、日志管理器
        # 所有模块均为懒加载
```

### 2. 懒加载属性

| 属性 | 模块 | 类型 |
|------|------|------|
| `loader` | 文档加载器 | `DocumentLoader` |
| `cleaner` | 文本清洗器 | `TextCleaner` |
| `chunker` | 文本分块器 | `RecursiveChunker` |
| `chunk_manager` | 分块管理器 | `ChunkManager` |
| `deduper` | 去重器 | `Deduper` |
| `encoder_manager` | 编码管理器 | `EncoderManager` |
| `vector_store` | 向量数据库 | `ChromaStore` |
| `retriever` | 检索器 | `VectorRetriever` |
| `task_file_manager` | 任务文件管理器 | `TaskFileManager` |
| `incremental_tracker` | 增量更新追踪器 | `IncrementalTracker` |
| `pipeline_tracker` | 全局阶段追踪器 | `PipelineStageTracker` |

### 3. `build_knowledge_base()` — 构建知识库

```python
def build_knowledge_base(
    self,
    input_dir: Optional[str] = None,
    file_limit: Optional[int] = None,
    incremental: bool = True,
    is_ocr: bool = False,
    force_rebuild: bool = False
) -> Dict[str, Any]:
```

**完整流程**:

```
1. 扫描输入目录 → 发现文件
2. 检查向量数据库状态（has_vector_data）
3. 创建任务计划（create_task_plan）
   └─ 实时写入过滤日志
4. 获取待处理文件（get_pending_files）
5. 如果没有待处理文件:
   ├─ 优先检查 pipeline_tracker 中断状态
   │   ├─ 中断中 → 调用 _run_dedup_and_encode() 恢复
   │   └─ 无中断 → 检查向量库是否为空
   │       ├─ 为空 → 重置文件为 PENDING，重新处理
   │       └─ 有数据 → 返回"没有需要处理的文件"
6. 调用 build_pipeline() 执行完整流程
7. 保存增量更新记录
8. 保存错误和过滤日志
```

**恢复逻辑优先级（关键）**:
```
pipeline_tracker 中断恢复 > 向量库为空重置
```
确保中断恢复时不会错误重置已处理的文件。

### 4. `retrieve()` — 检索知识库

```python
def retrieve(
    self,
    query: str,
    top_k: int = 5,
    threshold: Optional[float] = None
) -> Dict[str, Any]:
    """
    检索知识库
    Args:
        query: 查询问题
        top_k: 返回结果数量
        threshold: 相似度阈值过滤
    Returns:
        { status, query, total_results, results: [{ content, score, metadata }] }
    """
```

### 5. `_save_logs()` — 统一日志保存

合并统计数据中的错误和任务文件表中的错误/过滤记录，使用 `ErrorLogger` 和 `FilterLogger` 写入持久化日志文件：

- 错误日志: `./cache/error_log.json`
- 过滤日志: `./cache/filter_log.json`

---

## 处理流程

### 1. 完整处理流程

```python
def complete_pipeline_flow(input_dir: str) -> Dict[str, Any]:
    """完整Pipeline流程示例"""
    # 1. 初始化Pipeline管理器
    manager = PipelineManager()

    # 2. 构建知识库
    build_stats = manager.build_knowledge_base(
        input_dir=input_dir,
        incremental=True,
        file_limit=100
    )

    # 3. 执行检索
    query = "什么是机器学习？"
    result = manager.retrieve(query, top_k=5)
    print(f"查询: {query}")
    for r in result['results']:
        print(f"  [{r['score']:.3f}] {r['content'][:100]}...")

    return build_stats
```

### 2. 增量更新流程

```python
def incremental_update_flow(manager: PipelineManager, new_files_dir: str):
    """增量更新流程"""
    # 首次构建
    first_stats = manager.build_knowledge_base(
        input_dir="./data",
        incremental=False
    )
    print(f"首次构建: {first_stats['total_files']} 个文件")

    # 增量更新（只处理新文件或修改过的文件）
    incremental_stats = manager.build_knowledge_base(
        input_dir="./data",
        incremental=True
    )

    if incremental_stats.get('total_files', 0) > 0:
        print(f"增量更新: {incremental_stats['total_files']} 个文件")
    else:
        print("没有需要更新的文件")
```

---

## 断点续传机制

### 1. 支持的断点场景

| 中断阶段 | 恢复行为 |
|---------|---------|
| 文件处理中 | 重新处理未完成文件（task_file_manager 标记 PROCESSING→PENDING） |
| 文件处理完成 | pipeline_tracker 检测到 `STAGE_FILE_PROCESSING`，进入去重编码 |
| 去重中 | pipeline_tracker 检测到 `STAGE_DEDUP`，跳过去重，直接编码 |
| 编码存储中 | `get_existing_ids()` 检查已存储的分块，跳过已编码批次 |

### 2. 恢复流程图解

```
第一次运行:
文件处理(13/13) → 去重(427→423) → 编码(批次1/14:32) → 批次2/14:64 → ⚡中断
                                         ↓
                               pipeline_stage.json:
                               { stage: "encode_store", stored_chunks: 64 }

第二次运行:
get_pending_files() → 空
pipeline_tracker.get_stage() → "encode_store"
    ↓
⏭️ 跳过去重（数据库 423 个唯一分块）
    ↓
_get_existing_ids() → 64 个已存储
    ↓
只需编码 423-64=359 个分块
    ↓
批次1/12: 32 → 批次2/12: 64 → ... → 批次12/12: 359 ✅
```

### 3. 关键实现细节

```python
# pipeline.py - _run_dedup_and_encode() 恢复检测
current_stage = pipeline_tracker.get_stage()
dedup_already_done = current_stage in (STAGE_DEDUP, STAGE_ENCODE_STORE)

if not dedup_already_done:
    dedup_result = _deduplicate_chunks(...)  # 正常去重
else:
    # 恢复运行：直接统计数据库中的唯一分块数
    all_records = chunk_manager.db.get_all_chunks()
    stats['unique_chunks'] = len(all_records)
    stats['removed_chunks'] = 0

# pipeline.py - _encode_and_store() 断点续传
existing_ids = set(vector_store.get_existing_ids())
records_to_encode = [r for r in all_records
                     if f"{r.source_file}_{r.chunk_index}" not in existing_ids]

# 分批编码，每批即时存储
for batch in batches(records_to_encode, size=32):
    encoded = encoder_manager.encode_chunks(batch)
    vector_store.add(contents=texts, embeddings=embeddings, ...)
    pipeline_tracker.set_stage(STAGE_ENCODE_STORE, progress_stats)
```

---

## 配置参数

### 1. Pipeline 阶段追踪配置

```yaml
# 在 performance.incremental_update 下
performance:
  incremental_update:
    stage_file: "./cache/pipeline_stage.json"   # 阶段追踪持久化文件路径
```

### 2. 其他配置

各模块配置由对应的模块文档定义。Pipeline 模块本身通过 `default_config.yaml` 的以下部分进行配置：

```yaml
paths:
  input_dir: ./data                    # 默认输入目录
  output_dir: ./outputs                # 输出目录（加载/清洗/分块结果）
  cache_dir: ./cache                   # 缓存目录（任务文件、阶段追踪、日志）

performance:
  incremental_update:
    task_file: "./cache/task_file.json" # 任务文件状态持久化
```

---

## 使用示例

### 1. 基本使用

```python
from src.pipeline_manager import PipelineManager

# 初始化Pipeline管理器
manager = PipelineManager()

# 构建知识库
stats = manager.build_knowledge_base(
    input_dir="./data/documents",
    file_limit=100,
    incremental=True,
    is_ocr=False
)

print(f"处理完成: {stats['total_files']} 个文件")
print(f"总分块: {stats['total_chunks']}")
print(f"唯一分块: {stats['unique_chunks']}")
print(f"存储分块: {stats['stored_chunks']}")
print(f"错误数: {len(stats['errors'])}")
```

### 2. 强制重建

```python
stats = manager.build_knowledge_base(
    input_dir="./data",
    force_rebuild=True     # 清除阶段追踪状态，重置所有文件
)
```

### 3. 检索查询

```python
result = manager.retrieve(
    query="什么是机器学习？",
    top_k=5,
    threshold=0.5        # 相似度阈值过滤
)

for r in result['results']:
    print(f"[{r['score']:.3f}] {r['content'][:100]}")
    print(f"  来源: {r['metadata'].get('source', 'unknown')}")
```

### 4. 打印统计信息

```python
from src.pipeline_utils import print_stats

stats = manager.build_knowledge_base(input_dir="./data")
print_stats(stats)
# 输出:
# ============================================================
# 处理完成统计
# ============================================================
# 总文件数: 13
# 成功加载: 13
# 成功清洗: 13
# 成功分块: 12
# 成功去重: 12
# 总分块数: 427
# 唯一分块数: 423
# 去重分块数: 4
# 编码分块数: 423
# 存储分块数: 423
# 去重率: 0.9%
# 错误数: 1
```

### 5. 直接调用 Pipeline

```python
from src.pipeline import build_pipeline
from src.pipeline_stage_tracker import PipelineStageTracker

tracker = PipelineStageTracker(config)

stats = build_pipeline(
    files_to_process=files,
    config=config,
    task_file_manager=task_file_manager,
    loader=loader,
    cleaner=cleaner,
    chunker=chunker,
    chunk_manager=chunk_manager,
    deduper=deduper,
    encoder_manager=encoder_manager,
    vector_store=vector_store,
    output_manager=output_manager,
    is_ocr=False,
    pipeline_tracker=tracker,
)
```
