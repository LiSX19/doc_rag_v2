# Loader 模块详细说明文档

## 目录
1. [模块概述](#模块概述)
2. [文件结构](#文件结构)
3. [核心类与接口](#核心类与接口)
4. [各格式解析流程](#各格式解析流程)
5. [输入与输出](#输入与输出)
6. [优化处理](#优化处理)
7. [参数配置](#参数配置)
8. [使用示例](#使用示例)
9. [扩展开发](#扩展开发)

---

## 模块概述

Loader 模块是文档 RAG 系统的文档加载与解析组件，负责：
- 支持 **18 种文件格式** 的加载与解析
- 提供统一的文档加载接口
- 实现智能降级策略（优先现代库，降级到专用库/COM/子进程）
- 支持并行处理（ProcessPoolExecutor）和进度监控
- 实现错误重试机制和失败文件记录
- 支持增量更新（通过 IncrementalTracker）

### 支持的文件格式

| 类别 | 格式 | 扩展名 | 优先级策略 |
|------|------|--------|-----------|
| PDF | PDF | `.pdf` | Unstructured → OCR子进程 |
| Word | Word 2007+ | `.docx` | Unstructured → python-docx |
| Word | Word 97-2003 | `.doc` | Unstructured → pywin32(COM) |
| Word | WPS | `.wps` | Unstructured → pywin32(COM) |
| Excel | Excel 2007+ | `.xlsx` | Unstructured → openpyxl |
| Excel | Excel 97-2003 | `.xls` | Unstructured → xlrd |
| PowerPoint | PPTX | `.pptx` | Unstructured → python-pptx |
| PowerPoint | PPT | `.ppt` | Unstructured → pywin32(COM) |
| PowerPoint | 幻灯片放映 | `.ppsx` | Unstructured → pywin32(COM) |
| CAJ | CAJ | `.caj` | caj2pdf → PDFLoader |
| 文本 | 纯文本 | `.txt` | Unstructured → 原始读取 |
| 文本 | Markdown | `.md` | Unstructured(md) → 原始读取 |
| 文本 | CSV | `.csv` | 专用CSV处理器 |
| 文本 | JSON | `.json` | 原始读取 |
| 文本 | XML | `.xml` | 原始读取 |
| 文本 | RTF | `.rtf` | pywin32 → Unstructured → 原始读取 |
| 网页 | HTML | `.html` | Unstructured → BeautifulSoup → 原始读取 |
| 网页 | HTML | `.htm` | Unstructured → BeautifulSoup → 原始读取 |

---

## 文件结构

```
src/loaders/
├── __init__.py              # 模块导出
├── base.py                  # 基础加载器抽象类 (BaseLoader)
├── loader_factory.py        # 加载器工厂（注册与获取）+ register_all_loaders()
├── document_loader.py       # 统一文档加载入口
│
├── pdf_loader.py            # PDF 加载器（含OCR子进程）
├── word_loader.py           # Word/WPS 加载器
├── excel_loader.py          # Excel 加载器
├── ppt_loader.py            # PowerPoint 加载器
├── caj_loader.py            # CAJ 加载器
├── html_loader.py           # HTML 加载器
├── text_loader.py           # 文本加载器
├── rtf_loader.py            # RTF 加载器
│
├── ocr_processor.py         # OCR 子进程脚本（在OCR环境中独立运行）
│
└── caj2pdf/                 # caj2pdf 工具（需手动克隆）
    ├── caj2pdf              # 主脚本
    ├── cajparser.py         # CAJ 解析器
    ├── jbig2dec.py          # JBIG2 解码
    └── ...
```

### 文件关系图

```
┌──────────────────────────────────────────────────────────────────┐
│                     DocumentLoader (统一入口)                      │
│  - 并行处理 (ProcessPoolExecutor)                                 │
│  - 进度回调                                                       │
│  - 失败文件记录与报告                                               │
│  - 增量更新 (IncrementalTracker)                                  │
│  - 输出管理 (OutputManager)                                       │
└───────────────────────┬──────────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ LoaderFactory│ │ File Filter  │ │ Progress     │
│ (获取加载器)  │ │ (类型检查)   │ │ (进度回调)   │
└──────┬────────┘ └──────────────┘ └──────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│                      具体加载器实现                                │
├──────────────┬──────────────┬──────────────┬────────────────────┤
│ PDFLoader    │ WordLoader   │ ExcelLoader  │ PPTLoader          │
│ (Unstructured│ (Unstructured│ (Unstructured│ (Unstructured      │
│  → OCR子进程) │ → python-docx│ → openpyxl/ │ → python-pptx      │
│              │  → pywin32)  │   xlrd)      │  → pywin32)        │
├──────────────┼──────────────┼──────────────┼────────────────────┤
│ CAJLoader    │ HTMLLoader   │ TextLoader   │ RTFLoader          │
│ (caj2pdf     │ (Unstructured│ (Unstructured│ (pywin32           │
│  → PDFLoader)│  → BS4)      │  → 原始读取) │  → Unstructured)   │
└──────────────┴──────────────┴──────────────┴────────────────────┘
```

---

## 核心类与接口

### 1. BaseLoader (base.py)

所有加载器的抽象基类。

```python
class BaseLoader(ABC):
    def __init__(self, config: Optional[Dict[str, Any]] = None)

    @abstractmethod
    def load(self, file_path: Union[str, Path]) -> Dict[str, Any]

    @abstractmethod
    def supports(self, file_path: Union[str, Path]) -> bool

    def extract_metadata(self, file_path: Union[str, Path]) -> Dict[str, Any]
```

**extract_metadata 返回字段：**
| 字段 | 类型 | 说明 |
|------|------|------|
| `source` | str | 文件绝对路径 |
| `filename` | str | 文件名（含扩展名） |
| `extension` | str | 文件扩展名（小写） |
| `size_bytes` | int | 文件大小（字节） |
| `created_at` | str | 创建时间（ISO格式） |
| `modified_at` | str | 修改时间（ISO格式） |

### 2. LoaderFactory (loader_factory.py)

加载器注册与获取工厂。

```python
class LoaderFactory:
    @classmethod
    def register(cls, extension: str, loader_class: Type[BaseLoader])

    @classmethod
    def get_loader(cls, file_path, config=None) -> Optional[BaseLoader]

    @classmethod
    def get_supported_extensions(cls) -> List[str]

    @classmethod
    def is_supported(cls, file_path) -> bool

# 便捷函数
def get_loader(file_path, config=None) -> Optional[BaseLoader]

# 注册所有内置加载器
def register_all_loaders()
```

**注册机制：** `register_all_loaders()` 在模块导入时自动调用，注册以下映射：

```python
LoaderFactory.register('.pdf', PDFLoader)
LoaderFactory.register('.docx', WordLoader)
LoaderFactory.register('.doc', WordLoader)
LoaderFactory.register('.wps', WordLoader)
LoaderFactory.register('.xlsx', ExcelLoader)
LoaderFactory.register('.xls', ExcelLoader)
LoaderFactory.register('.pptx', PPTLoader)
LoaderFactory.register('.ppt', PPTLoader)
LoaderFactory.register('.ppsx', PPTLoader)
LoaderFactory.register('.txt', TextLoader)
LoaderFactory.register('.md', TextLoader)
LoaderFactory.register('.csv', TextLoader)
LoaderFactory.register('.json', TextLoader)
LoaderFactory.register('.xml', TextLoader)
LoaderFactory.register('.rtf', RTFLoader)
LoaderFactory.register('.html', HTMLLoader)
LoaderFactory.register('.htm', HTMLLoader)
LoaderFactory.register('.caj', CAJLoader)
```

### 3. DocumentLoader (document_loader.py)

统一文档加载入口，支持并行处理、增量更新和失败记录。

```python
class DocumentLoader:
    def __init__(self, config: Optional[Dict[str, Any]] = None)

    def load_document(self, file_path: Union[str, Path]) -> Dict[str, Any]

    def load_documents(
        self,
        file_paths: List[Union[str, Path]],
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        incremental: bool = True
    ) -> List[Dict[str, Any]]

    def load_directory(
        self,
        directory: Union[str, Path],
        extensions: Optional[List[str]] = None,
        recursive: bool = True,
        file_limit: Optional[int] = None
    ) -> List[Dict[str, Any]]

    def get_supported_extensions(self) -> List[str]
    def is_supported(self, file_path: Union[str, Path]) -> bool

    # 失败文件管理
    def get_failed_files(self) -> List[Dict[str, Any]]
    def save_failed_files_report(self, output_path=None) -> Path
    def clear_failed_records(self)

    # 增量更新管理
    def set_incremental_mode(self, enabled: bool)
    def clear_incremental_records(self)
    def get_incremental_stats(self) -> Dict[str, Any]
```

**并行处理机制：** 使用 `ProcessPoolExecutor`，通过模块级工作函数 `_load_single_document_worker(file_path, config)` 在工作进程中创建新的 `DocumentLoader` 实例执行加载。

**增量更新：** 当 `incremental=True` 时，通过 `IncrementalTracker.filter_files()` 筛选出已变更的文件，只处理新增或修改过的文件。

**输出管理：** 加载成功后通过 `OutputManager.save_loaded_document()` 保存加载产物（根据 `output.mode` 配置决定是否输出）。

---

## 各格式解析流程

### PDF 解析流程 (pdf_loader.py)

```
PDF 文件
    │
    ├─> 1. Unstructured (partition_pdf)
    │      ├─ fast 模式（纯文本，优先尝试）
    │      │   └─ 成功 → 返回结果（含分页内容）
    │      └─ hi_res 模式（复杂布局，含表格推断）
    │          └─ 成功 → 返回结果
    │          └─ 失败且OCR启用 → 继续
    │
    ├─> 2. [内容为空检查] → 扫描版PDF，触发OCR
    │
    └─> 3. OCR 子进程（conda run 或直接调用环境Python）
           │
           ├─> ocr_processor.py
           │    ├─ PyMuPDF (fitz) 转图片 (2x分辨率)
           │    ├─ PaddleOCR 识别（CPU模式）
           │    ├─ CPU线程数控制（通过性能配置）
           │    ├─ 进度汇报（通过JSON进度文件，0.5秒轮询）
           │    └─ 返回文本和分页结果
           │
           └─ conda环境定位
               ├─ 自动查找：常见路径列表 → PATH中查找(where/which)
               └─ 直接调用：从conda路径推导环境Python.exe路径
```

**关键特性：**
- 双环境隔离：主环境(RAG) + OCR环境(OCR)
- 无超时限制：大型 PDF 可完整处理
- 进度汇报：子进程实时汇报处理进度，主进程线程轮询
- conda 自动发现：无需手动配置 conda 路径
- CPU 限制：通过 `performance.max_workers` 控制 OCR 的 CPU 使用

### Word 解析流程 (word_loader.py)

```
.docx 文件                    .doc / .wps 文件
    │                              │
    ├─> Unstructured               ├─> Unstructured
    │   (partition_docx)           │   (partition_doc / partition_doc for .wps)
    │   └─ 成功                    │   └─ 成功
    │                              │
    └─> python-docx                └─> pywin32 (COM)
        └─ 成功                        ├─ 带重试机制（默认3次）
                                       ├─ 资源强制释放
                                       └─ 成功
```

**关键特性：**
- `.wps` 格式使用 `partition_doc` 解析，降级到 pywin32
- 重试机制：RPC 错误（`-2147023170` / `远程过程调用`）自动重试
- 资源释放：`finally` 块确保 COM 对象关闭和垃圾回收
- 配置参数：`loader.word.max_retries`, `loader.word.retry_delay`

### Excel 解析流程 (excel_loader.py)

```
.xlsx 文件                    .xls 文件
    │                              │
    ├─> Unstructured               ├─> Unstructured
    │   (partition_xlsx)           │   (partition_xls)
    │   └─ 成功                    │   └─ 成功
    │                              │
    └─> openpyxl                   └─> xlrd
        └─ 成功（含 sheet 元数据）      └─ 成功（含 sheet 元数据）
```

**关键特性：**
- 降级时提供 `sheet_count` 和 `sheet_names` 元数据
- 每个工作表以 `=== Sheet: {name} ===` 标题分隔
- 行内单元格以 ` | ` 分隔

### PowerPoint 解析流程 (ppt_loader.py)

```
.pptx 文件                    .ppt / .ppsx 文件
    │                              │
    ├─> Unstructured               ├─> Unstructured
    │   (partition_pptx)           │   (partition_ppt)
    │   └─ 成功（含 slides 分页）    │   └─ 成功
    │                              │
    └─> python-pptx                └─> pywin32 (COM)
        └─ 成功（含 slide_count）      ├─ 带重试机制（默认3次）
                                       └─ 成功（含 slide_count）
```

**关键特性：**
- pywin32 重试检测：COM 错误码 `-2147352567` / `发生意外` / `RPC`
- `slide_count` 元数据（python-pptx 和 pywin32 路径均有）
- 与 Word 相同的 COM 资源释放模式

### CAJ 解析流程 (caj_loader.py)

```
CAJ 文件
    │
    ├─> 检查 caj2pdf 工具
    │   └─ 默认路径: src/loaders/caj2pdf/
    │
    ├─> 转换为临时 PDF（120秒超时）
    │   python caj2pdf convert <input.caj> -o <temp.pdf>
    │
    └─> PDFLoader 加载临时 PDF
        ├─ Unstructured → OCR（如需要）
        └─ 返回结果（metadata 含 original_format='caj'）

    [清理临时PDF文件]
```

### RTF 解析流程 (rtf_loader.py)

```
RTF 文件
    │
    ├─> 1. pywin32（Windows）
    │      ├─ Word COM 接口打开
    │      ├─ 带重试机制（RPC错误，默认3次）
    │      ├─ 提取文本和元数据（author, title, page_count）
    │      └─ 成功 → 返回结果
    │      └─ 失败 → 继续
    │
    ├─> 2. Unstructured (partition_text)
    │      └─ 成功 → 返回结果
    │      └─ 失败 → 继续
    │
    └─> 3. 原始读取（多编码尝试）
           └─ 直接读取文件内容
```

**关键特性：**
- 使用 Word COM 接口处理 RTF（与 .doc 相同模式）
- 支持重试机制：RPC 错误自动重试
- 配置参数：`loader.rtf.max_retries`, `loader.rtf.retry_delay`

### HTML 解析流程 (html_loader.py)

```
HTML 文件
    │
    ├─> 1. Unstructured (partition_html)
    │      └─ 成功 → 返回结果
    │      └─ 失败 → 继续
    │
    ├─> 2. BeautifulSoup
    │      ├─ 多编码尝试 (utf-8, gbk, gb2312, latin-1)
    │      ├─ 移除 script/style 标签
    │      ├─ 提取标题（title 标签或 h1）
    │      └─ 返回纯文本
    │
    └─> 3. 直接读取
           └─ 多编码尝试 → 返回原始内容
```

### 文本解析流程 (text_loader.py)

```
.txt / .md / .json / .xml 文件      .csv 文件
    │                                    │
    ├─> Unstructured (partition_text)    ├─> 专用CSV处理器
    │   └─ 成功（.md文件用partition_md）  │   ├─ 多编码尝试
    │   └─ 失败 → 继续                   │   ├─ 行以 | 分隔
    │                                    │   └─ 含 row_count 元数据
    └─> 直接读取（多编码尝试）
        ├─ utf-8 → gbk → gb2312 → latin-1
        └─ 含 encoding 元数据
```

**关键特性：**
- CSV 有专门的 `_load_csv` 方法，不经过 Unstructured
- Markdown 使用 `partition_md` 进行结构化解析
- 多编码自动检测：`utf-8` → `gbk` → `gb2312` → `latin-1`

---

## 输入与输出

### 输入

**文件路径支持：**
- `str`: 字符串路径
- `Path`: pathlib.Path 对象

**配置参数：**
```python
config = {
    'loader': {
        'parallel': {
            'enabled': True,        # 是否并行处理
            'max_workers': 4,       # 最大工作进程数
        },
        'extract_metadata': True,   # 是否提取元数据
        'filters': {
            'min_file_size': 1024,  # 最小文件大小（字节）
        },
        'word': {
            'max_retries': 3,       # Word pywin32 重试次数
            'retry_delay': 2,       # 重试间隔（秒）
        },
        'ppt': {
            'max_retries': 3,       # PPT pywin32 重试次数
            'retry_delay': 2,       # 重试间隔（秒）
        },
        'rtf': {
            'max_retries': 3,       # RTF pywin32 重试次数
            'retry_delay': 2,       # 重试间隔（秒）
            'timeout': 30,          # 单个文件处理超时（秒）
        },
        'caj': {
            'caj2pdf_dir': './src/loaders/caj2pdf',
        },
        'unstructured': {
            'languages': ['chi_sim', 'eng'],  # OCR/解析语言
        },
    },
    'ocr': {
        'enabled': True,            # 是否启用 OCR
        'conda_env': 'OCR',         # OCR 环境名称
        'conda_path': '',           # conda 路径（留空自动查找）
        'progress_callback': None,  # OCR 进度回调函数
    },
    'performance': {
        'max_workers': 2,           # OCR CPU 核心数限制
    },
    'paths': {
        'cache_dir': './cache',     # 缓存目录
        'output_dir': './outputs',  # 输出目录
    },
}
```

### 输出

**统一返回格式：**

```python
{
    'content': str,              # 文档文本内容
    'metadata': {
        # 基础元数据（extract_metadata）
        'source': str,           # 文件绝对路径
        'filename': str,         # 文件名
        'extension': str,        # 扩展名（小写）
        'size_bytes': int,       # 文件大小（字节）
        'created_at': str,       # 创建时间（ISO格式）
        'modified_at': str,      # 修改时间（ISO格式）

        # 解析器信息
        'parser': str,           # 使用的解析器名称

        # 格式特定元数据
        'page_count': int,       # PDF/Word(RTF) 页数
        'slide_count': int,      # PPT 幻灯片数
        'sheet_count': int,      # Excel 工作表数
        'sheet_names': List[str],# Excel 工作表名
        'row_count': int,        # CSV 行数
        'author': str,           # 作者（pywin32/python-docx路径）
        'title': str,            # 标题
        'encoding': str,         # 实际使用的编码（原始读取路径）
        'original_format': str,  # 原始格式（CAJ转换场景）

        # PDFLoader 特有
        #   page_count: int       # 通过 Unstructured 返回的页数
        #   parser: 'unstructured' | 'paddleocr_subprocess'

        # WordLoader 特有
        #   parser: 'unstructured_docx' | 'unstructured_doc' | 'unstructured_wps'
        #           | 'python-docx' | 'pywin32_doc' | 'pywin32_wps'

        # ExcelLoader 特有
        #   parser: 'unstructured_xlsx' | 'unstructured_xls' | 'openpyxl' | 'xlrd'
        #   sheet_count: int
        #   sheet_names: List[str]

        # PPTLoader 特有
        #   parser: 'unstructured_pptx' | 'unstructured_ppt' | 'python_pptx' | 'pywin32'
        #   slide_count: int

        # TextLoader 特有
        #   parser: 'unstructured_text' | 'unstructured_md' | 'csv' | 'raw_text'
        #   encoding: str
        #   row_count: int (仅CSV)

        # HTMLLoader 特有
        #   parser: 'unstructured_html' | 'beautifulsoup' | 'raw_html'
        #   encoding: str
        #   title: str (仅BeautifulSoup路径)

        # RTFLoader 特有
        #   parser: 'pywin32_rtf' | 'unstructured_rtf' | 'raw_rtf'
        #   author: str
        #   title: str
        #   page_count: int

        # CAJLoader 特有
        #   parser: 'caj2pdf+{PDF解析器名}'
        #   original_format: 'caj'
    },
    'pages': [                   # 分页/分片内容（可选）
        {
            'page_num': int,     # 页码（PDF）或 slide_num（PPT）
            'content': str,      # 该页内容
        },
        ...
    ],
}
```

---

## 优化处理

### 1. 并行处理

使用 `ProcessPoolExecutor`（多进程）实现并行文档加载：

```python
loader = DocumentLoader({
    'loader': {
        'parallel': {
            'enabled': True,
            'max_workers': 4
        }
    }
})
```

- 工作进程独立创建 `DocumentLoader` 实例
- 自动恢复异常，不中断整体流程
- 仅当文件数量 > 1 时启用并行

### 2. 增量更新

通过 `IncrementalTracker` 实现增量加载：

```python
# 默认启用增量更新
results = loader.load_documents(file_paths)  # incremental=True

# 全量重建
results = loader.load_documents(file_paths, incremental=False)

# 切换模式
loader.set_incremental_mode(False)
loader.clear_incremental_records()
```

- 只处理新增或修改过的文件
- 成功加载后自动更新记录
- 支持统计查询

### 3. 降级策略

每种格式都有多级降级：
- **PDF**: Unstructured(fast→hi_res) → OCR 子进程
- **Word(.docx)**: Unstructured → python-docx
- **Word(.doc/.wps)**: Unstructured → pywin32(COM)
- **Excel**: Unstructured → openpyxl/xlrd
- **PPT(.pptx)**: Unstructured → python-pptx
- **PPT(.ppt/.ppsx)**: Unstructured → pywin32(COM)
- **RTF**: pywin32(COM) → Unstructured → 原始读取
- **HTML**: Unstructured → BeautifulSoup → 原始读取
- **CAJ**: caj2pdf → PDFLoader → Unstructured/OCR

### 4. 错误重试

pywin32 调用（Word/PPT/RTF）支持自动重试：

| 加载器 | 重试触发条件 | 默认次数 | 间隔 |
|--------|-------------|---------|------|
| WordLoader | `-2147023170` / `远程过程调用` | 3次 | 2秒 |
| PPTLoader | `-2147352567` / `发生意外` / `RPC` | 3次 | 2秒 |
| RTFLoader | `-2147023170` / `远程过程调用` | 3次 | 2秒 |

- 每次重试前强制垃圾回收（`gc.collect()`）
- 非RPC错误直接抛出，不重试

### 5. 资源释放

所有 pywin32 调用都确保资源释放：

```python
try:
    word = win32com.client.Dispatch("Word.Application")
    doc = word.Documents.Open(...)
    content