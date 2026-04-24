# 文本清洗模块 (Cleaner Module)

## 概述

文本清洗模块负责将文档加载器提取的原始文本进行清洗和规范化处理。支持多种清洗策略，包括结构清洗、编码修复、繁简转换、自定义规则以及OCR文本专用处理。

## 文件结构

```
src/cleaners/
├── __init__.py        # 模块入口，导出 BaseCleaner, TextCleaner, CleaningResult, QualityReport
├── base.py            # 抽象基类 BaseCleaner
└── text_cleaner.py    # 核心实现 TextCleaner，dataclass：CleaningResult, QualityReport
```

## 核心类与接口

### BaseCleaner (抽象基类)

**位置**: `src/cleaners/base.py`

```python
class BaseCleaner(ABC):
    def __init__(self, config: Optional[Dict[str, Any]] = None): ...
    
    @abstractmethod
    def clean(self, text: str) -> str: ...
    
    def clean_batch(self, texts: List[str]) -> List[str]: ...
```

| 方法 | 说明 |
| --- | --- |
| `clean(text)` | 清洗单条文本（抽象方法） |
| `clean_batch(texts)` | 批量清洗文本列表（基于 `clean` 的默认实现） |

### CleaningResult (数据类)

**位置**: `src/cleaners/text_cleaner.py`

```python
@dataclass
class CleaningResult:
    filename: str               # 文件名
    original_text: str          # 原始文本
    cleaned_text: str           # 清洗后文本
    quality_report: Dict[str, Any]  # 质量检查报告
    success: bool               # 是否成功
    error: Optional[str] = None # 错误信息（失败时）
```

### QualityReport (数据类)

```python
@dataclass
class QualityReport:
    original_length: int        # 原始长度
    cleaned_length: int         # 清洗后长度
    length_ratio: float         # 长度比例（清洗后/原始）
    char_set_valid: bool        # 字符集是否有效
    min_length_check: bool      # 最小长度检查是否通过
    passed: bool                # 是否全部通过
    issues: List[str]           # 问题列表
```

### TextCleaner

**位置**: `src/cleaners/text_cleaner.py`

```python
class TextCleaner(BaseCleaner):
    def __init__(self, config: Optional[Dict[str, Any]] = None): ...
    def clean(self, text: str, filename: Optional[str] = None, is_ocr: bool = False) -> str: ...
    def clean_with_report(self, text: str, filename: Optional[str] = None, is_ocr: bool = False) -> CleaningResult: ...
    def clean_batch(self, texts: List[Union[str, Tuple[str, str]]]) -> List[CleaningResult]: ...
    def clean_batch_parallel(self, texts: List[Union[str, Tuple[str, str]]]) -> List[CleaningResult]: ...
```

### 模块导出

**位置**: `src/cleaners/__init__.py`

```python
__all__ = ["BaseCleaner", "TextCleaner", "CleaningResult", "QualityReport"]
```

## 清洗流水线 (Pipeline)

清洗模块采用流水线设计，支持灵活配置清洗步骤：

```python
# 默认清洗步骤
self.pipeline = cleaner_config.get('pipeline', ['structure', 'encoding', 'simplified'])
```

```yaml
pipeline:
  - "structure"      # 结构清洗
  - "encoding"       # 编码修复
  - "simplified"     # 繁简转换
  - "custom_rules"   # 自定义规则
```

### 执行流程

```python
for step in self.pipeline:
    if step == 'structure':
        text = self._clean_structure(text)
    elif step == 'encoding':
        text = self._fix_encoding(text)
    elif step == 'simplified':
        text = self._convert_to_simplified(text)
    elif step == 'custom_rules':
        text = self._apply_custom_rules(text)
```

若文本为OCR文本（`is_ocr=True`），在进入流水线前会先执行 `_clean_ocr_text()` 专用清洗。

## 1. 结构清洗 (Structure Cleaning)

结构清洗有两种模式：**基础清洗**（默认）和 **Unstructured 高级清洗**（可选）。

### 1.1 基础结构清洗

**方法**: `_clean_structure_basic(text)`

步骤：
1. **规范化换行符** — 统一为 `\n`
2. **移除控制字符** — 保留 `\n`，移除 `\x00-\x08`, `\x0b-\x0c`, `\x0e-\x1f`, `\x7f`
3. **合并行内空白** — 多个空格/制表符合并为一个空格
4. **合并多个换行** — 保留段落分隔（最多两个连续换行）
5. **移除行首尾空白** — 每行 strip 空格和制表符

```python
text = text.replace('\r\n', '\n').replace('\r', '\n')
text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', text)
text = re.sub(r'[ \t]+', ' ', text)
text = re.sub(r'\n[ \t]*\n+', '\n\n', text)
lines = [line.strip(' \t') for line in text.split('\n')]
```

### 1.2 Unstructured 结构清洗

**方法**: `_clean_structure_unstructured(text)`

当配置启用且 Unstructured 库可用时，使用该库进行高级结构清洗。若清洗过程中出错，自动回退到基础清洗。

```python
from unstructured.cleaners.core import (
    clean_bullets,           # 清理项目符号
    clean_extra_whitespace,  # 清理多余空白
    clean_non_ascii_chars,   # 清理非ASCII字符
    clean_ordered_bullets,   # 清理有序列表符号
    group_broken_paragraphs, # 组合断裂段落
    remove_punctuation,      # 移除标点符号
)
```

**配置选项：**
```yaml
unstructured:
  enabled: true
  options:
    clean_bullets: true
    clean_extra_whitespace: true
    clean_non_ascii_chars: false
    group_broken_paragraphs: true
    remove_punctuation: false
```

执行顺序：
1. `clean_bullets` + `clean_ordered_bullets` — 清理项目符号和有序列表符号
2. `clean_extra_whitespace` — 清理多余空白
3. `clean_non_ascii_chars` — 清理非ASCII字符（默认关闭）
4. `group_broken_paragraphs` — 组合断裂段落
5. `remove_punctuation` — 移除标点（默认关闭）
6. 最后追加基础清洗以确保换行符保留

### 1.3 Unstructured 可用性检测

在模块导入时不会立即检测 Unstructured 库，采用**惰性检测**机制：

```python
# 首次实例化 TextCleaner 时检测
_ensure_unstructured_checked()

# 检测结果缓存到全局变量
UNSTRUCTURED_AVAILABLE      # Unstructured 核心是否可用
UNSTRUCTURED_OCR_AVAILABLE  # Unstructured OCR 功能是否可用
```

- 若 Unstructured 未安装，自动使用基础清洗
- 若仅核心库可用，使用高级结构清洗（不含OCR功能）
- 若OCR功能也可用，同时启用OCR专用清洗

## 2. 编码修复 (Encoding Fix)

**方法**: `_fix_encoding(text)`

使用 `ftfy` 库自动修复编码问题：
- 修复 Mojibake（字符乱码）
- 修复 HTML 实体编码
- 修复混合编码问题

```python
import ftfy
text = ftfy.fix_text(text)
```

## 3. 繁简转换 (Traditional to Simplified)

**方法**: `_convert_to_simplified(text)`

使用 `opencc` 库进行繁体中文到简体中文的转换：

```python
import opencc
self.converter = opencc.OpenCC('t2s')  # 繁体转简体
```

初始化时若 `pipeline` 包含 `'simplified'` 步骤，则会创建转换器实例。

## 4. 自定义规则 (Custom Rules)

**方法**: `_apply_custom_rules(text)`

支持通过代码配置或 YAML 文件定义自定义清洗规则，按优先级排序执行。

### 4.1 配置方式

**内联配置**：
```python
custom_rules = [
    {
        'name': 'remove_extra_whitespace',
        'pattern': '[ \\t]+',
        'replacement': ' ',
        'enabled': True,
        'priority': 1
    }
]
```

**YAML 文件配置**（通过 `custom_rules_file` 指定）：
```yaml
rules:
  - name: "remove_extra_whitespace"
    description: "移除多余空白字符"
    pattern: "[ \\t]+"
    replacement: " "
    enabled: true
    priority: 1
  
  - name: "normalize_quotes"
    description: "统一引号格式"
    pattern: '[""''`"]'
    replacement: '"'
    enabled: true
    priority: 2
```

### 4.2 加载流程

```python
def _load_custom_rules_from_file(self, file_path: str):
    with open(file_path, 'r', encoding='utf-8') as f:
        rules_config = yaml.safe_load(f)
    for rule in rules_config['rules']:
        if rule.get('enabled', False):
            self.custom_rules.append({...})
    self.custom_rules.sort(key=lambda x: x.get('priority', 100))
```

- 支持从 YAML 文件加载
- 仅加载 `enabled: true` 的规则
- 按 `priority` 升序执行

## 5. OCR 文本专用清洗

**方法**: `_clean_ocr_text(text)`

当调用 `clean()` 时设置 `is_ocr=True`，会在主流水线前执行 OCR 专用清洗。

### 5.1 Unstructured OCR 清洗（可选）

```python
from unstructured.cleaners.ocr import (
    clean_ligatures,        # 清理连字（ligatures）
    replace_unicode_quotes, # 替换Unicode引号
    clean_ordered_bullets,  # 清理有序列表符号
)
```

### 5.2 连字符断词修复

**方法**: `_fix_ocr_hyphenation(text)`

修复 OCR 中常见的连字符断词问题：

```python
# 匹配连字符+换行+字母的模式
text = re.sub(r'(\w)-\n(\w)', r'\1\2', text)
text = re.sub(r'(\w)-\s*\n\s*(\w)', r'\1\2', text)
```

| 修复前 | 修复后 |
| --- | --- |
| `com-\nputer` | `computer` |
| `tele-\nphone` | `telephone` |

### 5.3 智能换行合并

**方法**: `_merge_ocr_line_breaks(text)`

根据语义智能合并 OCR 文本中的断行：

1. 按换行符分割为行列表
2. 空行视为段落边界
3. **合并规则**：
   - 当前行以标点结尾（`.。!！?？;；:：`）→ 分段
   - 下一行以大写字母或数字开头 → 分段
   - 其他情况 → 合并为同一段落（添加空格连接）
4. 段落间用双换行分隔
5. 清理多余空白，合并过多换行

```python
# 合并前：
"这是一个com-\nputer示例\n还有tele-\nphone。\n\n下一段落"

# 合并后：
"这是一个computer示例 还有telephone。\n\n下一段落"
```

## 6. 质量检查

**方法**: `_check_quality(original_text, cleaned_text) -> QualityReport`

清洗后进行质量检查，防止过度清洗。

### 检查项目

| 检查项 | 说明 | 条件 |
| --- | --- | --- |
| 最小长度 | 清洗后文本长度是否过短 | `cleaned_length >= min_length`（默认10） |
| 长度比例 | 防止过度清洗导致信息丢失 | `cleaned_length / original_length >= max_length_ratio`（默认0.1） |
| 字符集有效 | 检查是否包含过多替换字符 | 替换字符 `\ufffd` 占比不超过10% |

### 判定

全部检查通过则 `passed = True`，否则记录问题列表到 `issues`。

## 7. 输出管理

清洗后的文本通过 `OutputManager.save_cleaned_text()` 保存，元数据中包含清洗流水线和质量报告信息。

```python
self.output_manager.save_cleaned_text(
    filename=filename,
    original_content=original_text,
    cleaned_content=cleaned_text,
    metadata={
        'pipeline': self.pipeline,
        'quality_report': {
            'original_length': ...,
            'cleaned_length': ...,
            'length_ratio': ...,
            'passed': ...
        }
    }
)
```

输出的 `.cleaned.txt` 文件格式由 `OutputManager` 统一管理，包含原始文件信息和清洗元数据。

**输出配置**（在 `config.yaml` 的 `output` 部分）：
```yaml
output:
  mode: "test"  # test/production/minimal/custom
  stages:
    cleaned: true   # 控制是否输出清洗产物
```

## 8. 并行处理

**方法**: `clean_batch_parallel(texts)`

支持多进程并行清洗多个文档，使用 `ProcessPoolExecutor`。

### 配置

```yaml
parallel:
  enabled: true
  max_workers: 4
```

### 工作函数

**位置**: 模块级函数 `_clean_worker(text, filename, config)`

```python
def _clean_worker(text: str, filename: Optional[str], config: Dict[str, Any]) -> CleaningResult:
    """并行清洗工作函数（必须在模块级别定义以便 pickle 序列化）"""
    cleaner = TextCleaner(config)
    return cleaner.clean_with_report(text, filename)
```

- 自动回退：若文本少于2条或未启用并行，自动使用 `clean_batch`
- 异常隔离：单个任务失败不影响其他任务，失败结果中 `success=False`

## API 使用

### 基础使用

```python
from src.cleaners import TextCleaner

# 使用默认配置
cleaner = TextCleaner()
text = "需要清洗的文本"
cleaned = cleaner.clean(text)
```

### 带文件名保存清洗结果

```python
cleaned = cleaner.clean(text, filename="doc.txt")
# 自动通过 OutputManager 保存清洗后文件
```

### 带报告清洗

```python
result = cleaner.clean_with_report(text, filename="doc.txt")
print(f"清洗成功: {result.success}")
print(f"原始长度: {result.quality_report['original_length']}")
print(f"清洗后长度: {result.quality_report['cleaned_length']}")
print(f"问题列表: {result.quality_report.get('issues', [])}")
```

### OCR 文本清洗

```python
# OCR 识别的文本
ocr_text = "这是一个com-\nputer示例，还有tele-\nphone。"
cleaned = cleaner.clean(ocr_text, is_ocr=True)
# 结果: "这是一个computer示例，还有telephone。"
```

### 批量清洗

```python
# 文本列表（可附带文件名）
texts = [
    ("文本1", "file1.txt"),
    ("文本2", "file2.txt"),
]
results = cleaner.clean_batch(texts)
# results: List[CleaningResult]
```

### 并行批量清洗

```python
results = cleaner.clean_batch_parallel(texts)
# 自动启用多进程，返回 List[CleaningResult]
```

### 配置传入

```python
config = {
    'cleaner': {
        'pipeline': ['structure', 'encoding', 'simplified', 'custom_rules'],
        'custom_rules_file': './src/configs/cleaning_rules.yaml',
        'quality_check': {
            'enabled': True,
            'min_length': 10,
            'max_length_ratio': 0.1
        }
    }
}
cleaner = TextCleaner(config)
```

## 配置示例

### 完整基础配置

```yaml
cleaner:
  pipeline:
    - "structure"
    - "encoding"
    - "simplified"
  custom_rules_file: "./src/configs/cleaning_rules.yaml"
  quality_check:
    enabled: true
    min_length: 10
    max_length_ratio: 0.1
```

### 启用 Unstructured 清洗

```yaml
cleaner:
  pipeline:
    - "structure"
    - "encoding"
    - "simplified"
  unstructured:
    enabled: true
    options:
      clean_bullets: true
      clean_extra_whitespace: true
      group_broken_paragraphs: true
```

### OCR 文本清洗

```yaml
cleaner:
  pipeline:
    - "structure"
    - "encoding"
  ocr:
    enabled: true
    options:
      fix_hyphenation: true
      merge_broken_lines: true
```

> **注意**: 代码中 OCR 开关通过 `clean()` 方法的 `is_ocr` 参数控制，而非配置中的 `ocr.enabled`。

### 并行处理

```yaml
cleaner:
  pipeline:
    - "structure"
    - "encoding"
    - "simplified"
  parallel:
    enabled: true
    max_workers: 4
```

## 依赖

### 核心依赖（必需）

| 库 | 用途 | 在代码中的使用 |
| --- | --- | --- |
| `ftfy` | 编码修复 | `ftfy.fix_text()` |
| `opencc-python-reimplemented` | 繁简转换 | `opencc.OpenCC('t2s')` |
| `pyyaml` | 配置文件解析 | `yaml.safe_load()` |

### 可选依赖

| 库 | 用途 | 检测方式 |
| --- | --- | --- |
| `unstructured` | 高级结构清洗 | `UNSTRUCTURED_AVAILABLE` |
| `unstructured[ocr]` | OCR 专用清洗 | `UNSTRUCTURED_OCR_AVAILABLE` |

安装可选依赖：
```bash
pip install unstructured
pip install "unstructured[ocr]"
```

## 质量检查与异常处理

### 质量检查触发

- 启用时（默认启用），每次 `clean()` 调用后自动检查
- 检查未通过仅记录警告日志，不中断流程

### 异常处理策略

- `clean_with_report()` 捕获所有异常，返回 `CleaningResult(success=False, error=str(e))`
- `clean_batch_parallel()` 单个任务异常不影响其他任务
- Unstructured 清洗失败自动回退到基础清洗

## 注意事项

1. **OCR 文本处理**：启用 `is_ocr=True` 会显著改变文本结构（合并断行），仅在确认文本来自 OCR 时使用
2. **质量检查**：建议始终启用质量检查，防止过度清洗导致信息丢失。检查基于替换字符 `\ufffd` 占比判断编码问题
3. **自定义规则**：规则按优先级排序执行，注意规则间的相互影响
4. **Unstructured 回退**：如未安装 Unstructured，自动回退到基础清洗功能，不影响正常使用
5. **配置结构**：TextCleaner 同时支持 `config['cleaner']` 嵌套结构和直接传入 flat 配置

## 测试

运行清洗模块测试：

```bash
python tests/test_clean.py
```

测试覆盖：
- 结构清洗功能
- 编码修复功能
- 繁简转换功能
- 自定义规则
- 质量检查
- OCR 文本清洗
- 配置加载
- 并行处理

## 更新日志

### v1.0.0
- 基础清洗功能实现
- 支持结构清洗、编码修复、繁简转换
- 自定义规则引擎

### v1.1.0
- 集成 Unstructured 结构清洗
- 添加质量检查机制

### v1.2.0
- 添加 OCR 文本专用清洗
- 支持连字符断词修复
- 智能换行合并

### v1.3.0
- 添加 `CleaningResult` 和 `QualityReport` 数据类
- 添加 `clean_with_report()` 方法
- 添加 `clean_batch_parallel()` 并行批量清洗
- 集成 `OutputManager` 输出管理
- 添加 Unstructured 惰性检测机制
- 优化异常处理与自动回退
- 导出模块公共 API（`__init__.py`）
