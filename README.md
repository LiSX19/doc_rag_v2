# DocRAG - 文档RAG系统

一个模块化、可配置的文档检索增强生成（RAG）系统，支持多种文档格式、智能文本处理、向量检索和评估。

## 功能特性

- **多格式文档支持**：PDF、Word、Excel、PPT、TXT、Markdown、CAJ等
- **智能文档解析**：Unstructured + PaddleOCR + 自定义解析器
- **文本清洗流水线**：编码修复、繁简转换、自定义规则
- **智能分块策略**：递归分块、语义分块、中文优化
- **多级去重机制**：哈希 + SimHash + Embedding相似度
- **Embedding模型**：支持BGE系列模型，GPU加速
- **向量数据库**：Chroma，支持增量更新
- **混合检索**：向量检索 + 关键词检索 + 重排序
- **完整评估体系**：RAGAS + 自定义指标

## 项目结构

```
doc_rag/
├── src/                          # 源代码目录
│   ├── loaders/                  # 文档加载器模块
│   ├── cleaners/                 # 文本清洗模块
│   ├── chunkers/                 # 文本分块模块
│   ├── dedupers/                 # 去重模块
│   ├── embedders/                # Embedding模块
│   ├── vector_stores/            # 向量数据库模块
│   ├── retrievers/               # 检索模块
│   ├── evaluators/               # 评估模块
│   ├── configs/                  # 配置文件
│   ├── config_manager.py     # 配置管理器
│   ├── default_config.yaml   # 默认配置（完整配置，只读）
│   └── cleaning_rules.yaml   # 清洗规则
│   └── main.py                   # 主程序入口
├── tests/                        # 测试脚本与输出
│   ├── unit/                     # 单元测试
│   └── outputs/                  # 测试输出
├── outputs/                      # 中间结果和最终输出
│   ├── loaded/                   # 加载的原始文档
│   ├── cleaned/                  # 清洗后的文本
│   ├── chunks/                   # 分块结果
│   ├── embeddings/               # Embedding向量
│   ├── retrieval/                # 检索结果
│   └── evaluation/               # 评估报告
├── models/                       # 模型文件目录
├── logs/                         # 日志文件目录
├── docs/                         # 项目文档目录
│   ├── loader_module.md          # 加载器模块文档
│   ├── cleaner_module.md         # 清洗模块文档
│   ├── chunker_module.md         # 分块模块文档
│   ├── utils_module.md           # 工具模块文档
│   ├── config.md                 # 配置系统文档
│   ├── config_usage.md           # 配置使用指南
│   ├── output_control.md         # 输出控制文档
│   └── incremental_update.md     # 增量更新文档
├── data/                         # 数据文件目录
├── config.yaml                   # 用户配置文件（关键参数）
├── requirements.txt              # Python依赖
└── README.md                     # 项目说明
```

## 安装

### 环境要求

- Python 3.11+
- CUDA 11.8+ (可选，用于GPU加速)

### 安装步骤

1. 克隆仓库
```bash
git clone <repository-url>
cd doc_rag
```

2. 创建虚拟环境
```bash
conda create -n doc_rag python=3.11
conda activate doc_rag
```

3. 安装依赖
```bash
pip install -r requirements.txt
```

4. 下载模型（如本地不存在）
```bash
# BGE small模型
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-zh-v1.5', cache_folder='./models')"

# BGE base模型
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-base-zh-v1.5', cache_folder='./models')"
```

## 使用方法

### 1. 构建知识库

```bash
# 完整构建流程
python -m src.main build --input-dir F:\\documents --dedup-strategy production --embedding-model bge-base-zh-v1.5

# 增量更新
python -m src.main build --input-dir F:\\documents --incremental

# 跳过文档加载，使用已有文本块
python -m src.main build --skip-loading --dedup-strategy test
```

### 2. 检索知识库

```bash
# 简单检索
python -m src.main retrieve --query "什么是机器学习？"

# 高级检索
python -m src.main retrieve --query "深度学习应用场景" --top-k 10 --rerank --output-format json
```

### 3. 评估系统

```bash
# 使用RAGAS评估
python -m src.main evaluate --eval-dataset .\\data\\eval_questions.json --metrics ragas

# 自定义评估
python -m src.main evaluate --eval-dataset .\\data\\eval_questions.json --metrics custom --visualize
```

### 4. 其他命令

```bash
# 初始化项目配置
python -m src.main init

# 显示系统状态
python -m src.main status

# 清理临时文件
python -m src.main clean

# 导出向量数据库
python -m src.main export --output export.zip
```

## 配置说明

### 配置文件

- `configs.yaml` - 全局主配置文件
- `src/configs/default_config.yaml` - 默认配置（开发/测试环境）
- `src/configs/production_config.yaml` - 生产环境配置
- `src/configs/cleaning_rules.yaml` - 文本清洗规则

### 配置优先级

命令行参数 > 指定配置文件 > 默认配置

### 常用配置项

```yaml
# 文档加载
loader:
  parallel:
    enabled: true
    max_workers: 4

# 文本分块
chunker:
  chunk_size: 500
  chunk_overlap: 50
  strategy: "recursive"

# 去重策略
deduper:
  strategy: "test"  # test, production, skip

# Embedding模型
embedder:
  model:
    name: "BAAI/bge-small-zh-v1.5"
    device: "auto"  # auto, cpu, cuda

# 检索配置
retriever:
  top_k: 5
  rerank:
    enabled: true
```

## 模块说明

### 文档加载器 (Loaders)

支持格式：
- PDF (Unstructured / PaddleOCR)
- Word (.docx / .doc)
- Excel (.xlsx / .xls)
- PowerPoint (.pptx / .ppt)
- 文本 (.txt / .md / .csv)
- 网页 (.html / .htm)
- CAJ (caj2pdf转换)

### 文本清洗 (Cleaners)

清洗流程：
1. 结构清洗 - 移除页眉页脚、多余空白
2. 编码修复 - ftfy修复编码问题
3. 繁简转换 - OpenCC繁体转简体
4. 自定义规则 - 正则表达式替换

### 文本分块 (Chunkers)

分块策略：
- **递归分块** - 按分隔符层级递归分割
- **Token分块** - 按Token数量分割
- **语义分块** - 基于句子相似度分割

### 去重 (Dedupers)

去重级别：
- **哈希去重** - MD5/SHA256精确去重
- **SimHash** - 局部敏感哈希近似去重
- **Embedding去重** - 向量相似度去重

### Embedding (Embedders)

支持模型：
- BAAI/bge-small-zh-v1.5
- BAAI/bge-base-zh-v1.5
- 其他Sentence Transformers模型

### 向量数据库 (Vector Stores)

当前支持：
- Chroma (默认)

预留接口：
- Pinecone
- Weaviate
- Qdrant

### 检索器 (Retrievers)

检索策略：
- 向量检索
- 关键词检索
- 混合检索
- 重排序 (BGE Reranker)

### 评估器 (Evaluators)

评估指标：
- RAGAS (Faithfulness, Answer Relevancy, Context Precision, Context Recall)
- 检索精度/召回率
- 响应延迟

## 开发指南

### 添加新的文档加载器

```python
# src/loaders/custom_loader.py
from .base import BaseLoader

class CustomLoader(BaseLoader):
    def load(self, file_path: str) -> dict:
        # 实现加载逻辑
        pass
```

### 添加自定义清洗规则

在 `src/configs/cleaning_rules.yaml` 中添加：

```yaml
rules:
  - name: "my_custom_rule"
    description: "自定义规则描述"
    pattern: "正则表达式"
    replacement: "替换内容"
    enabled: true
    priority: 100
```

### 运行测试

```bash
# 运行所有测试
pytest tests/

# 运行单元测试
pytest tests/unit/

# 生成覆盖率报告
pytest --cov=src tests/
```

## 性能优化

### 并行处理

- 文档加载并行化
- 文本清洗并行化
- 分块处理并行化
- Embedding批量处理

### 缓存机制

- 文件哈希缓存（增量更新）
- Embedding向量缓存
- 检索结果缓存

### 内存管理

- 流式处理大文件
- 分块加载Embedding
- 定期垃圾回收

## 常见问题

### Q: 如何处理PDF解析失败？

A: 系统会自动降级到OCR处理。可以在配置中启用OCR：
```yaml
loader:
  ocr:
    enabled: true
    engine: "paddleocr"
```

### Q: 如何支持更多文件格式？

A: 实现自定义加载器并注册到加载器工厂：
```python
from src.loaders import loader_factory
from src.loaders.custom_loader import CustomLoader

loader_factory.register(".ext", CustomLoader)
```

### Q: 如何切换向量数据库？

A: 修改配置中的vector_store类型，并实现对应的存储适配器。

## 许可证

[MIT License](LICENSE)

## 贡献指南

欢迎提交Issue和Pull Request！

## 联系方式

如有问题，请提交GitHub Issue。
