# DocRAG Agent 协作指南

> 本文档面向开发和维护 DocRAG 项目的 AI Agent，提供项目架构、模块关系、开发规范等关键信息。
>
> 用户文档请查看 [README.md](./README.md)

***

## 1. 项目架构概览

### 1.1 核心模块

```
┌─────────────────────────────────────────────────────────────────┐
│                      当前已实现 Pipeline                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Input → [TaskFileManager] → [Loader] → [Cleaner] → [Chunker]    │
│       ↓                                                  ↓       │
│  [Task Files]                                   [Chunk Database] │
│                                                      ↓           │
│  [Encoder] → [VectorStore] ← Build/Update ← [Deduper]           │
│       ↑                                                          │
│  Query → [Retriever] → Output                                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      完整 Pipeline (规划中)                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Input → [TaskFileManager] → [Loader] → [Cleaner] → [Chunker]    │
│       ↓                                                  ↓       │
│  [Task Files]                                   [Chunk Database] │
│                                                      ↓           │
│  [Encoder] → [VectorStore] ← Build/Update ← [Deduper]           │
│       ↑                                                          │
│  Query → [Retriever] → [Reranker] → Output                       │
│                            ↓                                     │
│                       [Evaluator]                                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 模块职责

| 模块              | 路径                   | 职责          | 状态    |
| --------------- | -------------------- | ----------- | ----- |
| **Loader**      | `src/loaders/`       | 文档加载与解析     | ✅ 已完成 |
| **Cleaner**     | `src/cleaners/`      | 文本清洗        | ✅ 已完成 |
| **Chunker**     | `src/chunkers/`      | 文本分块        | ✅ 已完成 |
| **TaskFileManager** | `src/utils/`     | 任务文件表管理     | ✅ 已集成 |
| **Utils**       | `src/utils/`         | 通用工具        | ✅ 已完成 |
| **Pipeline**    | `src/pipeline*.py`   | 流程协调与管理    | ✅ 已集成 |
| **Configs**     | `src/configs/`       | 配置管理        | ✅ 已完成 |
| **Deduper**     | `src/dedupers/`      | 文本去重        | ✅ 已集成 |
| **Encoder**     | `src/encoders/`      | 文本编码与向量生成 | ✅ 已集成 |
| **VectorStore** | `src/vector_stores/` | 向量存储        | ✅ 已集成 |
| **Retriever**   | `src/retrievers/`    | 检索与重排序      | ✅ 已集成 |
| **Evaluator**   | `src/evaluators/`    | 评估          | ⏳ 已实现，未集成 |

***

## 2. 模块详细说明

### 2.1 文档加载器 (Loaders)

**位置**: `src/loaders/`

**详细文档**: [docs/loader\_module.md](./docs/loader_module.md)

**核心文件**:

- `base.py` - 抽象基类 `BaseLoader`
- `loader_factory.py` - 加载器工厂 `LoaderFactory`
- `document_loader.py` - 统一入口 `DocumentLoader`
- `pdf_loader.py`, `word_loader.py`, `excel_loader.py`, `ppt_loader.py`, etc.

**关键接口**:

```python
# 统一入口
from src.loaders import DocumentLoader
loader = DocumentLoader(config)
doc = loader.load_document("path/to/file.pdf")

# 返回格式
{
    'content': str,           # 文档文本内容
    'metadata': {...},        # 元数据（source, size, parser等）
    'pages': [...]            # 分页内容（可选）
}
```

**开发注意**:

- 新格式支持：继承 `BaseLoader`，在 `loader_factory.py` 注册
- 降级策略：优先使用 Unstructured，失败时降级到专用库或 COM
- OCR 处理：PDF 解析失败时自动调用 OCR 子进程

***

### 2.2 文本清洗 (Cleaners)

**位置**: `src/cleaners/`

**详细文档**: [docs/cleaner\_module.md](./docs/cleaner_module.md)

**核心文件**:

- `base.py` - 抽象基类 `BaseCleaner`
- `text_cleaner.py` - 实现类 `TextCleaner`

**清洗流程**:

```
structure → encoding → simplified → custom_rules
```

**关键接口**:

```python
from src.cleaners import TextCleaner
cleaner = TextCleaner(config)
cleaned_text = cleaner.clean(raw_text, filename="doc")
```

**开发注意**:

- 自定义规则在 `src/configs/cleaning_rules.yaml` 配置
- 支持 OCR 模式（额外处理识别错误）

***

### 2.3 文本分块 (Chunkers)

**位置**: `src/chunkers/`

**详细文档**: [docs/chunker\_module.md](./docs/chunker_module.md)

**核心文件**:

- `base.py` - 抽象基类 `BaseChunker`，数据类 `TextChunk`
- `recursive_chunker.py` - 递归分块器 `RecursiveChunker`
- `chunk_manager.py` - 分块管理器 `ChunkManager`，分块数据库 `ChunkDatabase`

**关键接口**:

```python
from src.chunkers import RecursiveChunker, ChunkManager

# 分块
chunker = RecursiveChunker(config)
chunks = chunker.split(text, metadata={...})
# 返回 List[TextChunk]

# 分块管理
manager = ChunkManager(config)
records = manager.store_chunks(file_path, chunks, file_hash)
```

**中文优化分隔符**:

```python
["\n\n", "\n", "。", "；", "，", " ", ""]
```

**开发注意**:

- 分块大小默认 500，重叠 50
- 分块数据库存储在 `cache/chunks_db.json`
- 支持增量更新（通过文件哈希检查）

***

### 2.4 去重 (Dedupers) ✅ 已集成

> **状态**: 已集成到主流程，位于 Chunker 之后

**位置**: `src/dedupers/`

**详细文档**: [docs/deduper\_module.md](./docs/deduper_module.md)

**核心文件**:

- `base.py` - 抽象基类 `BaseDeduper`
- `deduper.py` - 多级去重实现 `Deduper`

**去重策略**:

| 模式 | 策略 |
|------|------|
| `test` | MD5/SHA256 → SimHash |
| `production` | MD5/SHA256 → SimHash → BGE Embedding（TODO） |

**核心方法**:

| 方法 | 说明 |
|------|------|
| `deduplicate(chunks, strategy)` | 多级去重主入口，返回 `(deduplicated_chunks, removed_chunks)` |
| `_hash_deduplicate(chunks)` | 基于 MD5/SHA256 的精确去重 |
| `_simhash_deduplicate(chunks)` | 基于 SimHash 的近似去重（海明距离阈值） |
| `_embedding_deduplicate(chunks)` | 基于 BGE Embedding 的语义去重（TODO，当前为存根） |

**集成位置**: 在 `Chunker` 之后，对所有分块进行全局去重

**持久化**: 哈希表通过 `hash_table_path` 配置持久化到 JSON 文件，支持增量去重

**输出**: 通过 `OutputManager.save_dedup_report()` 保存去重报告到 `outputs/dedup/` 目录

***

### 2.5 编码 (Encoders) ✅ 已集成

> **状态**: 已集成到主流程，并替代了原有的 Embedder 模块

**位置**: `src/encoders/`

**详细文档**: [docs/encoder\_module.md](./docs/encoder_module.md)

**核心文件**:

- `base.py` - 抽象基类 `BaseEncoder`，数据类 `EncodedVector`
- `dense_encoder.py` - 稠密编码器 `DenseEncoder`（基于 BGE 模型）
- `sparse_encoder.py` - 稀疏编码器 `SparseEncoder`（TF-IDF / BM25）
- `hybrid_encoder.py` - 混合编码器 `HybridEncoder`（稠密 + 稀疏组合）
- `encoder_manager.py` - 编码管理器 `EncoderManager`，编码数据库 `EncodingDatabase`

**EncoderManager 核心方法**:

| 方法 | 说明 |
|------|------|
| `encode_dense(texts)` | 稠密编码，返回 `List[EncodedVector]` |
| `encode_sparse(texts)` | 稀疏编码，返回 `List[EncodedVector]` |
| `encode(texts)` | 自动编码（根据配置选择类型），返回 `List[EncodedVector]` |
| `encode_and_store(texts, metadatas)` | 编码并存储到向量数据库（批量操作） |

**支持模型**:

- `BAAI/bge-small-zh-v1.5`（默认，速度快）
- `BAAI/bge-base-zh-v1.5`（精度高）

**编码类型**:

| 类型 | 说明 | 配置值 |
|------|------|--------|
| 稠密编码 | BGE 模型生成固定维度向量 | `dense` |
| 稀疏编码 | TF-IDF / BM25 词袋向量 | `sparse` |
| 混合编码 | 稠密 + 稀疏向量拼接/加权 | `hybrid` |

**编码数据库**: `EncodingDatabase` 提供基于哈希的编码缓存，避免重复编码

**增量编码**: 通过文件哈希检查跳过未变化文件的编码

**输出**: 通过 `OutputManager.save_embeddings()` 保存 `.npy` 向量文件和 `.meta.json` 元数据文件到 `outputs/embeddings/`

***

### 2.6 向量存储 (Vector Stores) ✅ 已集成

> **状态**: 代码已实现，并已集成到主流程

**位置**: `src/vector_stores/`

**详细文档**: [docs/vector\_store\_module.md](./docs/vector_store_module.md)

**核心文件**:

- `base.py` - 抽象基类 `BaseVectorStore`
- `chroma_store.py` - ChromaDB 实现 `ChromaStore`

**集成位置**: 在 `Encoder` 之后，用于存储向量到 Chroma 数据库

**ChromaStore 核心方法**:

| 方法 | 说明 |
|------|------|
| `add(contents, embeddings, metadatas)` | 批量添加向量到集合 |
| `search(query_embedding, top_k)` | 检索最相似的 top_k 个向量 |
| `get_existing_ids()` | 获取已有 ID 列表，用于增量更新去重 |
| `get_stats()` | 获取集合统计信息（总数、维度等） |
| `delete_collection()` | 删除整个集合 |

**配置参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `vector_store.collection_name` | str | `"doc_rag"` | Chroma 集合名称 |
| `vector_store.distance_metric` | str | `"cosine"` | 距离度量：`cosine` / `l2` / `ip` |
| `vector_store.persist_directory` | str | `"./chroma_db"` | 持久化目录路径 |

**索引类型**: 使用 HNSW（Hierarchical Navigable Small World）索引，支持高效的近似最近邻搜索

**使用方式**:

```python
from src.vector_stores import ChromaVectorStore
vector_store = ChromaVectorStore(config)

# 添加向量
vector_store.add(contents=texts, embeddings=embeddings, metadatas=metadatas)

# 检索
results = vector_store.search(query_embedding, top_k=5)

# 增量更新
existing_ids = vector_store.get_existing_ids()
# 过滤已存在的 ID，只添加新的
```

***

### 2.7 检索器 (Retrievers) ✅ 已集成

> **状态**: 代码已实现，并已集成到主流程

**位置**: `src/retrievers/`

**详细文档**: [docs/retriever\_module.md](./docs/retriever_module.md)

**核心文件**:

- `base.py` - 抽象基类 `BaseRetriever`
- `vector_retriever.py` - 向量检索实现 `VectorRetriever`

**集成位置**: 在 `retrieve` 命令中调用，从 `VectorStore` 检索相关内容

**VectorRetriever 核心方法**:

| 方法 | 说明 |
|------|------|
| `retrieve(query, top_k)` | 检索主入口，内部包含编码 + 向量搜索 + 可选重排序 |
| `retrieve_and_save(query, top_k, output_manager)` | 检索并保存结果到文件 |

**处理流程**:

```
query → encode(query) → vector_store.search() → [optional rerank] → results
```

**可选重排序**: 支持通过 CrossEncoder 模型对初次检索结果进行重排序，提高检索精度

**配置参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `retriever.top_k` | int | `5` | 返回结果数量 |
| `retriever.rerank.enabled` | bool | `false` | 是否启用重排序 |
| `retriever.rerank.model` | str | `"BAAI/bge-reranker-base"` | 重排序模型名称 |

**使用方式**:

```python
from src.retrievers import VectorRetriever
retriever = VectorRetriever(config)

# 检索
results = retriever.retrieve(query, top_k=5)

# 检索并保存
retriever.retrieve_and_save(query, top_k=5, output_manager=output_manager)
```

***

### 2.8 评估器 (Evaluators) ⚠️ 代码已实现，未集成

> **状态**: 代码已实现，但未集成到主流程（CLI）

**位置**: `src/evaluators/`

**详细文档**: [docs/evaluator\_module.md](./docs/evaluator_module.md)

**核心文件**:

- `base.py` - 抽象基类 `BaseEvaluator`
- `ragas_evaluator.py` - RAGAS 评估实现 `RAGASEvaluator`

**RAGASEvaluator 功能**:

| 功能 | 说明 |
|------|------|
| LLM Provider | 支持 OpenAI API 和本地 Ollama 部署 |
| 评估指标 | 精确率（Precision）、召回率（Recall）、F1 分数 |
| 降级机制 | RAGAS 不可用时自动回退到模拟评估 |
| 报告输出 | 通过 `OutputManager.save_evaluation_report()` 保存评估报告 |

**配置参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `evaluator.provider` | str | `"openai"` | LLM 提供者：`openai` / `ollama` |
| `evaluator.model` | str | `"gpt-4o-mini"` | 评估用模型名称 |
| `evaluator.metrics` | list | `["precision", "recall", "f1"]` | 评估指标列表 |

**降级策略**: 当 RAGAS 库或 LLM 服务不可用时，`evaluate_retrieval()` 自动降级为基于关键词匹配的模拟评估，确保核心流程不因评估模块故障而中断

**集成位置**: 用于评估检索和生成质量，目前可通过API调用，但未集成到CLI命令

**使用方式**:

```python
from src.evaluators import RAGASEvaluator
evaluator = RAGASEvaluator(config)

# 评估检索结果
metrics = evaluator.evaluate_retrieval(query, retrieved_docs, reference_docs)
# 返回: {"precision": 0.85, "recall": 0.78, "f1": 0.81}
```

***

### 2.9 工具模块 (Utils)

**位置**: `src/utils/`

**详细文档**: [docs/utils\_module.md](./docs/utils_module.md)

**核心文件**:

- `logger.py` - 日志管理 `get_logger()`, `setup_logging()`
- `file_utils.py` - 文件工具 `FileUtils`
- `incremental_tracker.py` - 增量追踪 `IncrementalTracker`
- `task_file_manager.py` - 任务文件表管理 `TaskFileManager`
- `output_manager.py` - 输出管理 `OutputManager`
- `interactive_config.py` - 交互式配置 `InteractiveConfigurator`

**关键接口**:

```python
from src.utils import (
    get_logger, setup_logging,
    FileUtils, OutputManager,
    IncrementalTracker, TaskFileManager,
    InteractiveConfigurator
)
```

**TaskFileManager 功能**:

- 创建任务文件表，记录所有待处理文件
- 跟踪文件处理状态（pending/processing/completed/error/skipped/filtered）
- 支持按文件类型优先级排序处理
- 文件大小过滤（默认 < 1KB 的文件会被过滤）
- 断点续传支持

```python
from src.utils.task_file_manager import TaskFileManager, FileStatus

task_manager = TaskFileManager(config)

# 创建任务计划
task_manager.create_task_plan(
    file_paths=all_files,
    batch_id="batch_001",
    incremental_tracker=incremental_tracker
)

# 获取待处理文件（按优先级排序）
pending_files = task_manager.get_pending_files(sort_by_priority=True)

# 更新文件状态
task_manager.update_file_status(file_path, FileStatus.COMPLETED)

# 获取统计信息
stats = task_manager.get_statistics()
# {'total': 23, 'pending': 0, 'processing': 0, 'completed': 20, 
#  'error': 1, 'skipped': 1, 'filtered': 1}
```

***

### 2.10 Pipeline协调模块

**位置**: `src/pipeline.py`, `src/pipeline_manager.py`, `src/pipeline_utils.py`

**核心文件**:

- `pipeline_manager.py` - Pipeline管理器 `PipelineManager`
- `pipeline.py` - 实际执行各个处理阶段的函数
- `pipeline_utils.py` - 管道相关工具函数

**主要功能**:

- `PipelineManager`: 协调各模块完成文档处理流程，提供`build_knowledge_base()`和`retrieve()`方法
- `pipeline`模块: 包含`build_pipeline()`函数，实际执行文件处理、去重、编码和存储
- `pipeline_utils`: 提供统计信息打印等辅助功能

**关键接口**:

```python
from src.pipeline_manager import PipelineManager
from src.pipeline import build_pipeline

# 使用PipelineManager（推荐）
pipeline = PipelineManager(config)
stats = pipeline.build_knowledge_base(input_dir="./data")

# 直接使用pipeline函数
result = build_pipeline(
    files_to_process=files,
    config=config,
    task_file_manager=task_manager,
    loader=loader,
    cleaner=cleaner,
    chunker=chunker,
    chunk_manager=chunk_manager,
    deduper=deduper,
    encoder_manager=encoder_manager,
    vector_store=vector_store,
    output_manager=output_manager
)
```

**架构设计**:

1. **PipelineManager**: 高层接口，负责模块初始化和流程协调
2. **build_pipeline**: 核心处理逻辑，执行具体的文档处理步骤
3. **模块懒加载**: PipelineManager中的模块按需初始化，提高性能
4. **错误隔离**: 单个文件处理失败不影响其他文件
5. **增量更新支持**: 通过IncrementalTracker和TaskFileManager实现

***

### 2.11 配置管理 (Configs)

**位置**: `src/configs/`

**详细文档**: [docs/config.md](./docs/config.md)

**核心文件**:

- `config_manager.py` - 配置管理器 `ConfigManager`
- `default_config.yaml` - 完整默认配置（只读）
- `cleaning_rules.yaml` - 清洗规则配置

**配置优先级**:

```
命令行 --config > ./config.yaml > src/configs/default_config.yaml
```

**关键接口**:

```python
from src.configs import ConfigManager

config = ConfigManager(config_path=None)
value = config.get('chunker.chunk_size', default=500)
config.set('paths.input_dir', './data')
```

***

## 3. 主程序入口

**位置**: `src/main.py`

**核心类**:

- `PipelineManager` - 处理流程管理与协调
- `pipeline`模块 - 实际执行各个处理阶段
- `PipelineUtils` - 管道相关工具函数

**CLI 命令**:

```bash
python -m src.main [command] [options]

Commands:
  build       构建知识库（加载→清洗→分块→去重→编码→存储）
  retrieve    检索知识库（查询→编码→向量搜索→返回结果）
  evaluate    评估系统 ⚠️ 未实现
  init        初始化项目
  status      显示状态
  clean       清理缓存
  export      导出数据库 ⚠️ 未实现
```

**当前实现的处理流程 (build)**:

```python
# PipelineManager.build_knowledge_base()
1. scan_files()              # 扫描文件
2. task_file_manager.create_task_plan()  # 创建任务文件表（支持增量更新）
3. 对于每个待处理文件:
   - loader.load_document()  # 加载
   - cleaner.clean()         # 清洗
   - chunker.split()         # 分块
   - chunk_manager.store_chunks()  # 存储到分块数据库
4. 全局 deduper.deduplicate()  # 全局去重
5. encoder_manager.encode_and_store()  # 编码并存储到向量数据库
6. 保存统计报告
```

**当前实现的检索流程 (retrieve)**:

```python
# PipelineManager.retrieve()
1. retriever.retrieve(query)  # 检索（内部包含编码和向量搜索）
2. 应用阈值过滤（如果设置了threshold）
3. 返回格式化结果
```

**规划中但未实现的流程**:

```python
# 检索增强（规划中）
1. 检索增强：
   - retriever.retrieve()     # 检索 ✅ 已实现
   - reranker.rerank()        # 重排序 ⚠️ 未实现

# 评估流程（规划中）
2. 评估时：
   - evaluator.evaluate()     # 评估 ⚠️ 未实现（代码已存在，未集成到CLI）
```

***

## 4. 文件规范

### 4.1 项目结构

```
doc_rag/
├── src/                          # 源代码
│   ├── loaders/                  # 文档加载器
│   ├── cleaners/                 # 文本清洗
│   ├── chunkers/                 # 文本分块
│   ├── dedupers/                 # 去重
│   ├── encoders/                  # 文本编码与向量生成
│   ├── vector_stores/            # 向量存储
│   ├── retrievers/               # 检索
│   ├── evaluators/               # 评估
│   ├── utils/                    # 工具
│   ├── configs/                  # 配置
│   └── main.py                   # 主程序
├── tests/                        # 测试
├── models/                       # 模型文件
├── cache/                        # 缓存
│   ├── chunks_db.json            # 分块数据库
│   ├── file_hashes.json          # 文件哈希记录
│   └── file_timestamps.json      # 文件时间戳
├── logs/                         # 日志
├── docs/                         # 文档
│   ├── loader_module.md
│   ├── cleaner_module.md
│   ├── chunker_module.md
│   ├── utils_module.md
│   ├── config.md
│   ├── config_usage.md
│   ├── output_control.md
│   └── incremental_update.md
├── outputs/                      # 输出目录
├── data/                         # 数据目录
├── config.yaml                   # 用户配置
└── README.md                     # 用户文档
```

### 4.2 中间输出文件

| 阶段        | 文件名格式                          | 位置                    | 状态     |
| --------- | ------------------------------ | --------------------- | -------- |
| 加载        | `{filename}.txt`               | `outputs/loaded/`     | ✅ 已实现 |
| 清洗        | `{filename}.cleaned.txt`       | `outputs/cleaned/`    | ✅ 已实现 |
| 分块        | `{filename}.chunks.json`       | `outputs/chunks/`     | ✅ 已实现 |
| 去重        | `{filename}.dedup_report.json` | `outputs/dedup/`      | ✅ 已实现 |
| 编码向量 | `{filename}.embeddings.npy`    | `outputs/embeddings/` | ✅ 已实现 |
| 向量数据库    | `chroma_db/`                   | `./chroma_db/`        | ✅ 已实现 |
| 检索        | `{query_hash}.retrieval.json`  | `outputs/retrieval/`  | ✅ 已实现 |
| 评估        | `{timestamp}.eval_report.json` | `outputs/evaluation/` | ⏳ 未实现 |

### 4.3 输出控制配置

**配置位置**: `src/configs/default_config.yaml` 中的 `output` 部分

**输出模式**:

| 模式           | 说明                 | 加载  | 清洗  | 分块  | 去重报告 |
| ------------ | ------------------ | --- | --- | --- | ---- |
| `test`       | 测试模式（输出所有中间产物）   | ✅   | ✅   | ✅   | ✅    |
| `production` | 生产模式（只输出必要产物）    | ❌   | ❌   | ❌   | ✅    |
| `minimal`    | 最小输出（几乎不输出中间产物）  | ❌   | ❌   | ❌   | ❌    |
| `custom`     | 自定义（通过 stages 配置） | 可配置 | 可配置 | 可配置 | 可配置  |

**配置示例**:

```yaml
output:
  mode: "custom"  # test/production/minimal/custom
  stages:
    loaded: true      # 输出加载产物
    cleaned: false    # 不输出清洗产物
    chunks: true      # 输出分块产物
    dedup_report: true  # 输出去重报告
```

**CLI 参数**:

```bash
# 使用预设模式
python -m src.main build --output-mode production

# 使用自定义模式，单独控制各阶段
python -m src.main build --output-mode custom --no-output-loaded --output-chunks

# 或简写形式
python -m src.main build -m minimal
python -m src.main build --no-output-loaded --no-output-cleaned
```

***

## 5. 开发规范

### 5.1 模块设计原则

1. **单一职责**: 每个模块只负责一个功能
2. **接口分离**: 通过抽象基类定义接口
3. **依赖注入**: 通过 config 字典注入配置
4. **错误隔离**: 模块错误不影响其他模块

### 5.2 代码规范

```python
# 模块模板
"""
模块简要说明

详细说明...
"""

from typing import Optional, Dict, Any, List
from src.utils import get_logger

logger = get_logger(__name__)


class MyModule:
    """类说明"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        # 读取配置
        self.param = self.config.get('key', default_value)
    
    def process(self, input_data: str) -> Dict[str, Any]:
        """
        处理方法
        
        Args:
            input_data: 输入数据
            
        Returns:
            处理结果
            
        Raises:
            ValueError: 输入无效
        """
        try:
            # 处理逻辑
            result = {...}
            return result
        except Exception as e:
            logger.error(f"处理失败: {e}")
            raise
```

### 5.3 配置读取规范

```python
# 正确：使用 get 方法，提供默认值
chunk_size = self.config.get('chunker.chunk_size', 500)

# 正确：读取嵌套配置
chunker_config = self.config.get('chunker', {})
chunk_size = chunker_config.get('chunk_size', 500)

# 错误：直接访问可能不存在的键
chunk_size = self.config['chunker']['chunk_size']  # 可能 KeyError
```

***

## 6. 修改模块时的检查清单

### 6.1 修改 Loader 模块

- [ ] 是否更新了 `loader_factory.py` 的注册？
- [ ] 是否实现了 `BaseLoader` 的所有抽象方法？
- [ ] 是否处理了降级策略？
- [ ] 返回格式是否符合规范？
- [ ] 是否更新了 [docs/loader\_module.md](./docs/loader_module.md)？

### 6.2 修改 Cleaner 模块

- [ ] 清洗步骤是否正确？
- [ ] 是否支持自定义规则？
- [ ] 是否处理了 OCR 模式？
- [ ] 是否更新了 [docs/cleaner\_module.md](./docs/cleaner_module.md)？

### 6.3 修改 Chunker 模块

- [ ] 分块大小和重叠是否正确？
- [ ] 分隔符列表是否合理？
- [ ] 后处理逻辑是否正确？
- [ ] 分块数据库是否正确更新？
- [ ] 是否更新了 [docs/chunker\_module.md](./docs/chunker_module.md)？

### 6.4 修改 Utils 模块

- [ ] 是否影响了增量更新逻辑？
- [ ] 输出文件路径是否正确？
- [ ] 是否更新了 [docs/utils\_module.md](./docs/utils_module.md)？

### 6.5 修改 Config 模块

- [ ] 是否更新了 `default_config.yaml`？
- [ ] 配置项是否有默认值？
- [ ] 是否更新了 [docs/config.md](./docs/config.md)？

### 6.6 集成状态（Deduper/VectorStore/Retriever）

> ⚠️ 以下模块代码已实现但未集成到主流程

- [ ] 是否在 `main.py` 的 `DocRAGPipeline` 中添加了模块调用？
- [ ] 是否正确处理了模块间的数据传递？
- [ ] 是否更新了模块状态（从"未集成"改为"已完成"）？
- [ ] 是否更新了 AGENTS.md 中的流程图和CLI命令说明？
- [ ] 是否添加了相应的输出目录和文件格式？

***

## 7. 文档维护规范

### 7.1 文档结构

每个模块文档应包含：

1. 模块概述
2. 文件结构
3. 核心类与接口
4. 处理流程/算法
5. 输入与输出
6. 参数配置
7. 使用示例
8. 扩展开发指南

### 7.2 文档同步

修改代码后必须同步更新：

1. 模块详细文档 (`docs/{module}_module.md`)
2. AGENTS.md 中的模块说明
3. README.md 中的用户指南（如影响用户接口）

### 7.3 文档链接

```markdown
# 在 AGENTS.md 中引用模块文档
详细文档: [docs/loader_module.md](./docs/loader_module.md)

# 在模块文档中引用代码
核心文件: `src/loaders/base.py`
```

***

## 8. 调试与测试

### 8.1 日志调试

```python
from src.utils import get_logger, setup_logging

# 开启详细日志
setup_logging(level="DEBUG", console_output=True)
logger = get_logger(__name__)

logger.debug("调试信息")
logger.info("一般信息")
logger.warning("警告")
logger.error("错误")
```

### 8.2 测试文件

- `tests/test_load.py` - 加载测试
- `tests/test_clean.py` - 清洗测试
- `tests/test_chunk.py` - 分块测试

### 8.3 测试数据

测试数据存放在 `data/` 目录，包含各种格式的示例文件。

***

## 9. 常见问题

### Q: 如何添加新的文档格式支持？

A:

1. 在 `src/loaders/` 创建新的加载器类，继承 `BaseLoader`
2. 在 `loader_factory.py` 注册新格式
3. 更新 `src/configs/default_config.yaml` 的 `supported_extensions`
4. 更新 [docs/loader\_module.md](./docs/loader_module.md)

### Q: 如何修改分块策略？

A:

1. 修改 `src/chunkers/recursive_chunker.py` 或创建新分块器
2. 更新配置中的 `chunker.chunk_size` 和 `chunker.chunk_overlap`
3. 更新 [docs/chunker\_module.md](./docs/chunker_module.md)

### Q: 如何添加新的配置项？

A:

1. 在 `src/configs/default_config.yaml` 添加默认值
2. 在模块中通过 `config.get('key', default)` 读取
3. 如需交互式配置，在 `src/utils/interactive_config.py` 添加 `ConfigItem`
4. 更新 [docs/config.md](./docs/config.md)

***

## 10. 版本历史

| 版本    | 日期      | 修改内容        |
| ----- | ------- | ----------- |
| 1.0.0 | 2024-01 | 初始版本，完成核心模块 |

***

## 11. 联系与贡献

- 问题反馈：提交 GitHub Issue
- 代码贡献：提交 Pull Request
- 文档维护：遵循本文档规范

***

**最后更新**: 2026-04-22
