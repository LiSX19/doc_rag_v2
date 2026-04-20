# 增量更新功能文档

## 概述

系统支持两种更新模式：
- **增量更新**（默认）：只处理新增或修改的文件
- **全量更新**：重新处理所有文件

## 工作原理

### 文件识别机制

使用 **MD5 哈希值** 识别文件是否变化：

1. **首次处理**：计算文件哈希值并记录
2. **后续处理**：比较当前哈希与记录哈希
   - 哈希相同 → 跳过（文件未变化）
   - 哈希不同 → 处理（文件已修改）
   - 无记录 → 处理（新文件）

### 记录存储

```
cache/
├── file_hashes.json      # 文件哈希记录
└── file_timestamps.json  # 文件时间戳记录
```

## 使用方法

### 命令行使用

```bash
# 增量更新（默认）- 只处理新增或修改的文件
python doc_rag.py build --input-dir F:\documents

# 全量更新 - 重新处理所有文件
python doc_rag.py build --full --input-dir F:\documents

# 清空增量记录，下次全量处理
python doc_rag.py build --clear-incremental
```

### 代码中使用

```python
from src.loaders import DocumentLoader

# 创建加载器（默认启用增量更新）
loader = DocumentLoader(config)

# 查看增量更新统计
stats = loader.get_incremental_stats()
print(f"已记录文件数: {stats['total_recorded']}")

# 切换模式
loader.set_incremental_mode(True)   # 增量模式
loader.set_incremental_mode(False)  # 全量模式

# 清空记录（全量重建）
loader.clear_incremental_records()

# 加载文档（使用增量更新）
docs = loader.load_documents(file_paths, incremental=True)

# 加载文档（强制全量更新）
docs = loader.load_documents(file_paths, incremental=False)
```

## 配置

在 `configs.yaml` 中配置：

```yaml
incremental_update:
  enabled: true                    # 默认启用增量更新
  hash_file: "./cache/file_hashes.json"
  timestamp_file: "./cache/file_timestamps.json"
```

## 输出示例

### 增量更新模式

```
[INFO] 文档加载器初始化完成，支持格式: 18 种
[INFO] 增量更新追踪器初始化完成，模式: 增量
[INFO] 已记录文件数: 100
[INFO] 文件筛选完成:
[INFO]   总计: 120 个
[INFO]   需要处理: 25 个
[INFO]     - 新文件: 10 个
[INFO]     - 已修改: 15 个
[INFO]   跳过（未变化）: 95 个
[INFO] 开始批量加载 25 个文档
...
[INFO] 批量加载完成，成功: 25/25
[INFO] 更新 25 个文件的记录
```

### 全量更新模式

```
[INFO] 文档加载器初始化完成，支持格式: 18 种
[INFO] 增量更新追踪器初始化完成，模式: 全量
[INFO] 全量更新模式：处理所有文件
[INFO] 开始批量加载 120 个文档
...
[INFO] 批量加载完成，成功: 120/120
[INFO] 更新 120 个文件的记录
```

## 手动管理记录

```python
from src.utils import IncrementalTracker

tracker = IncrementalTracker(config)

# 检查单个文件
need_process, reason = tracker.check_file("doc.pdf")
print(f"需要处理: {need_process}, 原因: {reason}")
# 输出: (True, "new") 或 (True, "modified") 或 (False, "unchanged")

# 批量筛选文件
to_process, stats = tracker.filter_files(file_paths)
print(f"需要处理: {len(to_process)} 个")

# 更新记录
tracker.update_record("doc.pdf")
tracker.update_records(file_paths)

# 清理无效记录（文件已删除）
tracker.clean_orphaned_records()

# 清空所有记录
tracker.clear_all_records()

# 获取统计
stats = tracker.get_statistics()
```

## 注意事项

1. **首次运行**：自动全量处理，建立哈希记录
2. **文件重命名**：视为新文件（路径变化）
3. **文件移动**：视为新文件（路径变化）
4. **哈希冲突**：概率极低，可忽略
5. **清理记录**：删除 `cache/file_hashes.json` 可强制全量更新

## 使用场景

| 场景 | 建议模式 | 命令 |
|------|---------|------|
| 日常更新 | 增量 | `python doc_rag.py build` |
| 首次构建 | 全量（自动） | `python doc_rag.py build` |
| 修复数据 | 全量 | `python doc_rag.py build --full` |
| 重建索引 | 全量 | `python doc_rag.py build --full` |
| 清空记录 | - | `python doc_rag.py build --clear-incremental` |
