# 输出控制文档

## 概述

系统支持两种输出模式：**测试模式** 和 **生产模式**，通过配置文件统一管理各模块的输出。

## 配置方式

在 `config.yaml` 中配置（用户配置）或在 `default_config.yaml` 中查看默认配置：

```yaml
# config.yaml (用户配置) 或 default_config.yaml (默认配置)
output:
  # 输出模式: test(测试模式) / production(生产模式) / minimal(最小输出) / custom(自定义)
  mode: "test"
  
  # 各阶段中间产物输出控制（mode为custom时生效）
  # 设置为 true 则输出该阶段产物，false 则不输出
  stages:
    loaded: false      # 加载阶段：输出原始文本
    cleaned: false     # 清洗阶段：输出清洗后的文本
    chunks: false      # 分块阶段：输出分块结果
    dedup_report: true  # 去重阶段：输出去重报告
    embeddings: true   # 向量化阶段：输出编码向量
    retrieval: true    # 检索阶段：输出检索结果
    evaluation: true   # 评估阶段：输出评估报告
  
  # 测试模式配置（输出所有中间产物）
  test:
    save_loaded: true
    save_cleaned: true
    save_chunks: true
    save_dedup_report: true
    save_embeddings: true
    save_retrieval: true
    save_evaluation: true
  
  # 生产模式配置（只输出必要产物）
  production:
    save_loaded: false
    save_cleaned: false
    save_chunks: false
    save_dedup_report: true
    save_embeddings: false
    save_retrieval: false
    save_evaluation: true
  
  # 最小输出模式（几乎不输出中间产物）
  minimal:
    save_loaded: false
    save_cleaned: false
    save_chunks: false
    save_dedup_report: false
    save_embeddings: false
    save_retrieval: false
    save_evaluation: false
```

## 输出目录结构

```
outputs/
├── loaded/          # 加载的原始文档 (.txt)
├── cleaned/         # 清洗后的文本 (.cleaned.txt)
├── chunks/          # 分块结果 (.chunks.json)
├── embeddings/      # 编码向量 (.npy, .json)
├── retrieval/       # 检索结果 (.json)
└── evaluation/      # 评估报告 (.json)
```

## 使用方式

### 1. 自动输出（推荐）

各模块在初始化时自动创建 `OutputManager`，根据配置决定是否保存：

```python
from src.loaders import DocumentLoader
from src.cleaners import TextCleaner
from src.chunkers import RecursiveChunker

# 加载配置
config = {...}  # 从 config.yaml 或 default_config.yaml 读取

# 初始化模块（自动根据配置决定是否输出）
loader = DocumentLoader(config)
cleaner = TextCleaner(config)
chunker = RecursiveChunker(config)

# 使用带保存功能的方法
docs = loader.load_document("doc.pdf")  # 自动保存到 outputs/loaded/
cleaned = cleaner.clean(doc['content'], filename="doc")  # 自动保存到 outputs/cleaned/
chunks = chunker.split_and_save(cleaned, filename="doc")  # 自动保存到 outputs/chunks/
```

### 2. 手动控制输出

```python
from src.utils import OutputManager

# 创建输出管理器
output_manager = OutputManager(config)

# 手动保存
output_manager.save_loaded_document(filename, content, metadata)
output_manager.save_cleaned_text(filename, original, cleaned)
output_manager.save_chunks(filename, chunks)
output_manager.save_dedup_report(report)
output_manager.save_embeddings(filename, embeddings)
output_manager.save_retrieval_results(query, results)
output_manager.save_evaluation_report(report)
```

### 3. 切换模式

```python
# 测试模式（开发调试）
config['output']['mode'] = 'test'

# 生产模式（正式运行）
config['output']['mode'] = 'production'
```

## 各模块输出方法

| 模块 | 普通方法 | 带保存方法 | 输出文件 |
|------|---------|-----------|---------|
| **Loader** | `load_document()` | - | 自动保存到 `loaded/` |
| **Cleaner** | `clean()` | `clean(filename=...)` | `cleaned/` |
| **Chunker** | `split()` | `split_and_save()` | `chunks/` |
| **Deduper** | `deduplicate()` | `deduplicate(filename=...)` | 自动保存报告 |
| **Encoder** | `encode()` | `encode_and_save()` | `embeddings/` |
| **Retriever** | `retrieve()` | `retrieve_and_save()` | `retrieval/` |
| **Evaluator** | `evaluate()` | `evaluate_and_save()` | `evaluation/` |

## 输出文件格式

### 1. 加载的文档 (`loaded/*.txt`)
```
文件: /path/to/doc.pdf
解析器: unstructured_pdf
大小: 12345 字节
================================================================================

[文档内容...]
```

### 2. 清洗后的文本 (`cleaned/*.cleaned.txt`)
```
原始文件: doc
原始长度: 12345 字符
清洗后长度: 12000 字符
清洗步骤: ['structure', 'encoding', 'simplified']
================================================================================

[清洗后的内容...]
```

### 3. 分块结果 (`chunks/*.chunks.json`)
```json
{
  "filename": "doc",
  "chunk_count": 25,
  "timestamp": "20240115_120000",
  "chunks": [
    {
      "index": 0,
      "content": "...",
      "start_pos": 0,
      "end_pos": 500,
      "metadata": {...}
    }
  ]
}
```

### 4. 去重报告 (`dedup_report_*.json`)
```json
{
  "timestamp": "20240115_120000",
  "filename": "doc",
  "strategy": "test",
  "original_count": 100,
  "unique_count": 85,
  "removed_count": 15,
  "stats": {...},
  "duplicate_groups": [...]
}
```

### 5. 编码向量 (`embeddings/*.npy`, `*.json`)
- `.npy`: numpy 数组文件
- `.json`: 元数据文件

### 6. 检索结果 (`retrieval/*.json`)
```json
{
  "query": "什么是机器学习？",
  "result_count": 5,
  "timestamp": "20240115_120000",
  "results": [
    {
      "content": "...",
      "score": 0.95,
      "metadata": {...}
    }
  ]
}
```

### 7. 评估报告 (`eval_report_*.json`)
```json
{
  "timestamp": "20240115_120000",
  "metrics": {
    "faithfulness": 0.85,
    "answer_relevancy": 0.90
  },
  "details": [...],
  "metadata": {...}
}
```

## 生产环境建议

### 1. 配置示例

```yaml
output:
  mode: "production"
  production:
    save_loaded: false      # 不保存，已存入向量库
    save_cleaned: false     # 不保存中间结果
    save_chunks: false      # 不保存，已存入向量库
    save_dedup_report: true # 保存统计信息用于监控
    save_embeddings: false  # 不保存，已存入向量库
    save_retrieval: true    # 保存检索结果用于分析
    save_evaluation: true   # 保存评估报告
```

### 2. 定期清理

```python
from src.utils import OutputManager

output_manager = OutputManager(config)

# 清理所有输出文件
output_manager.clean_outputs(confirm=True)
```

### 3. 监控输出

```python
# 获取输出配置摘要
summary = output_manager.get_output_summary()
print(summary)
# {
#   'mode': 'production',
#   'output_dir': './outputs',
#   'save_flags': {...}
# }
```

## 失败文件记录

### 自动记录

系统会自动记录以下类型的文件问题：

| 类型 | 原因 | 记录位置 |
|------|------|---------|
| **filtered** | 文件大小不足（< 1KB） | `task_files.json` 中的 `filtered` 状态 |
| **error** | 文档处理失败 | `task_files.json` 中的 `error` 状态 |
| **failed_files** | 文档加载失败 | `failed_files` 列表 (DocumentLoader) |

### 获取失败文件

```python
from src.utils.task_file_manager import TaskFileManager, FileStatus

# 获取任务文件管理器
task_manager = TaskFileManager(config)

# 获取统计信息
stats = task_manager.get_statistics()
print(f"处理完成: {stats['completed']} 个")
print(f"处理失败: {stats['error']} 个")
print(f"被过滤: {stats['filtered']} 个")
print(f"被跳过: {stats['skipped']} 个")

# 查看被过滤的文件
for file_key, file_info in task_manager.task_files.items():
    if file_info['status'] == FileStatus.FILTERED.value:
        print(f"文件: {file_info['filename']}")
        print(f"原因: {file_info['error']}")
```

### 从 DocumentLoader 获取失败文件

```python
from src.loaders import DocumentLoader

loader = DocumentLoader(config)

# 批量加载文档
docs = loader.load_documents(file_paths)

# 获取加载失败的文件
failed = loader.get_failed_files()

print(f"加载失败: {len(failed)} 个")

# 查看失败详情
for f in failed:
    print(f"文件: {f['filename']}")
    print(f"原因: {f['reason']}")
    print(f"错误: {f['error']}")
```

### 保存失败文件报告

```python
# 方法1: 通过 DocumentLoader
report_path = loader.save_failed_files_report()
# 输出: outputs/failed_files_report_20240115_120000.json

# 方法2: 通过 OutputManager
output_manager.save_failed_files_report(
    failed_files=loader.get_failed_files()
)
```

### 失败文件报告格式

```json
{
  "timestamp": "2024-01-15T12:00:00",
  "summary": {
    "total_failed": 5
  },
  "failed_files": [
    {
      "file_path": "F:/data/corrupt.pdf",
      "filename": "corrupt.pdf",
      "reason": "load_error",
      "error": "PDF解析失败...",
      "error_type": "ValueError",
      "timestamp": "2024-01-15T12:00:00"
    }
  ]
}
```

### 任务文件表格式

任务文件表 (`task_files.json`) 包含所有文件的处理状态：

```json
{
  "batch_id": "F:\\doc_rag\\data",
  "created_at": "2024-01-15T12:00:00",
  "files": {
    "F:\\doc_rag\\data\\txt\\small.txt": {
      "path": "F:\\doc_rag\\data\\txt\\small.txt",
      "filename": "small.txt",
      "extension": ".txt",
      "hash": "fa86d2175504c21db50714895dca5540",
      "status": "filtered",
      "priority": 1,
      "created_at": "2024-01-15T12:00:00",
      "updated_at": "2024-01-15T12:00:00",
      "error": "文件大小不足: small.txt, 大小: 33 字节 (0.03 KB), 最小要求: 1024 字节 (1.0 KB)",
      "retry_count": 0
    }
  }
}
```

**状态说明：**
- `pending`: 等待处理
- `processing`: 正在处理
- `completed`: 处理完成
- `error`: 处理出错
- `skipped`: 被跳过（未修改）
- `filtered`: 被过滤（大小不足等）

### 清空记录

```python
# 清空所有记录（开始新一轮处理前）
loader.clear_failed_records()
```

## 注意事项

1. **磁盘空间**: 测试模式会产生大量中间文件，注意磁盘空间
2. **性能影响**: 频繁写入文件会影响性能，生产环境建议关闭不必要的输出
3. **数据安全**: 输出文件可能包含敏感信息，注意权限管理
4. **清理策略**: 定期清理旧的输出文件，避免磁盘占满
5. **失败文件报告**: 失败文件报告**总是保存**（不受 output.mode 影响），用于问题排查
