# DocRAG 配置模块文档

## 概述

DocRAG 采用双层配置结构，将默认配置和用户配置分离，便于管理和维护。

## 配置文件结构

```
f:\doc_rag\
├── config.yaml                    # 用户配置（关键参数，通过set命令修改）
└── src\
    └── configs\
        └── default_config.yaml     # 全局默认配置（所有参数，只读）
```

## 配置加载优先级

配置加载遵循**从低到高**的优先级顺序：

```
1. src/configs/default_config.yaml    # 全局默认配置（最低优先级）
2. ./config.yaml                       # 用户配置（覆盖默认值）
3. --config 指定的文件                 # 命令行指定（最高优先级）
```

### 配置合并规则

- **递归合并**：字典类型的配置会递归合并，而非简单替换
- **优先级覆盖**：高优先级的配置值会覆盖低优先级的相同键值

**示例：**

```yaml
# default_config.yaml
loader:
  parallel:
    enabled: true
    max_workers: 2

# config.yaml（用户配置）
loader:
  parallel:
    max_workers: 4

# 最终生效配置
loader:
  parallel:
    enabled: true      # 来自default_config
    max_workers: 4     # 被config.yaml覆盖
```

## 全局默认配置 (default_config.yaml)

### 项目信息

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `project.name` | string | "DocRAG" | 项目名称 |
| `project.version` | string | "1.0.0" | 项目版本 |
| `project.description` | string | "文档RAG系统" | 项目描述 |

### 路径配置

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `paths.input_dir` | string | "./data" | 输入文档目录 |
| `paths.output_dir` | string | "./outputs" | 输出目录 |
| `paths.models_dir` | string | "./models" | 模型文件目录 |
| `paths.logs_dir` | string | "./logs" | 日志文件目录 |
| `paths.cache_dir` | string | "./cache" | 缓存文件目录 |

### 日志配置

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `logging.level` | string | "INFO" | 日志级别(DEBUG/INFO/WARNING/ERROR) |
| `logging.format` | string | "structured" | 日志格式(structured/simple) |
| `logging.file` | string | "./logs/doc_rag.log" | 日志文件路径 |
| `logging.max_size` | string | "100MB" | 单个日志文件最大大小 |
| `logging.backup_count` | int | 3 | 日志备份数量 |
| `logging.console_output` | bool | true | 是否输出到控制台 |

### 文档加载配置 (loader)

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `loader.supported_extensions` | list | [".pdf", ".docx", ...] | 支持的文件扩展名列表 |
| `loader.parallel.enabled` | bool | true | 是否启用并行加载 |
| `loader.parallel.max_workers` | int | 4 | 并行加载线程数 |
| `loader.extract_metadata` | bool | true | 是否提取文档元数据 |
| `loader.filters.min_file_size` | int | 1024 | 最小文件大小(字节) |
| `loader.word.max_retries` | int | 3 | Word加载重试次数 |
| `loader.word.retry_delay` | int | 2 | Word加载重试延迟(秒) |
| `loader.ppt.max_retries` | int | 3 | PPT加载重试次数 |
| `loader.ppt.retry_delay` | int | 2 | PPT加载重试延迟(秒) |
| `loader.rtf.max_retries` | int | 3 | RTF加载重试次数 |
| `loader.rtf.retry_delay` | int | 2 | RTF加载重试延迟(秒) |
| `loader.caj.caj2pdf_dir` | string | "./src/loaders/caj2pdf" | CAJ转换工具目录 |

### OCR配置

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `ocr.enabled` | bool | true | 是否启用OCR功能 |
| `ocr.conda_env` | string | "OCR" | Conda环境名称 |
| `ocr.conda_path` | string | "" | Conda可执行文件路径(留空自动查找) |
| `ocr.progress_callback` | null/function | null | OCR进度回调函数 |

### 文本清洗配置 (cleaner)

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `cleaner.pipeline` | list | ["structure", "encoding", "simplified"] | 清洗流程步骤 |
| `cleaner.custom_rules_file` | string | "./src/configs/cleaning_rules.yaml" | 自定义规则文件路径 |
| `cleaner.quality_check.enabled` | bool | true | 是否启用质量检查 |
| `cleaner.quality_check.min_length` | int | 10 | 最小长度检查阈值 |
| `cleaner.quality_check.max_length_ratio` | float | 0.1 | 最大长度比率阈值 |
| `cleaner.unstructured.enabled` | bool | true | 是否启用Unstructured清洗 |
| `cleaner.unstructured.options.clean_bullets` | bool | true | 清理项目符号 |
| `cleaner.unstructured.options.clean_extra_whitespace` | bool | true | 清理多余空白 |
| `cleaner.unstructured.options.clean_non_ascii_chars` | bool | false | 清理非ASCII字符 |
| `cleaner.unstructured.options.group_broken_paragraphs` | bool | true | 组合断裂段落 |
| `cleaner.unstructured.options.remove_punctuation` | bool | false | 移除标点符号 |
| `cleaner.parallel.enabled` | bool | false | 是否启用并行清洗 |
| `cleaner.parallel.max_workers` | int | 4 | 并行清洗线程数 |

### 文本分块配置 (chunker)

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `chunker.strategy` | string | "recursive" | 分块策略 |
| `chunker.chunk_size` | int | 500 | 每个分块的最大字符数 |
| `chunker.chunk_overlap` | int | 50 | 相邻分块的重叠字符数 |
| `chunker.separators` | list | ["\n\n", "\n", "。", ...] | 分块分隔符列表 |
| `chunker.post_process.filter_short_chunks` | bool | true | 是否过滤短块 |
| `chunker.post_process.min_chunk_length` | int | 20 | 最小分块长度 |
| `chunker.post_process.merge_adjacent_short` | bool | true | 是否合并相邻短块 |
| `chunker.db_path` | string | "./cache/chunks_db.json" | 分块数据库路径 |

### 性能配置 (performance)

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `performance.max_workers` | int | 2 | 系统最大并行工作线程数 |
| `performance.parallel_processing` | bool | true | 是否启用并行处理 |
| `performance.incremental_update.enabled` | bool | true | 是否启用增量更新 |
| `performance.incremental_update.hash_file` | string | "./cache/file_hashes.json" | 文件哈希记录路径 |
| `performance.incremental_update.timestamp_file` | string | "./cache/file_timestamps.json" | 文件时间戳记录路径 |
| `performance.cache.enabled` | bool | true | 是否启用缓存 |
| `performance.cache.type` | string | "disk" | 缓存类型(disk/redis) |
| `performance.cache.disk_path` | string | "./cache" | 磁盘缓存路径 |
| `performance.cache.max_size` | string | "5GB" | 最大缓存大小 |

## 用户配置 (config.yaml)

用户配置只包含**关键参数**，通过 `set` 命令交互式生成。

### 可配置的关键参数

| 分类 | 参数 | 说明 |
|------|------|------|
| paths | `input_dir` | 输入目录 |
| paths | `output_dir` | 输出目录 |
| paths | `models_dir` | 模型目录 |
| logging | `level` | 日志级别 |
| logging | `console_output` | 控制台输出 |
| loader | `parallel.enabled` | 并行加载开关 |
| loader | `parallel.max_workers` | 加载线程数 |
| loader | `ocr.enabled` | OCR开关 |
| cleaner | `unstructured.enabled` | Unstructured清洗开关 |
| cleaner | `quality_check.enabled` | 质量检查开关 |
| cleaner | `parallel.enabled` | 并行清洗开关 |
| chunker | `chunk_size` | 分块大小 |
| chunker | `chunk_overlap` | 分块重叠长度 |
| chunker | `post_process.min_chunk_length` | 最小分块长度 |
| performance | `max_workers` | 最大工作线程数 |
| performance | `incremental_update.enabled` | 增量更新开关 |

## 命令行配置工具

### 交互式配置

```bash
# 配置所有参数
python src/main.py set

# 只配置特定分类
python src/main.py set --category paths
python src/main.py set --category logging
python src/main.py set --category loader
python src/main.py set --category cleaner
python src/main.py set --category chunker
python src/main.py set --category performance
```

### 查看当前配置

```bash
# 文本格式显示
python src/main.py showset

# YAML格式显示
python src/main.py showset --format yaml

# 只显示特定分类
python src/main.py showset --category loader
```

### 使用自定义配置文件

```bash
# 使用自定义配置文件运行
python src/main.py build --config ./my_config.yaml
```

## 配置读取示例

### 在模块中读取配置

```python
from src.configs import ConfigManager

# 初始化配置管理器
config = ConfigManager()

# 获取配置值（支持点号分隔）
input_dir = config.get('paths.input_dir', './data')
chunk_size = config.get('chunker.chunk_size', 500)

# 获取所有配置
all_config = config.get_all()
```

### 在Loader模块中

```python
class DocumentLoader:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # 读取并行配置
        parallel_config = self.config.get('loader', {}).get('parallel', {})
        self.parallel_enabled = parallel_config.get('enabled', True)
        self.max_workers = parallel_config.get('max_workers', 4)
```

### 在Cleaner模块中

```python
class TextCleaner:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # 读取cleaner配置
        cleaner_config = self.config.get('cleaner', self.config)
        self.pipeline = cleaner_config.get('pipeline', ['structure', 'encoding', 'simplified'])
```

### 在Chunker模块中

```python
class RecursiveChunker:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # 读取chunker配置
        chunker_config = self.config.get('chunker', self.config)
        self.chunk_size = chunker_config.get('chunk_size', 500)
```

## 注意事项

1. **不要直接修改 default_config.yaml**：此文件包含所有参数的默认值，升级时可能会被覆盖

2. **使用 set 命令修改配置**：通过 `python src/main.py set` 交互式修改配置，会自动保存到 `config.yaml`

3. **配置优先级**：命令行指定的配置文件 > 用户配置 > 默认配置

4. **递归合并**：配置合并时会递归处理嵌套字典，确保不会丢失默认参数

5. **路径配置**：所有路径都支持相对路径（相对于项目根目录）和绝对路径

6. **日志级别**：生产环境建议使用 `WARNING` 或 `ERROR`，开发环境使用 `DEBUG` 或 `INFO`

7. **并行配置**：根据CPU核心数调整 `max_workers`，建议不超过CPU核心数的2倍
