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
- 实现智能降级策略（优先现代库，降级到 COM/子进程）
- 支持并行处理和进度监控
- 实现错误重试机制

### 支持的文件格式

| 类别 | 格式 | 扩展名 | 优先级策略 |
|------|------|--------|-----------|
| PDF | PDF | `.pdf` | Unstructured → OCR子进程 |
| Word | Word 2007+ | `.docx` | Unstructured → python-docx |
| Word | Word 97-2003 | `.doc` | Unstructured → pywin32 |
| Word | WPS | `.wps` | Unstructured → pywin32 |
| Excel | Excel 2007+ | `.xlsx` | Unstructured → openpyxl |
| Excel | Excel 97-2003 | `.xls` | Unstructured → xlrd |
| PowerPoint | PPTX | `.pptx` | Unstructured → python-pptx |
| PowerPoint | PPT | `.ppt` | Unstructured → pywin32 |
| PowerPoint | 幻灯片放映 | `.ppsx` | Unstructured → pywin32 |
| CAJ | CAJ | `.caj` | caj2pdf → PDFLoader |
| 文本 | 纯文本 | `.txt` | TextLoader |
| 文本 | Markdown | `.md` | TextLoader |
| 文本 | CSV | `.csv` | TextLoader |
| 文本 | JSON | `.json` | TextLoader |
| 文本 | XML | `.xml` | TextLoader |
| 文本 | RTF | `.rtf` | pywin32 → Unstructured → 原始读取 |
| 网页 | HTML | `.html`, `.htm` | HTMLLoader |

---

## 文件结构

```
src/loaders/
├── __init__.py              # 模块导出
├── base.py                  # 基础加载器抽象类
├── loader_factory.py        # 加载器工厂（注册与获取）
├── document_loader.py       # 统一文档加载入口
│
├── pdf_loader.py            # PDF 加载器（含OCR子进程）
├── word_loader.py           # Word/WPS 加载器
├── excel_loader.py          # Excel 加载器
├── ppt_loader.py            # PowerPoint 加载器
├── caj_loader.py            # CAJ 加载器
├── html_loader.py           # HTML 加载器
├── text_loader.py           # 文本加载器
├── rtf_loader.py            # RTF 加载器（pywin32）
│
└── ocr_processor.py         # OCR 子进程脚本
```

### 文件关系图

```
┌─────────────────────────────────────────────────────────────┐
│                    DocumentLoader (统一入口)                  │
│                   - 并行处理                                   │
│                   - 进度回调                                   │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ LoaderFactory │ │ File Filter  │ │ Progress     │
│ (获取加载器)   │ │ (类型检查)   │ │ (进度监控)   │
└──────┬────────┘ └──────────────┘ └──────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│                      具体加载器实现                          │
├─────────────┬─────────────┬─────────────┬───────────────────┤
│ PDFLoader   │ WordLoader  │ ExcelLoader │ PPTLoader         │
│ (Unstruct   │ (Unstruct   │ (Unstruct   │ (Unstruct         │
│  → OCR)     │  → pywin32) │  → openpyxl)│  → pywin32)       │
├─────────────┼─────────────┼─────────────┼───────────────────┤
│ CAJLoader   │ HTMLLoader  │ TextLoader  │ RTFLoader         │
│ (caj2pdf    │ (Beautiful  │ (直接读取)  │ (pywin32         │
│  → PyMuPDF) │  Soup)      │             │  → Unstructured)  │
└─────────────┴─────────────┴─────────────┴───────────────────┘
```

---

## 核心类与接口

### 1. BaseLoader (base.py)

所有加载器的抽象基类。

```python
class BaseLoader(ABC):
    def __init__(self, config: Optional[Dict[str, Any]] = None)
    
    @abstractmethod
    def supports(self, file_path: Union[str, Path]) -> bool
    
    @abstractmethod
    def load(self, file_path: Union[str, Path]) -> Dict[str, Any]
    
    def extract_metadata(self, file_path: Path) -> Dict[str, Any]
```

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
```

### 3. DocumentLoader (document_loader.py)

统一文档加载入口，支持并行处理、文件过滤、增量更新和失败记录。

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
    
    # 失败文件管理
    def get_failed_files(self) -> List[Dict[str, Any]]
    def save_failed_files_report(self, output_path: Optional[Union[str, Path]] = None) -> Path
    def clear_failed_records(self)
    
    # 增量更新管理
    def set_incremental_mode(self, enabled: bool)
    def clear_incremental_records(self)
    def get_incremental_stats(self) -> Dict[str, Any]
```

---

## 各格式解析流程

### PDF 解析流程 (pdf_loader.py)

```
PDF 文件
    │
    ├─> 1. Unstructured (partition_pdf)
    │      ├─ fast 模式（纯文本）
    │      │   └─ 成功 → 返回结果
    │      └─ hi_res 模式（复杂布局）
    │          └─ 成功 → 返回结果
    │          └─ 失败 → 继续
    │
    └─> 2. OCR 子进程（conda run -n OCR）
           ├─> ocr_processor.py
           │    ├─ PyMuPDF 转图片
           │    ├─ PaddleOCR 识别
           │    └─ 返回文本
           │
           └─ 支持进度监控（progress 文件）
```

**关键特性：**
- 双环境隔离：主环境(RAG) + OCR环境(OCR)
- 无超时限制：大型 PDF 可完整处理
- 进度汇报：子进程实时汇报处理进度

### Word 解析流程 (word_loader.py)

```
.docx 文件                    .doc / .wps 文件
    │                              │
    ├─> Unstructured               ├─> Unstructured
    │   (partition_docx)           │   (partition_doc / partition_doc)
    │   └─ 成功                    │   └─ 成功
    │                              │
    └─> python-docx                └─> pywin32 (COM)
        └─ 成功                        ├─ 带重试机制（默认3次）
                                       ├─ 资源强制释放
                                       └─ 成功
```

**关键特性：**
- 重试机制：RPC 错误自动重试
- 资源释放：`finally` 块确保 COM 对象释放
- 配置参数：`max_retries`, `retry_delay`

### Excel 解析流程 (excel_loader.py)

```
.xlsx 文件                    .xls 文件
    │                              │
    ├─> Unstructured               ├─> Unstructured
    │   (partition_xlsx)           │   (partition_xls)
    │   └─ 成功                    │   └─ 成功
    │                              │
    └─> openpyxl                   └─> xlrd
        └─ 成功                        └─ 成功
```

### PowerPoint 解析流程 (ppt_loader.py)

```
.pptx 文件                    .ppt / .ppsx 文件
    │                              │
    ├─> Unstructured               ├─> Unstructured
    │   (partition_pptx)           │   (partition_ppt)
    │   └─ 成功                    │   └─ 成功
    │                              │
    └─> python-pptx                └─> pywin32 (COM)
        └─ 成功                        ├─ 带重试机制
                                       └─ 成功
```

### CAJ 解析流程 (caj_loader.py)

```
CAJ 文件
    │
    ├─> 检查 caj2pdf 工具
    │
    ├─> 转换为临时 PDF
    │   python caj2pdf convert <input.caj> -o <temp.pdf>
    │
    └─> PDFLoader 加载
        ├─ Unstructured → OCR（如需要）
        └─ 返回结果
    
    [清理临时文件]
```

### RTF 解析流程 (rtf_loader.py)

```
RTF 文件
    │
    ├─> 1. pywin32（Windows）
    │      ├─ Word COM 接口打开
    │      ├─ 带重试机制（默认3次）
    │      ├─ 提取文本和元数据
    │      └─ 成功 → 返回结果
    │      └─ 失败 → 继续
    │
    ├─> 2. Unstructured
    │      └─ 成功 → 返回结果
    │      └─ 失败 → 继续
    │
    └─> 3. 原始读取
           └─ 直接读取文件内容
```

**关键特性：**
- 使用 Word COM 接口处理RTF（与.doc/.ppt相同）
- 支持重试机制：RPC错误自动重试
- 资源释放：`finally` 块确保 COM 对象释放
- 配置参数：`max_retries`, `retry_delay`

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
        'word': {
            'max_retries': 3,       # Word pywin32 重试次数
            'retry_delay': 2,       # 重试间隔（秒）
        },
        'ppt': {
            'max_retries': 3,       # PPT pywin32 重试次数
            'retry_delay': 2,       # 重试间隔（秒）
        },
    },
    'ocr': {
        'enabled': True,            # 是否启用 OCR
        'conda_env': 'OCR',         # OCR 环境名称
        'conda_path': 'conda',      # conda 路径
        'progress_callback': None,  # OCR 进度回调函数
    },
    'paths': {
        'cache_dir': './cache',     # 缓存目录
    }
}
```

### 输出

**统一返回格式：**

```python
{
    'content': str,              # 文档文本内容
    'metadata': {
        'source': str,           # 文件路径
        'filename': str,         # 文件名
        'extension': str,        # 扩展名
        'size': int,             # 文件大小（字节）
        'created_at': str,       # 创建时间（ISO格式）
        'modified_at': str,      # 修改时间（ISO格式）
        'parser': str,           # 使用的解析器
        # 格式特定元数据
        'page_count': int,       # PDF/Word 页数
        'slide_count': int,      # PPT 幻灯片数
        'sheet_count': int,      # Excel 工作表数
        'sheet_names': List[str],# Excel 工作表名
        'author': str,           # 作者
        'title': str,            # 标题
    },
    'pages': [                   # 分页/分片内容（可选）
        {
            'page_num': int,     # 页码
            'content': str,      # 该页内容
        },
        ...
    ],
}
```

---

## 优化处理

### 1. 并行处理

```python
# 启用并行加载（多进程）
loader = DocumentLoader({
    'loader': {
        'parallel': {
            'enabled': True,
            'max_workers': 4
        }
    }
})
```

### 3. 降级策略

每种格式都有多级降级：
- **PDF**: Unstructured → OCR 子进程
- **Word**: Unstructured → python-docx/pywin32
- **Excel**: Unstructured → openpyxl/xlrd
- **PPT**: Unstructured → python-pptx/pywin32
- **RTF**: pywin32 → Unstructured → 原始读取
- **CAJ**: caj2pdf → PDFLoader → Unstructured/OCR

### 4. 错误重试

pywin32 调用（Word/PPT/RTF）支持自动重试：
- 检测 RPC 错误（-2147023170）
- 默认重试 3 次，间隔 2 秒
- 每次重试前强制垃圾回收

### 5. 资源释放

所有 pywin32 调用都确保资源释放：
```python
try:
    # 使用 COM 对象
    ...
finally:
    if doc:
        try: doc.Close()
        except: pass
    if app:
        try: app.Quit()
        except: pass
    import gc
    gc.collect()
```

### 6. OCR 进度监控

PDF OCR 处理支持实时进度：
```python
def on_ocr_progress(current, total, message):
    print(f"OCR: {current}/{total} - {message}")

config = {
    'ocr': {
        'progress_callback': on_ocr_progress
    }
}
```

---

## 参数配置

### 完整配置示例

```yaml
# config.yaml (用户配置) 或 default_config.yaml (默认配置)
loader:
  parallel:
    enabled: true
    max_workers: 4
  
  extract_metadata: true
  
  word:
    max_retries: 3
    retry_delay: 2
  
  ppt:
    max_retries: 3
    retry_delay: 2
  
  rtf:
    max_retries: 3
    retry_delay: 2

ocr:
  enabled: true
  conda_env: "OCR"
  conda_path: "conda"
  # progress_callback: 在代码中设置

paths:
  cache_dir: "./cache"
```

### 环境变量

```bash
# OCR 环境（conda）
conda create -n OCR python=3.11
conda activate OCR
pip install -r requirements-ocr.txt

# 主环境
conda activate RAG
pip install -r requirements.txt
```

---

## 使用示例

### 基本使用

```python
from src.loaders import DocumentLoader

# 创建加载器
loader = DocumentLoader()

# 加载单个文件
result = loader.load_document("document.pdf")
print(result['content'])
print(result['metadata']['parser'])

# 加载目录
docs = loader.load_directory("./data", recursive=True)
```

### 带进度回调

```python
def on_progress(current, total, filename):
    print(f"[{current}/{total}] {filename}")

loader = DocumentLoader()
file_paths = ["doc1.pdf", "doc2.docx", "doc3.pptx"]
results = loader.load_documents(file_paths, progress_callback=on_progress)
```

### 自定义配置

```python
config = {
    'loader': {
        'parallel': {'enabled': True, 'max_workers': 8},
        'word': {'max_retries': 5}
    },
    'ocr': {
        'enabled': True,
        'progress_callback': lambda c, t, m: print(f"OCR: {c}/{t} {m}")
    }
}

loader = DocumentLoader(config)
```

### 批量加载带错误处理

```python
loader = DocumentLoader()
file_paths = [...]  # 文件列表

results = loader.load_documents(file_paths)

for result in results:
    if result.get('content'):
        print(f"成功: {result['metadata']['source']}")
    else:
        print(f"失败: {result['metadata'].get('error', '未知错误')}")
```

---

## 扩展开发

### 添加新的加载器

1. **创建加载器类**（继承 BaseLoader）

```python
# src/loaders/myformat_loader.py
from .base import BaseLoader

class MyFormatLoader(BaseLoader):
    def supports(self, file_path) -> bool:
        return Path(file_path).suffix.lower() == '.myf'
    
    def load(self, file_path) -> Dict[str, Any]:
        # 实现加载逻辑
        content = self._parse_file(file_path)
        
        return {
            'content': content,
            'metadata': {
                **self.extract_metadata(file_path),
                'parser': 'myformat_loader'
            },
            'pages': [],
        }
```

2. **注册到工厂**

```python
# src/loaders/loader_factory.py
def register_all_loaders():
    from .myformat_loader import MyFormatLoader
    
    # ... 其他注册
    LoaderFactory.register('.myf', MyFormatLoader)
```

3. **更新 __init__.py**

```python
# src/loaders/__init__.py
from .myformat_loader import MyFormatLoader

__all__ = [
    # ... 其他导出
    'MyFormatLoader',
]
```

### 添加新的降级策略

在现有加载器中添加新的降级方法：

```python
def load(self, file_path):
    # 尝试方法1
    if self._lib1_available:
        try:
            return self._load_with_lib1(file_path)
        except:
            pass
    
    # 尝试方法2（新增）
    if self._lib2_available:
        try:
            return self._load_with_lib2(file_path)
        except:
            pass
    
    # 最终降级
    raise RuntimeError(f"无法解析文件: {file_path}")
```

---

## 注意事项

1. **Windows 依赖**: .doc, .ppt, .wps, .rtf 需要 Windows + pywin32
2. **OCR 环境**: PDF OCR 需要独立的 OCR conda 环境
3. **caj2pdf**: CAJ 需要本地克隆 caj2pdf 工具到 `src/loaders/caj2pdf`
4. **内存管理**: 大型 PDF OCR 会占用较多内存
5. **并发限制**: pywin32 调用不建议过多并发（COM 对象限制）

---

## 更新日志

| 日期 | 版本 | 更新内容 |
|------|------|---------|
| 2024-04-17 | 1.0 | 初始版本，支持 18 种格式 |
| 2024-04-17 | 1.1 | 添加 OCR 进度监控 |
| 2024-04-17 | 1.2 | 添加 pywin32 重试机制 |
| 2024-04-17 | 1.3 | 添加 .wps 格式支持 |

---

**文档维护**: 当添加新格式或修改解析流程时，请同步更新本文档。
