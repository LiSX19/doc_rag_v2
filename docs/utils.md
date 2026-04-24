# Utils 模块文档

## 1. 模块概述

Utils 模块是 DocRAG 项目的工具模块集合，提供日志管理、文件操作、增量追踪、输出管理、进度显示、任务调度等通用功能。各工具模块相互独立，通过统一的配置接口与主流程集成。

### 模块文件结构

```
src/utils/
├── __init__.py              # 模块导出
├── file_utils.py            # 文件操作工具
├── incremental_tracker.py   # 增量更新追踪器
├── interactive_config.py    # 交互式配置
├── log_manager.py           # 错误/过滤日志管理
├── logger.py                # 结构化日志系统
├── output_manager.py        # 输出管理
├── progress_tracker.py      # 进度条显示
└── task_file_manager.py     # 任务文件表管理
```

### 导出接口

```python
from src.utils import (
    get_logger,                # 获取结构化日志器
    setup_logging,             # 初始化日志系统
    FileUtils,                 # 文件操作工具类
    OutputManager,             # 输出管理器
    IncrementalTracker,        # 增量更新追踪器
    TaskFileManager,           # 任务文件表管理器
    InteractiveConfigurator,   # 交互式配置器
    ProgressTracker,           # 进度条追踪器
    ErrorLogger,               # 错误日志管理器
    FilterLogger,              # 过滤日志管理器
    show_current_config,       # 显示当前配置
    get_config_categories,     # 获取配置分类
    FileStatus,                # 文件状态枚举
)
```

***

## 2. 日志模块 (logger.py)

### 2.1 概述

基于 `structlog` 库构建的结构化日志系统，支持 JSON 格式输出、分级控制、中文字符编码、控制台与文件分离配置。

### 2.2 核心函数

#### `setup_logging()`

初始化全局日志系统。

```python
def setup_logging(
    level: str = "INFO",
    format_type: str = "json",
    log_file: Optional[str] = None,
    console_output: bool = True,
    console_level: Optional[str] = None,
) -> None
```

**参数说明**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `level` | str | `"INFO"` | 文件日志级别，优先级：CLI > 配置文件 > 默认值 |
| `format_type` | str | `"json"` | 输出格式，支持 `json` / `console` |
| `log_file` | Optional[str] | `None` | 日志文件路径，为 `None` 时不写入文件 |
| `console_output` | bool | `True` | 是否输出到控制台 |
| `console_level` | Optional[str] | `None` | 控制台日志级别，为 `None` 时与 `level` 一致 |

**行为说明**:

- 控制台和文件使用独立的日志级别控制
- 控制台输出经过 `structlog` 格式化（颜色高亮、键值对展示）
- 文件日志输出为 JSON 格式，每条日志为单行 JSON 对象
- 当 `console_output=False` 时，仍会输出 ERROR 级别及以上的日志到控制台（硬编码兜底）

**优先级规则**:

```
CLI 参数 (--log-level, --console-level) > 配置文件 (logging.level, logging.console_level) > 默认值 (INFO)
```

#### `get_logger()`

获取当前模块的结构化日志器。

```python
def get_logger(module_name: str = __name__) -> structlog.stdlib.BoundLogger
```

**参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `module_name` | str | `__name__` | 模块名称，通常传入 `__name__` |

**返回**: `structlog.stdlib.BoundLogger` 实例

**使用示例**:

```python
from src.utils import get_logger

logger = get_logger(__name__)
logger.debug("调试信息", extra_key="value")
logger.info("处理完成", file_count=42, total_size="1.2MB")
logger.warning("配置缺失", key="output.mode")
logger.error("处理失败", file="data.pdf", error="File not found")
```

### 2.3 自定义格式化器

#### `JsonFormatter`

继承 `logging.Formatter`，将结构化日志数据重新序列化为 JSON 字符串，并设置 `ensure_ascii=False` 以支持中文正确显示。

```python
class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        # 1. 使用 structlog 的 JSONRenderer 将记录格式化为 JSON
        # 2. 使用 json.dumps(..., ensure_ascii=False) 重新序列化
        # 3. 确保中文字符正常显示而非 \\uXXXX 转义序列
```

### 2.4 配置示例

```yaml
# config.yaml
logging:
  level: "INFO"              # 文件日志级别
  console_level: "WARNING"   # 控制台日志级别（可选，不设置则与 level 一致）
  console_output: true       # 是否输出到控制台
  format: "json"             # 日志格式：json 或 console
  log_dir: "logs"            # 日志目录
```

### 2.5 日志文件格式

```json
{"event": "处理完成", "file_count": 42, "total_size": "1.2MB", "timestamp": "2026-04-20T10:30:00", "logger": "src.pipeline", "level": "info"}
{"event": "文件处理失败", "file": "data.pdf", "error": "File not found", "timestamp": "2026-04-20T10:30:01", "logger": "src.loaders", "level": "error"}
```

### 2.6 CLI 参数覆盖

```bash
# 设置文件日志级别为 WARNING，控制台日志级别为 ERROR
python -m src.main build --log-level WARNING --console-level ERROR

# 关闭控制台输出
python -m src.main build --no-console-output
```

***

## 3. 文件操作工具 (file_utils.py)

### 3.1 概述

提供文件哈希计算、JSON/Pickle/Text 格式的读写、文件扩展名/名称提取、目录文件递归列举等基础文件操作。

### 3.2 核心类与方法

#### `FileUtils` 工具类

所有方法均为静态方法，无需实例化。

```python
class FileUtils:
    @staticmethod
    def calculate_file_hash(file_path: str, algorithm: str = "md5") -> str
    @staticmethod
    def calculate_content_hash(content: str, algorithm: str = "md5") -> str
    @staticmethod
    def save_json(file_path: str, data: Any, ensure_ascii: bool = False) -> None
    @staticmethod
    def load_json(file_path: str) -> Any
    @staticmethod
    def save_pickle(file_path: str, data: Any) -> None
    @staticmethod
    def load_pickle(file_path: str) -> Any
    @staticmethod
    def save_text(file_path: str, content: str, encoding: str = "utf-8") -> None
    @staticmethod
    def load_text(file_path: str, encoding: str = "utf-8") -> str
    @staticmethod
    def get_file_extension(file_path: str) -> str
    @staticmethod
    def get_file_name(file_path: str, with_extension: bool = True) -> str
    @staticmethod
    def list_files(directory: str, extensions: Optional[List[str]] = None) -> List[str]
```

#### 方法详细说明

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| `calculate_file_hash` | `file_path` 文件路径, `algorithm` 哈希算法 | str | 计算文件哈希值，支持 `md5` / `sha256` |
| `calculate_content_hash` | `content` 字符串内容, `algorithm` 哈希算法 | str | 计算字符串内容的哈希值 |
| `save_json` | `file_path` 路径, `data` 数据, `ensure_ascii` 是否转义 | None | 保存 JSON 文件，默认不转义中文字符 |
| `load_json` | `file_path` 路径 | Any | 加载 JSON 文件 |
| `save_pickle` | `file_path` 路径, `data` 数据 | None | 保存 Pickle 文件 |
| `load_pickle` | `file_path` 路径 | Any | 加载 Pickle 文件 |
| `save_text` | `file_path` 路径, `content` 内容, `encoding` 编码 | None | 保存文本文件 |
| `load_text` | `file_path` 路径, `encoding` 编码 | str | 读取文本文件 |
| `get_file_extension` | `file_path` 路径 | str | 获取文件扩展名（小写，含点号，如 `.pdf`） |
| `get_file_name` | `file_path` 路径, `with_extension` 是否含扩展名 | str | 获取文件名 |
| `list_files` | `directory` 目录, `extensions` 扩展名过滤列表 | List[str] | 递归列举目录下所有文件 |

### 3.3 使用示例

```python
from src.utils import FileUtils

# 计算文件哈希
file_hash = FileUtils.calculate_file_hash("data/doc.pdf", algorithm="sha256")

# 递归列举所有 PDF 文件
pdf_files = FileUtils.list_files("./data", extensions=[".pdf"])

# JSON 读写（自动创建目录）
FileUtils.save_json("output/report.json", {"files": 42, "status": "ok"})
data = FileUtils.load_json("output/report.json")
```

### 3.4 注意事项

- `save_json` 和 `save_text` 会自动创建目标文件的父目录
- `list_files` 使用 `/` 作为路径分隔符（`Path.as_posix()`）
- 哈希算法仅支持 `md5` 和 `sha256`

***

## 4. 增量更新追踪器 (incremental_tracker.py)

### 4.1 概述

管理文件的处理状态，通过哈希值比对和时间戳记录来判断文件是否需要重新处理，支持断点续传。

### 4.2 核心类

#### `IncrementalTracker`

```python
class IncrementalTracker:
    def __init__(self, config: Optional[Dict[str, Any]] = None)
```

**配置项**:

| 配置键 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `incremental.db_path` | str | `"incremental_db.json"` | 追踪数据库文件路径 |

#### 核心方法

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| `check_file` | `file_path` 文件路径, `file_hash` 哈希值 | `(needs_processing: bool, reason: str, status: str)` | 检查文件是否需要处理。返回 `(是否需要处理, 原因, 状态)` |
| `filter_files` | `file_paths` 文件路径列表 | List[str] | 批量过滤出需要处理的文件 |
| `update_record` | `file_path` 路径, `status` 状态 | None | 更新文件处理状态记录 |
| `get_statistics` | 无 | Dict[str, Any] | 获取处理统计信息 |
| `clear_progress` | 无 | None | 清除所有处理进度 |
| `is_broken_point` | 无 | bool | 检查是否存在断点（之前未完成的任务） |
| `get_break_point` | 无 | str | 获取断点位置（上次中断的文件路径） |

**`check_file` 返回的状态枚举**:

| 状态 | 含义 | needs_processing | reason |
|------|------|-----------------|--------|
| `new` | 新文件，未处理过 | `True` | `"new_file"` |
| `modified` | 文件已修改（哈希值变化） | `True` | `"file_modified"` |
| `unchanged` | 文件未变化 | `False` | `"no_change"` |
| `error_skipped` | 上次处理出错被跳过 | `True` | `"error_skipped"` |

### 4.3 持久化机制

- **文件**: `incremental_db.json`（默认路径，可通过配置修改）
- **记录结构**:

```json
{
  "data/doc.pdf": {
    "file_hash": "abc123...",
    "status": "completed",
    "timestamp": "2026-04-20T10:30:00",
    "error": null
  },
  "data/broken.docx": {
    "file_hash": "def456...",
    "status": "error",
    "timestamp": "2026-04-20T09:00:00",
    "error": "Parser failed"
  }
}
```

### 4.4 使用示例

```python
from src.utils import IncrementalTracker, FileUtils

tracker = IncrementalTracker(config)
all_files = FileUtils.list_files("./data", extensions=[".pdf", ".docx"])

# 过滤出需要处理的文件
files_to_process = tracker.filter_files(all_files)

# 处理文件...
for file_path in files_to_process:
    try:
        # 处理逻辑...
        tracker.update_record(file_path, "completed")
    except Exception as e:
        tracker.update_record(file_path, "error")
        logger.error(f"处理失败: {e}")

# 检查断点续传
if tracker.is_broken_point():
    break_point = tracker.get_break_point()
    logger.info(f"检测到断点，从上一次中断位置继续: {break_point}")

# 获取统计
stats = tracker.get_statistics()
```

***

## 5. 输出管理器 (output_manager.py)

### 5.1 概述

管理文档处理各个阶段的中间产物输出，支持 `test` / `production` / `minimal` / `custom` 四种模式，控制加载、清洗、分块、去重、编码、检索、评估各阶段的文件保存。

### 5.2 核心类

#### `OutputManager`

```python
class OutputManager:
    def __init__(self, config: Optional[Dict[str, Any]] = None)
```

**配置项**:

| 配置键 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `output.mode` | str | `"custom"` | 输出模式，可选 `test` / `production` / `minimal` / `custom` |
| `output.stages.loaded` | bool | `true` | 是否输出加载产物 |
| `output.stages.cleaned` | bool | `true` | 是否输出清洗产物 |
| `output.stages.chunks` | bool | `true` | 是否输出分块产物 |
| `output.stages.dedup_report` | bool | `true` | 是否输出报告 |
| `output.paths.output_dir` | str | `"outputs"` | 输出根目录 |

#### 预设模式

| 模式 | loaded | cleaned | chunks | dedup_report | embeddings | retrieval | evaluation |
|------|--------|---------|--------|-------------|------------|-----------|------------|
| `test` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `production` | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| `minimal` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `custom` | 可配置 | 可配置 | 可配置 | 可配置 | 可配置 | 可配置 | 可配置 |

#### 核心方法

| 方法 | 参数 | 说明 |
|------|------|------|
| `save_loaded_document` | `file_path`, `content`, `metadata` | 保存加载后的文本内容 |
| `save_loaded_documents` | `loaded_docs` | 批量保存加载结果 |
| `save_cleaned_text` | `file_path`, `text`, `metadata` | 保存清洗后的文本 |
| `save_cleaned_texts` | `cleaned_texts` | 批量保存清洗结果 |
| `save_chunks` | `file_path`, `chunks` | 保存分块结果 |
| `save_dedup_report` | `report_data` | 保存报告 |
| `save_embeddings` | `file_path`, `embeddings`, `metadata` | 保存编码向量 |
| `save_retrieval_results` | `query`, `results` | 保存检索结果 |
| `save_evaluation_report` | `report_data` | 保存评估报告 |
| `save_failed_files_report` | `failed_files` | 保存失败文件报告 |
| `clear_output_dir` | 无 | 清除输出目录（确认后操作） |

#### 内部检查方法

| 方法 | 说明 |
|------|------|
| `_should_output(stage_name)` | 检查指定阶段是否应该输出 |

### 5.3 输出文件路径规则

```
outputs/
├── loaded/          # {文件名}.txt
├── cleaned/         # {文件名}.cleaned.txt
├── chunks/          # {文件名}.chunks.json
├── dedup/           # {文件名}.dedup_report.json
├── embeddings/      # {文件名}.embeddings.npy
├── retrieval/       # {查询哈希}.retrieval.json
└── evaluation/      # {时间戳}.eval_report.json
```

### 5.4 使用示例

```python
from src.utils import OutputManager

output_manager = OutputManager(config)

# 使用预设模式
output_manager = OutputManager({"output": {"mode": "test"}})

# 使用自定义模式
output_manager = OutputManager({
    "output": {
        "mode": "custom",
        "stages": {
            "loaded": True,
            "cleaned": False,
            "chunks": True,
            "dedup_report": True
        }
    }
})

# 保存各阶段产物
output_manager.save_loaded_document("data/doc.pdf", "文档内容...", {"source": "doc.pdf"})
output_manager.save_cleaned_text("data/doc.pdf", "清洗后内容...")
output_manager.save_chunks("data/doc.pdf", [{"text": "...", "metadata": {}}])
output_manager.save_dedup_report({"total": 100, "removed": 10})
```

***

## 6. 任务文件表管理 (task_file_manager.py)

### 6.1 概述

管理待处理文件的调度队列，支持文件按类型优先级排序、文件大小过滤、状态跟踪、断点续传、任务统计。

### 6.2 核心枚举

#### `FileStatus`

```python
class FileStatus(Enum):
    PENDING = "pending"         # 待处理
    PROCESSING = "processing"   # 处理中
    COMPLETED = "completed"     # 已完成
    ERROR = "error"             # 出错
    SKIPPED = "skipped"         # 跳过
    FILTERED = "filtered"       # 被过滤（如文件过小）
```

### 6.3 核心类

#### `TaskFileManager`

```python
class TaskFileManager:
    def __init__(self, config: Optional[Dict[str, Any]] = None)
```

**配置项**:

| 配置键 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `task_file.db_path` | str | `"task_files.json"` | 任务数据库路径 |
| `task_file.min_file_size` | int | `1024` | 最小文件大小（字节），小于此值被过滤 |
| `task_file.file_type_priority` | list | `[".pdf", ".docx", ...]` | 文件类型优先级列表 |

**默认文件类型优先级**:

```yaml
file_type_priority:
  - .pdf
  - .docx
  - .doc
  - .xlsx
  - .xls
  - .pptx
  - .ppt
  - .txt
  - .csv
  - .md
  - .html
  - .htm
  - .xml
  - .json
```

#### 核心方法

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| `create_task_plan` | `file_paths`, `batch_id`, `incremental_tracker` | None | 创建任务计划，分析文件状态并初始化任务队列 |
| `get_pending_files` | `sort_by_priority` | List[tuple] | 获取待处理文件列表，按优先级排序 |
| `update_file_status` | `file_path`, `status`, `error_msg` | None | 更新文件处理状态 |
| `get_statistics` | 无 | Dict | 获取任务统计信息 |

**`get_statistics()` 返回格式**:

```python
{
    'total': 23,        # 总文件数
    'pending': 0,       # 待处理
    'processing': 0,    # 处理中
    'completed': 20,    # 已完成
    'error': 1,         # 出错
    'skipped': 1,       # 跳过
    'filtered': 1       # 被过滤
}
```

#### 内部方法

| 方法 | 说明 |
|------|------|
| `_load_task_files()` | 从文件加载任务数据库 |
| `_save_task_files()` | 保存任务数据库到文件 |
| `_get_file_size(file_path)` | 获取文件大小 |
| `_is_valid_file(file_path)` | 检查文件是否有效 |
| `_get_priority(file_path)` | 获取文件类型优先级 |

### 6.4 使用示例

```python
from src.utils import TaskFileManager, FileStatus, IncrementalTracker

task_manager = TaskFileManager(config)
tracker = IncrementalTracker(config)

# 创建任务计划
all_files = ["data/doc1.pdf", "data/doc2.docx", "data/notes.txt"]
task_manager.create_task_plan(
    file_paths=all_files,
    batch_id="batch_001",
    incremental_tracker=tracker
)

# 获取待处理文件（按优先级排序）
pending_files = task_manager.get_pending_files(sort_by_priority=True)
# 返回格式: [("data/doc1.pdf", "pending"), ("data/doc2.docx", "pending"), ...]

# 更新文件状态
for file_path, _ in pending_files:
    try:
        task_manager.update_file_status(file_path, FileStatus.PROCESSING)
        # ... 处理文件 ...
        task_manager.update_file_status(file_path, FileStatus.COMPLETED)
    except Exception as e:
        task_manager.update_file_status(file_path, FileStatus.ERROR, str(e))

# 获取统计
stats = task_manager.get_statistics()
```

***

## 7. 进度条追踪器 (progress_tracker.py)

### 7.1 概述

支持主进度 + 子进度的双层进度条显示，基于 ANSI 转义序列实现控制台进度渲染，支持耗时估算和格式化时间显示。

### 7.2 核心类

#### `ProgressTracker`

```python
class ProgressTracker:
    def __init__(
        self,
        total: int,
        desc: str = "Processing",
        unit: str = "item",
        show_sub_progress: bool = False,
    )
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `total` | int | 必填 | 总任务数 |
| `desc` | str | `"Processing"` | 进度条描述文字 |
| `unit` | str | `"item"` | 计数单位 |
| `show_sub_progress` | bool | `False` | 是否显示子进度条 |

#### 核心方法

| 方法 | 参数 | 说明 |
|------|------|------|
| `update` | `n=1` 步进数 | 更新主进度条 |
| `set_sub_progress` | `current`, `total`, `desc` | 设置子进度条状态 |
| `clear_sub_progress` | 无 | 清除子进度条 |
| `close` | 无 | 关闭进度条，显示最终统计 |
| `_draw` | 无 | 渲染进度条到控制台 |
| `_format_time` | `seconds` | 格式化时间显示 |

### 7.3 显示效果

```
Processing: 100%|████████████████████| 42/42 [00:15<00:00, 2.80item/s]
```

带子进度时：

```
Processing:  50%|████████████        | 21/42 [00:08<00:08, 2.50item/s]
  └─ Processing doc.pdf:  60%|██████▌    | 3/5 [00:03<00:02]
```

### 7.4 使用示例

```python
from src.utils import ProgressTracker

# 基本使用
tracker = ProgressTracker(total=42, desc="Processing", unit="file")
for file in files:
    process_file(file)
    tracker.update()
tracker.close()

# 带子进度
tracker = ProgressTracker(
    total=10, desc="Building", unit="file", show_sub_progress=True
)
for file in files:
    tracker.set_sub_progress(current=0, total=5, desc=f"Processing {file.name}")
    for i in range(5):
        process_step(i)
        tracker.set_sub_progress(current=i + 1, total=5)
    tracker.update()
tracker.close()
```

### 7.5 进度条格式说明

```
{描述}: {百分比}|{进度条}|{当前}/{总数} [{已用时间}<{预估剩余时间}, {速率}{单位}/s]
```

- 进度条使用 `█` 填充，` ` 空白
- 百分比四舍五入到整数
- 时间格式：`时:分:秒` 或 `分:秒`
- 速率单位根据描述中的单位自动拼接

***

## 8. 错误/过滤日志管理 (log_manager.py)

### 8.1 概述

管理处理过程中产生的错误日志和过滤日志，提供结构化存储和批量合并功能。

### 8.2 核心类

#### `ErrorLogger`

管理处理失败的文件记录。

```python
class ErrorLogger:
    def __init__(self, log_dir: str = "logs")
```

| 方法 | 参数 | 说明 |
|------|------|------|
| `append` | `file_path`, `error`, `stage`, `timestamp` | 添加单条错误记录 |
| `merge` | `other_errors` | 批量合并错误记录（去重） |
| `_load()` | 无 | 从文件加载错误日志 |
| `_save()` | 无 | 保存错误日志到文件 |

存储路径: `{log_dir}/error_log.json`

#### `FilterLogger`

管理被过滤的文件记录（如文件过小）。

```python
class FilterLogger:
    def __init__(self, log_dir: str = "logs")
```

| 方法 | 参数 | 说明 |
|------|------|------|
| `append` | `file_path`, `reason`, `timestamp` | 添加单条过滤记录 |
| `merge` | `other_filters` | 批量合并过滤记录（去重） |
| `_load()` | 无 | 从文件加载过滤日志 |
| `_save()` | 无 | 保存过滤日志到文件 |

存储路径: `{log_dir}/filter_log.json`

### 8.3 使用示例

```python
from src.utils import ErrorLogger, FilterLogger

error_logger = ErrorLogger(log_dir="logs")
filter_logger = FilterLogger(log_dir="logs")

# 记录错误
error_logger.append(
    file_path="data/corrupt.pdf",
    error="PDF parsing failed: Invalid header",
    stage="load",
)

# 记录过滤
filter_logger.append(
    file_path="data/empty.txt",
    reason="file_too_small: size=50 bytes < min_size=1024 bytes",
)

# 合并（用于多进程/批量处理场景）
error_logger.merge([
    {"file_path": "data/a.pdf", "error": "...", "stage": "load"},
    {"file_path": "data/b.pdf", "error": "...", "stage": "chunk"},
])
```

***

## 9. 交互式配置 (interactive_config.py)

### 9.1 概述

提供命令行交互式配置功能，通过问答引导用户设置项目配置项。

### 9.2 核心类

#### `ConfigItem`

单个配置项定义。

```python
class ConfigItem:
    def __init__(
        self,
        key: str,
        prompt: str,
        type: str,
        default: Any = None,
        choices: Optional[List[str]] = None,
    )
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `key` | str | 配置键路径，如 `output.mode` |
| `prompt` | str | 提示信息 |
| `type` | str | 配置项类型：`bool` / `choice` / `int` / `path` / `string` |
| `default` | Any | 默认值 |
| `choices` | Optional[List[str]] | 选项列表（仅 `choice` 类型使用） |

**提示方法**:

| 方法 | 说明 |
|------|------|
| `prompt_bool()` | 布尔选择 |
| `prompt_choice()` | 多选一 |
| `prompt_int()` | 整数输入 |
| `prompt_path()` | 路径输入 |
| `prompt_string()` | 字符串输入 |

#### `InteractiveConfigurator`

```python
class InteractiveConfigurator:
    def __init__(self, config: Optional[Dict[str, Any]] = None)
```

| 方法 | 说明 |
|------|------|
| `start()` | 启动交互式配置流程 |

**默认配置项定义**:

| 配置键 | 提示 | 类型 | 默认值 |
|--------|------|------|--------|
| `paths.data_dir` | 数据目录路径 | path | `""` |
| `paths.output_dir` | 输出目录路径 | path | `"outputs"` |
| `output.mode` | 输出模式 | choice | `"custom"` |
| `output.stages.loaded` | 是否输出加载产物 | bool | `True` |
| `output.stages.cleaned` | 是否输出清洗产物 | bool | `True` |
| `output.stages.chunks` | 是否输出分块产物 | bool | `True` |
| `output.stages.dedup_report` | 是否输出去重报告 | bool | `True` |
| `chunker.chunk_size` | 分块大小 | int | `500` |
| `chunker.chunk_overlap` | 分块重叠大小 | int | `50` |
| `logging.level` | 日志级别 | choice | `"INFO"` |
| `logging.console_output` | 是否输出到控制台 | bool | `True` |

### 9.3 使用示例

```python
from src.utils import InteractiveConfigurator

# 启动交互式配置
configurator = InteractiveConfigurator()
config = configurator.start()
# 返回包含所有配置项的字典
```

### 9.4 辅助函数

| 函数 | 说明 |
|------|------|
| `show_current_config(config, categories)` | 格式化显示当前配置，按分类分组展示 |
| `get_config_categories()` | 获取配置项分类（路径配置 / 输出配置 / 分块配置 / 日志配置） |

***

## 10. 模块导出 (__init__.py)

### 10.1 导出内容

```python
from src.utils.incremental_tracker import IncrementalTracker
from src.utils.logger import get_logger, setup_logging
from src.utils.file_utils import FileUtils
from src.utils.output_manager import OutputManager
from src.utils.interactive_config import (
    InteractiveConfigurator,
    show_current_config,
    get_config_categories,
)
from src.utils.log_manager import ErrorLogger, FilterLogger
from src.utils.progress_tracker import ProgressTracker
from src.utils.task_file_manager import TaskFileManager, FileStatus
```

### 10.2 导入方式

```python
# 推荐：统一从 utils 导入
from src.utils import (
    get_logger, setup_logging,
    FileUtils, OutputManager,
    IncrementalTracker, TaskFileManager,
    InteractiveConfigurator, ProgressTracker,
    ErrorLogger, FilterLogger,
    show_current_config, get_config_categories,
    FileStatus,
)
```

***

## 11. 模块间调用关系

```
PipelineManager / main.py
    │
    ├── setup_logging()           # 初始化日志系统
    ├── get_logger()              # 获取日志器
    │
    ├── TaskFileManager           # 创建任务计划
    │   └── IncrementalTracker    # 检查文件是否需要处理
    │
    ├── OutputManager             # 管理各阶段输出
    │   └── FileUtils             # 底层文件读写
    │
    ├── ErrorLogger               # 记录处理错误
    ├── FilterLogger              # 记录过滤信息
    │
    └── ProgressTracker           # 显示处理进度
```

***

## 12. 配置参考

### 完整配置项

```yaml
# 日志配置
logging:
  level: "INFO"              # 日志级别：DEBUG/INFO/WARNING/ERROR
  console_level: null        # 控制台日志级别（可选）
  console_output: true       # 是否输出到控制台
  format: "json"             # 日志格式：json/console
  log_dir: "logs"            # 日志目录

# 输出配置
output:
  mode: "custom"             # 模式：test/production/minimal/custom
  stages:
    loaded: true             # 输出加载产物
    cleaned: false           # 输出清洗产物
    chunks: true             # 输出分块产物
    dedup_report: true       # 输出去重报告

# 增量更新配置
incremental:
  db_path: "cache/incremental_db.json"  # 增量数据库路径

# 任务文件表配置
task_file:
  db_path: "cache/task_files.json"      # 任务数据库路径
  min_file_size: 1024                   # 最小文件大小（字节）

# 分块配置
chunker:
  chunk_size: 500          # 分块大小
  chunk_overlap: 50        # 分块重叠
```

***

## 13. 开发指南

### 13.1 添加新的工具模块

1. 在 `src/utils/` 下创建新模块文件
2. 在 `src/utils/__init__.py` 中导出
3. 遵循统一的配置读取规范：`self.config.get('key', default)`
4. 更新本文档

### 13.2 配置读取规范

```python
# 正确：使用 get 方法，提供默认值
chunk_size = self.config.get('chunker.chunk_size', 500)

# 正确：读取嵌套配置
chunker_config = self.config.get('chunker', {})
chunk_size = chunker_config.get('chunk_size', 500)

# 错误：直接访问可能不存在的键
chunk_size = self.config['chunker']['chunk_size']  # 可能 KeyError
```

### 13.3 日志使用规范

```python
from src.utils import get_logger

logger = get_logger(__name__)

# 使用结构化日志，传递键值对参数
logger.info("处理完成", file_count=42, duration_seconds=15.3)

# 不要使用字符串格式化
logger.info(f"处理完成: {count} 个文件")  # 不推荐
```

***

## 14. 版本历史

| 版本 | 日期 | 修改内容 |
|-----|------|---------|
| 1.0.0 | 2026-04-24 | 初始版本，覆盖全部 9 个工具模块 |

***

**最后更新**: 2026-04-24
