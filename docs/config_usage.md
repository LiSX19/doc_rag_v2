# 配置统一管理文档

## 概述

所有模块的参数都通过 `configs.yaml` 统一管理，通过 `ConfigManager` 读取并传递给各模块。

## 配置文件结构

```yaml
# configs.yaml
project:          # 项目信息
paths:            # 路径配置
logging:          # 日志配置
loader:           # 文档加载配置
cleaner:          # 文本清洗配置
chunker:          # 文本分块配置
deduper:          # 去重配置
encoder:          # 编码配置（原Embedding配置）
vector_store:     # 向量数据库配置
retriever:        # 检索配置
evaluator:        # 评估配置
performance:      # 性能优化配置
```

## 配置读取方式

### 1. 主程序入口

```python
from src.configs import ConfigManager
from src.utils import get_logger

# 加载配置
config_manager = ConfigManager(config_path="configs.yaml")

# 获取具体配置值
input_dir = config_manager.get('paths.input_dir')
log_level = config_manager.get('logging.level', 'INFO')

# 获取整个配置字典（传递给各模块）
full_config = config_manager._config
```

### 2. 各模块配置读取

各模块通过构造函数接收配置字典，并读取对应配置：

```python
# 统一模式：先尝试读取模块专属配置，如果不存在则使用传入的配置
module_config = self.config.get('module_name', self.config)
specific_config = module_config.get('key', default_value)
```

## 各模块配置映射

| 模块 | 配置路径 | 关键配置项 |
|------|---------|-----------|
| **Loader** | `loader.*`, `ocr.*`, `paths.*` | `parallel.enabled`, `ocr.enabled` |
| **TaskFileManager** | `task_file_manager.*`, `loader.filters.*` | `task_file`, `min_file_size` |
| **Cleaner** | `cleaner.*` | `pipeline`, `custom_rules_file` |
| **Chunker** | `chunker.*` | `chunk_size`, `chunk_overlap`, `separators` |
| **Deduper** | `deduper.*` | `strategy`, `test.*`/`production.*` |
| **Encoder** | `encoder.*` | `model.name`, `batch_size`, `cache.enabled` |
| **VectorStore** | `vector_store.*` | `chroma.*` |
| **Retriever** | `retriever.*` | `top_k`, `rerank.enabled`, `filter.threshold` |
| **Evaluator** | `evaluator.*` | `ragas.metrics` |

## 使用示例

### 完整流程示例

```python
from src.configs import ConfigManager
from src.utils import setup_logging, get_logger
from src.loaders import DocumentLoader
from src.cleaners import TextCleaner
from src.chunkers import RecursiveChunker
from src.dedupers import Deduper
from src.encoders import BGEEncoder
from src.vector_stores import ChromaStore
from src.retrievers import VectorRetriever

# 1. 加载配置
config_manager = ConfigManager("configs.yaml")
config = config_manager._config  # 获取完整配置字典

# 2. 设置日志
setup_logging(
    level=config_manager.get('logging.level', 'INFO'),
    log_file=config_manager.get('logging.file')
)
logger = get_logger(__name__)

# 3. 初始化各模块（自动读取配置）
logger.info("初始化模块...")

# Loader - 自动读取 loader.*, ocr.*, paths.*
loader = DocumentLoader(config)

# Cleaner - 自动读取 cleaner.*
cleaner = TextCleaner(config)

# Chunker - 自动读取 chunker.*
chunker = RecursiveChunker(config)

# Deduper - 自动读取 deduper.*
deduper = Deduper(config)

# Encoder - 自动读取 encoder.*
encoder = BGEEncoder(config)

# VectorStore - 自动读取 vector_store.*
vector_store = ChromaStore(config)

# Retriever - 自动读取 retriever.*
retriever = VectorRetriever(config, vector_store)

# 4. 执行流程
logger.info("开始处理文档...")

# 加载文档
docs = loader.load_directory(config_manager.get('paths.input_dir'))

# 清洗
cleaned_docs = [cleaner.clean(doc['content']) for doc in docs]

# 分块
chunks = chunker.chunk_batch(cleaned_docs)

# 去重
dedup_result = deduper.deduplicate(chunks)

# 编码
embeddings = encoder.encode_batch([c.text for c in dedup_result.unique_chunks])

# 存储
vector_store.add(
    ids=[c.id for c in dedup_result.unique_chunks],
    embeddings=embeddings,
    contents=[c.text for c in dedup_result.unique_chunks],
    metadatas=[c.metadata for c in dedup_result.unique_chunks]
)

logger.info("处理完成！")
```

### 命令行覆盖配置

```python
# main.py
import click
from src.configs import ConfigManager

@click.command()
@click.option('--config', '-c', help='配置文件路径')
@click.option('--chunk-size', type=int, help='覆盖分块大小')
@click.option('--top-k', type=int, help='覆盖检索数量')
def build(config, chunk_size, top_k):
    # 加载配置
    config_manager = ConfigManager(config)
    
    # 命令行参数覆盖配置文件
    if chunk_size:
        config_manager.set('chunker.chunk_size', chunk_size)
    if top_k:
        config_manager.set('retriever.top_k', top_k)
    
    # 使用配置
    config = config_manager._config
    # ...
```

## 配置优先级

1. **命令行参数** (最高优先级)
2. **用户指定的配置文件** (`--config`)
3. **全局配置文件** (`./configs.yaml`)
4. **默认配置** (`src/configs/default_config.yaml`)
5. **代码中的默认值** (最低优先级)

## 添加新配置项

### 1. 在 configs.yaml 中添加

```yaml
module_name:
  new_key: "value"
  nested:
    key: 123
```

### 2. 在模块中读取

```python
class MyModule:
    def __init__(self, config):
        self.config = config or {}
        
        # 读取模块配置
        module_config = self.config.get('module_name', self.config)
        
        # 读取具体配置
        self.new_key = module_config.get('new_key', 'default')
        self.nested_key = module_config.get('nested', {}).get('key', 0)
```

### 3. 添加默认值到 default_config.yaml

```yaml
module_name:
  new_key: "default_value"
  nested:
    key: 0
```

## 环境特定配置

### 开发环境

```yaml
# configs.dev.yaml
logging:
  level: "DEBUG"

encoder:
  model:
    device: "cpu"  # 开发环境使用CPU
```

### 生产环境

```yaml
# configs.prod.yaml
logging:
  level: "WARNING"

encoder:
  model:
    device: "cuda"  # 生产环境使用GPU

deduper:
  strategy: "production"  # 生产环境使用完整去重
```

### 使用环境配置

```bash
# 开发环境
python -m src.main build --config configs.dev.yaml

# 生产环境
python -m src.main build --config configs.prod.yaml
```

## 配置验证

```python
from src.configs import ConfigManager

class ConfigValidator:
    @staticmethod
    def validate(config_manager: ConfigManager) -> bool:
        """验证配置是否完整有效"""
        required_keys = [
            'paths.input_dir',
            'paths.output_dir',
            'encoder.model.name',
            'vector_store.chroma.persist_directory',
        ]
        
        for key in required_keys:
            if config_manager.get(key) is None:
                raise ValueError(f"缺少必需配置项: {key}")
        
        return True

# 使用
config_manager = ConfigManager("configs.yaml")
ConfigValidator.validate(config_manager)
```

## 注意事项

1. **向后兼容**: 模块应同时支持直接传入配置字典和从 `configs.yaml` 读取
2. **默认值**: 所有配置项都应有合理的默认值
3. **类型检查**: 重要配置项应进行类型检查
4. **文档**: 新增配置项需同步更新本文档
