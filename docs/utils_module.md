# Utils 模块详细说明文档

## 目录
1. [模块概述](#模块概述)
2. [文件结构](#文件结构)
3. [核心类与接口](#核心类与接口)
4. [增量更新追踪器](#增量更新追踪器)
5. [输出管理器](#输出管理器)
6. [交互式配置](#交互式配置)
7. [使用示例](#使用示例)

---

## 模块概述

Utils 模块是文档 RAG 系统的通用工具组件，提供：
- 日志管理（结构化日志、多级别输出）
- 文件工具（文件扫描、路径处理）
- 增量更新追踪（文件哈希/时间戳记录）
- 输出管理（中间结果保存）
- 交互式配置（命令行配置向导）

---

## 文件结构

```
src/utils/
├── __init__.py              # 模块导出
├── logger.py                # 日志管理器
├── file_utils.py            # 文件工具类
├── incremental_tracker.py   # 增量更新追踪器
├── output_manager.py        # 输出管理器
└── interactive_config.py    # 交互式配置模块
```

---

## 核心类与接口

### 1. Logger (logger.py)

日志管理器，支持结构化日志和多级别输出。

```python
def get_logger(name: str) -> logging.Logger

def setup_logging(
    level: str = "INFO",
    format_type: str = "structured",
    log_file: Optional[str] = None,
    console_output: bool = True,
    console_level: Optional[str] = None
)
```

### 2. FileUtils (file_utils.py)

文件工具类，提供文件扫描和路径处理功能。

```python
class FileUtils:
    @staticmethod
    def list_files(
        directory: Union[str, Path],
        extensions: Optional[List[str]] = None,
        recursive: bool = True
    ) -> List[Path]
    
    @staticmethod
    def ensure_dir(path: Union[str, Path]) -> Path
    
    @staticmethod
    def get_file_hash(file_path: Union[str, Path], algorithm: str = 'md5') -> str
```

### 3. IncrementalTracker (incremental_tracker.py)

增量更新追踪器，记录文件哈希和时间戳，支持增量处理。

```python
class IncrementalTracker:
    def __init__(self, config: Optional[Dict[str, Any]] = None)
    
    def filter_files(self, file_paths: List[Union[str, Path]]) -> Tuple[List[Path], Dict[str, Any]]
    
    def update_record(self, file_path: Union[str, Path])
    
    def is_file_changed(self, file_path: Union[str, Path]) -> bool
    
    def get_stats(self) -> Dict[str, Any]
    
    def clear_records()
```

### 4. OutputManager (output_manager.py)

输出管理器，统一管理各阶段的中间结果输出。

```python
class OutputManager:
    def __init__(self, config: Optional[Dict[str, Any]] = None)
    
    def save_loaded_document(self, filename: str, content: str, metadata: Dict[str, Any])
    
    def save_cleaned_text(self, filename: str, original_content: str, cleaned_content: str, metadata: Dict[str, Any])
    
    def save_chunks(self, filename: str, chunks: List[Dict[str, Any]])
    
    def save_dedup_report(self, report: Dict[str, Any])
    
    def save_embeddings(self, filename: str, embeddings: Any, metadata: Dict[str, Any])
    
    def save_retrieval_results(self, query: str, results: List[Dict[str, Any]])
    
    def save_evaluation_report(self, report: Dict[str, Any])
    
    def clean_outputs(self, confirm: bool = False)
    
    def get_output_summary(self) -> Dict[str, Any]
```

### 5. InteractiveConfigurator (interactive_config.py)

交互式配置器，提供命令行配置向导。

```python
class InteractiveConfigurator:
    def __init__(self, config: Dict[str, Any])
    
    def run(self, category: Optional[str] = None) -> Dict[str, Any]

class ConfigItem:
    def __init__(
        self,
        key: str,
        name: str,
        description: str,
        default: Any,
        value_type: str = "string",
        choices: Optional[List[str]] = None,
        validator: Optional[Callable] = None,
        category: str = "general"
    )

def show_current_config(config: Dict[str, Any], format: str = "text")

def get_config_categories() -> List[str]
```

---

## 增量更新追踪器

### 工作原理

增量更新追踪器通过记录文件的哈希值和时间戳，实现只处理新增或修改的文件。

```
扫描文件
  │
  ├─> 1. 计算每个文件的当前哈希
  │
  ├─> 2. 对比记录中的哈希
  │      ├─ 哈希相同 → 跳过（文件未变化）
  │      └─ 哈希不同或不存在 → 需要处理
  │
  └─> 3. 返回需要处理的文件列表
```

### 存储格式

**文件哈希记录** (`cache/file_hashes.json`):
```json
{
  "/path/to/file1.pdf": {
    "hash": "md5_hash_value",
    "timestamp": "2024-01-15T12:00:00"
  },
  "/path/to/file2.docx": {
    "hash": "md5_hash_value",
    "timestamp": "2024-01-15T12:00:00"
  }
}
```

---

## 输出管理器

### 输出目录结构

```
outputs/
├── loaded/                  # 加载的原始文档
│   └── {filename}.txt
├── cleaned/                 # 清洗后的文本
│   └── {filename}.cleaned.txt
├── chunks/                  # 分块结果
│   └── {filename}.chunks.json
├── embeddings/              # Embedding向量
│   ├── {filename}.embeddings.npy
│   └── {filename}.embeddings_meta.json
├── retrieval/               # 检索结果
│   └── {query_hash}.retrieval.json
└── evaluation/              # 评估报告
    └── {timestamp}.eval_report.json
```

### 测试模式 vs 生产模式

| 输出类型 | 测试模式 | 生产模式 |
|---------|---------|---------|
| loaded | 保存 | 不保存 |
| cleaned | 保存 | 不保存 |
| chunks | 保存 | 不保存 |
| dedup_report | 保存 | 保存（监控用） |
| embeddings | 保存 | 不保存 |
| retrieval | 保存 | 保存 |
| evaluation | 保存 | 保存 |

---

## 交互式配置

### 配置分类

| 分类 | 说明 | 包含参数 |
|------|------|---------|
| paths | 路径配置 | input_dir, output_dir, models_dir |
| logging | 日志配置 | level, console_output |
| loader | 文档加载配置 | parallel.enabled, parallel.max_workers, ocr.enabled |
| cleaner | 文本清洗配置 | unstructured.enabled, quality_check.enabled, parallel.enabled |
| chunker | 文本分块配置 | chunk_size, chunk_overlap, post_process.min_chunk_length |
| performance | 性能配置 | max_workers, incremental_update.enabled |

### 配置项类型

- `string`: 字符串输入
- `int`: 整数输入（带范围验证）
- `bool`: 布尔选择（Y/N）
- `choice`: 单选（从列表中选择）
- `path`: 路径输入（自动展开用户目录）

---

## 使用示例

### 日志使用

```python
from src.utils import get_logger, setup_logging

# 设置日志
setup_logging(
    level="INFO",
    format_type="structured",
    log_file="./logs/app.log",
    console_output=True
)

# 获取logger
logger = get_logger(__name__)
logger.info("处理开始")
logger.debug("调试信息")
```

### 文件工具

```python
from src.utils import FileUtils

# 扫描文件
files = FileUtils.list_files(
    directory="./data",
    extensions=[".pdf", ".docx"],
    recursive=True
)

# 确保目录存在
output_dir = FileUtils.ensure_dir("./outputs/cleaned")
```

### 增量更新

```python
from src.utils import IncrementalTracker

# 创建追踪器
tracker = IncrementalTracker(config)

# 筛选需要处理的文件
all_files = FileUtils.list_files("./data")
files_to_process, stats = tracker.filter_files(all_files)

print(f"总文件: {len(all_files)}, 需要处理: {len(files_to_process)}")

# 处理完成后更新记录
for file_path in files_to_process:
    # 处理文件...
    tracker.update_record(file_path)
```

### 输出管理

```python
from src.utils import OutputManager

# 创建输出管理器
output_manager = OutputManager(config)

# 保存加载的文档
output_manager.save_loaded_document(
    filename="document",
    content="文档内容...",
    metadata={"source": "doc.pdf", "parser": "pdf_loader"}
)

# 保存清洗后的文本
output_manager.save_cleaned_text(
    filename="document",
    original_content="原始内容...",
    cleaned_content="清洗后内容...",
    metadata={"pipeline": ["structure", "encoding"]}
)

# 保存分块结果
output_manager.save_chunks(
    filename="document",
    chunks=[
        {"index": 0, "content": "...", "start_pos": 0, "end_pos": 500},
        {"index": 1, "content": "...", "start_pos": 450, "end_pos": 950},
    ]
)
```

### 交互式配置

```python
from src.utils import InteractiveConfigurator, show_current_config

# 创建配置器
configurator = InteractiveConfigurator(current_config)

# 运行交互式配置
new_config = configurator.run()

# 显示当前配置
show_current_config(config, format="yaml")
```

---

## 注意事项

1. **日志级别**：
   - DEBUG: 开发调试使用
   - INFO: 正常运行信息
   - WARNING: 警告信息
   - ERROR: 错误信息

2. **增量更新**：
   - 文件内容修改会触发重新处理
   - 文件名修改会被视为新文件
   - 定期清理哈希记录文件

3. **输出管理**：
   - 测试模式产生大量中间文件，注意磁盘空间
   - 生产环境建议关闭不必要的输出
   - 定期清理输出目录

4. **交互式配置**：
   - 配置会自动保存到 config.yaml
   - 支持部分配置（按分类）
   - 可以预览配置后再保存
