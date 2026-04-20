# 文本清洗模块 (Cleaner Module)

## 概述

文本清洗模块负责将文档加载器提取的原始文本进行清洗和规范化处理。支持多种清洗策略，包括结构清洗、编码修复、繁简转换、自定义规则以及OCR文本专用处理。

## 核心功能

### 1. 清洗流水线 (Pipeline)

清洗模块采用流水线设计，支持灵活配置清洗步骤：

```yaml
pipeline:
  - "structure"      # 结构清洗
  - "encoding"       # 编码修复
  - "simplified"     # 繁简转换
  - "custom_rules"   # 自定义规则
```

### 2. 结构清洗 (Structure Cleaning)

#### 2.1 基础结构清洗
- 规范化换行符（统一为 `\n`）
- 移除控制字符
- 合并行内多余空白
- 合并多个换行（保留段落分隔）

#### 2.2 Unstructured 结构清洗
使用 Unstructured 库进行高级结构清洗：

```python
from unstructured.cleaners.core import (
    clean_bullets,           # 清理项目符号
    clean_extra_whitespace,  # 清理多余空白
    clean_non_ascii_chars,   # 清理非ASCII字符
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

### 3. 编码修复 (Encoding Fix)

使用 `ftfy` 库自动修复编码问题：
- 修复 Mojibake（字符乱码）
- 修复 HTML 实体编码
- 修复混合编码问题

### 4. 繁简转换 (Traditional to Simplified)

使用 `opencc` 库进行繁体中文到简体中文的转换：

```python
converter = opencc.OpenCC('t2s')  # 繁体转简体
```

### 5. 自定义规则 (Custom Rules)

支持通过 YAML 配置文件定义自定义清洗规则：

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

### 6. OCR 文本专用清洗

针对 OCR 识别文本的特殊处理，解决换行频繁、连字符断词等问题。

#### 6.1 Unstructured OCR 功能

```python
from unstructured.cleaners.ocr import (
    clean_ligatures,        # 清理连字
    replace_unicode_quotes, # 替换Unicode引号
    clean_ordered_bullets,  # 清理有序列表符号
)
```

#### 6.2 连字符断词修复

修复 OCR 中常见的连字符断词问题：

```python
# 修复前: "这是一个com-\nputer示例"
# 修复后: "这是一个computer示例"
text = re.sub(r'(\w)-\n(\w)', r'\1\2', text)
```

#### 6.3 智能换行合并

根据语义智能合并 OCR 文本中的断行：

```python
def _merge_ocr_line_breaks(text: str) -> str:
    """
    智能合并OCR中的断行
    - 不以标点结尾的行与下一行合并
    - 以标点结尾的行为段落边界
    """
```

**使用方式：**
```python
cleaner = TextCleaner()
result = cleaner.clean(text, is_ocr=True)
```

**配置选项：**
```yaml
ocr:
  enabled: true
  options:
    fix_hyphenation: true      # 修复连字符断词
    merge_broken_lines: true   # 合并断裂行
    paragraph_threshold: 2     # 段落检测阈值
```

## 质量检查

清洗后进行质量检查，防止过度清洗：

```yaml
quality_check:
  enabled: true
  min_length: 10              # 最小长度检查
  max_length_ratio: 0.1       # 最大长度损失比例
```

**检查项目：**
- 文本长度是否过短
- 清洗后长度损失是否过大
- 字符集是否有效（无过多替换字符）

## 配置示例

### 基础配置
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

## API 使用

### 基础使用
```python
from src.cleaners import TextCleaner

# 使用默认配置
cleaner = TextCleaner()
text = "需要清洗的文本"
cleaned = cleaner.clean(text)
```

### 带报告清洗
```python
result = cleaner.clean_with_report(text, filename="doc.txt")
print(f"原始长度: {result.quality_report['original_length']}")
print(f"清洗后长度: {result.quality_report['cleaned_length']}")
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
texts = [
    ("文本1", "file1.txt"),
    ("文本2", "file2.txt"),
]
results = cleaner.clean_batch(texts)
```

## 输出文件

清洗后的文本保存为 `.cleaned.txt` 文件，包含：
- 原始文件信息
- 清洗后的文本内容
- 质量检查报告
- 清洗流水线信息

**文件格式：**
```
原始文件: document.txt
清洗时间: 2024-01-20 10:30:00
质量报告:
  原始长度: 1000
  清洗后长度: 950
  长度比例: 0.95
  检查通过: True
清洗流水线: ['structure', 'encoding', 'simplified']
====
[清洗后的文本内容]
```

## 性能优化

### 并行处理
支持多进程并行清洗多个文档：

```yaml
parallel:
  enabled: true
  max_workers: 4
```

### 缓存机制
- 自定义规则文件缓存
- 繁简转换器单例模式

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

## 依赖

核心依赖：
- `ftfy` - 编码修复
- `opencc-python-reimplemented` - 繁简转换
- `pyyaml` - 配置文件解析

可选依赖：
- `unstructured` - 高级结构清洗
- `unstructured[ocr]` - OCR 专用清洗

安装可选依赖：
```bash
pip install unstructured
```

## 注意事项

1. **OCR 文本处理**：启用 `is_ocr=True` 会显著改变文本结构，仅在确认文本来自 OCR 时使用
2. **质量检查**：建议始终启用质量检查，防止过度清洗导致信息丢失
3. **自定义规则**：规则按优先级排序执行，注意规则间的相互影响
4. **Unstructured 依赖**：如未安装 Unstructured，会自动回退到基础清洗功能

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
