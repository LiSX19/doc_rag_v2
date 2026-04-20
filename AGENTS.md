# ==================== 整体架构与模块化设计 ====================
1. 模块化设计：每个核心模块（Loader、Cleaner、Chunker、Deduper、Embedder、VectorStore、Retriever、Evaluator）独立为类或函数，便于单元测试和替换。
2. 配置化管理：使用YAML/JSON配置文件统一管理参数（分块大小、重叠长度、去重阈值、模型路径等）。
3. 日志与监控：集成结构化日志（logging模块），记录各阶段耗时、处理文档数、去重率等。
4. 错误处理与重试：对文件解析、网络请求等可能失败的步骤添加异常捕获、重试机制和降级策略。
5. 增量更新：记录已处理文件的哈希或时间戳，支持增量添加文档，避免全量重建。
6. 缓存中间结果：将解析后的文本、分块结果、Embedding向量缓存到磁盘或Redis，加速重复处理。

# ==================== 文档加载与解析（Loader & Parser） ====================
核心工具：Unstructured + PaddleOCR(子进程) + caj2pdf + pywin32
支持格式：.pdf / .docx / .doc / .wps / .xlsx / .xls / .pptx / .ppt / .ppsx / .caj / .txt / .md / .csv / .html / .htm / .rtf / .json / .xml

解析策略（优先级降序）：
- PDF: Unstructured → OCR子进程（双环境隔离）
- Word: Unstructured → python-docx(.docx) / pywin32(.doc/.wps)
- Excel: Unstructured → openpyxl(.xlsx) / xlrd(.xls)
- PPT: Unstructured → python-pptx(.pptx) / pywin32(.ppt/.ppsx)
- CAJ: caj2pdf → PDFLoader
- 其他: 专用加载器

优化特性：
- 文件大小过滤（默认>1KB）
- 并行处理（multiprocessing）
- pywin32自动重试（RPC错误处理）
- OCR进度监控（无超时限制）
- 统一输出格式（content/metadata/pages）

详细文档：./docs/loader_module.md

# ==================== 文本清洗（Clean） ====================
核心工具：Unstructured（结构清洗）+ ftfy（编码修复）+ opencc（繁简统一）+ 自定义规则（业务噪声）

优化增强：
1. 自定义清洗规则引擎：允许用户通过配置文件或DSL定义业务噪声规则（如正则表达式替换），无需修改代码。
2. 清洗流水线：将多个清洗步骤按顺序组合（结构清洗→编码修复→繁简统一→自定义规则），支持配置启用/禁用步骤。
3. 质量检查：清洗后检查文本长度、字符集等，确保清洗未过度删除内容。
4. 并行清洗：对多个文档并行执行清洗操作。

# ==================== 文本分块（Chunking） ====================
基础工具：LangChain Text Splitter（RecursiveCharacterTextSplitter/TokenTextSplitter）

优化增强：
1. 中文分块策略优化：调整分隔符列表为["\n\n", "\n", "。", "；", "，", " ", ""]以适应中文标点。
2. 语义分块增强：集成句子嵌入模型（如BGE），计算句子间相似度，在语义边界处进行分割，减少跨段落分割。
3. 分块参数动态调优：根据文档类型（技术文档、法律文书）动态调整分块大小、重叠长度。
4. 分块后处理：过滤过短的块、合并相邻的短块，保持块的完整性。
5. 并行分块：对多个文档并行执行分块操作。

# ==================== 文本块去重（Dedup） ====================
基础策略：
- 测试环境：MD5/SHA256 + SimHash
- 生产环境：MD5/SHA256 + SimHash + BGE Embedding

优化增强：
1. 多级去重流水线：设计多级去重（哈希 → SimHash → Embedding）并管理阈值。
2. 近似去重加速：引入局部敏感哈希（LSH）或Faiss进行近似去重，平衡速度与准确率。
3. 相似度计算与聚类：基于Embedding计算余弦相似度，使用聚类算法（如DBSCAN）或最近邻搜索找出重复块。
4. 去重策略：支持保留第一个出现的块，或合并重复块的内容。
5. 性能优化：对大量文本块使用Faiss或Annoy进行快速相似度搜索。

# ==================== Embedding模型 ====================
核心模型：BGE (BAAI)
本地路径模型：BAAI/bge-small-zh-v1.5, BAAI/bge-base-zh-v1.5

优化增强：
1. 模型管理：根据配置选择模型路径，处理模型加载失败的情况。
2. 批量处理与GPU加速：使用sentence-transformers的encode()批处理功能，支持GPU加速。
3. 多模型支持：预留接口接入OpenAI Embeddings、Cohere、自定义模型等。
4. Embedding缓存：将生成的向量缓存到磁盘或Redis，避免重复计算。
5. 模型版本控制：对Embedding模型版本进行标记，便于回滚和实验对比。

# ==================== 向量数据库（Vector Store） ====================
核心工具：Chroma

优化增强：
1. 向量存储抽象层：定义统一接口，未来可轻松切换至Pinecone、Weaviate、Qdrant等。
2. 索引参数调优：根据数据量和查询需求调整HNSW参数（hnsw:space、hnsw:construction_ef等）。
3. 增量更新支持：支持向现有集合中添加新文档，无需重建整个索引。
4. 数据库初始化与连接管理：创建/连接数据库，设置集合名称、元数据等。
5. 数据插入与更新：将文本块、Embedding向量、元数据批量插入，支持增量更新。

# ==================== 检索与重排序（Retrieval & Rerank） ====================
基础工具：Chroma（向量检索）+ BGE Reranker（重排序）

优化增强：
1. 检索策略增强：实现多路检索（关键词+向量）、混合搜索等。
2. 重排序流水线：将检索结果传递给重排序模型（FlagModel或CrossEncoder），综合原始分数与重排序分数。
3. 结果过滤与分页：根据置信度阈值过滤结果，支持分页返回。
4. 检索缓存：对常见查询结果进行缓存，提升响应速度。
5. 检索质量监控：对线上检索结果进行采样评估，及时发现模型退化。

# ==================== 评估与监控 ====================
基础工具：RAGAS（RAG Assessment）

优化增强：
1. 多维度评估：除了RAGAS，集成自定义指标（检索精度、召回率、响应延迟）和业务相关指标。
2. 评估数据集构建：支持准备带标注的问答对或人工评估数据。
3. 实时质量监控：对线上检索结果进行采样评估，生成可视化报告（使用matplotlib或plotly）。
4. A/B测试支持：设计实验框架，对比不同分块策略、去重方法、重排序模型的效果。
5. 监控仪表板：集成Prometheus+Grafana，实时显示系统性能指标（处理速度、内存使用、错误率等）。

# ==================== 程序接口 ====================
## 运行方式
python doc_rag.py [命令] [参数]

## 命令行界面设计
使用argparse或click库构建命令行参数解析，支持子命令模式：

### 全局参数
- `--config`：配置文件路径（YAML/JSON格式）
- `--verbose`：详细输出模式
- `--log-level`：日志级别（DEBUG/INFO/WARNING/ERROR）
- `--log-file`：日志文件路径
- `--version`：显示版本信息
- `--help`：显示帮助信息

### 1. 构建模式（build）
构建知识库，处理文档并生成向量索引。

**参数：**
- `--input-dir`：输入文件夹路径（默认：F:\test）
- `--file-limit`：文件数量限制（默认：全部）
- `--skip-loading`：跳过文档加载，使用数据库中已有的文本块
- `--dedup-strategy`：去重策略（test/production/skip，默认：test）
  - `test`：测试环境策略（MD5/SHA256 + SimHash）
  - `production`：生产环境策略（MD5/SHA256 + SimHash + BGE Embedding）
  - `skip`：跳过去重模块
- `--embedding-model`：Embedding模型选择（bge-small-zh-v1.5/bge-base-zh-v1.5，默认：bge-small-zh-v1.5）
- `--skip-embedding`：跳过向量嵌入模块
- `--incremental`：增量更新模式，只处理新增或修改的文件
- `--chunk-size`：分块大小（默认：500）
- `--chunk-overlap`：分块重叠长度（默认：50）
- `--output-dir`：输出目录路径（默认：.\outputs）
- `--clean-cache`：清理缓存文件

**示例：**
```bash
# 完整构建流程
python doc_rag.py build --input-dir F:\documents --dedup-strategy production --embedding-model bge-base-zh-v1.5

# 增量更新
python doc_rag.py build --input-dir F:\documents --incremental

# 跳过文档加载，使用已有文本块
python doc_rag.py build --skip-loading --dedup-strategy test
```

### 2. 检索模式（retrieve）
检索知识库，获取相关文档片段。

**参数：**
- `--query`：查询问题（必需）
- `--top-k`：返回结果数量（默认：5）
- `--rerank`：启用重排序（默认：true）
- `--rerank-model`：重排序模型（默认：BGE Reranker）
- `--output-format`：输出格式（json/text，默认：text）
- `--threshold`：相似度阈值（默认：0.5）
- `--include-metadata`：包含元数据信息
- `--save-results`：保存检索结果到文件

**示例：**
```bash
# 简单检索
python doc_rag.py retrieve --query "什么是机器学习？"

# 高级检索
python doc_rag.py retrieve --query "深度学习应用场景" --top-k 10 --rerank --output-format json
```

### 3. 评估模式（evaluate）
评估RAG系统性能。

**参数：**
- `--eval-dataset`：评估数据集路径（JSON/CSV格式）
- `--metrics`：评估指标（ragas/custom/all，默认：ragas）
- `--output-report`：评估报告输出路径（默认：.\outputs\eval_report.json）
- `--visualize`：生成可视化图表
- `--compare-baseline`：与基线结果对比
- `--sample-size`：采样数量（默认：全部）

**示例：**
```bash
# 使用RAGAS评估
python doc_rag.py evaluate --eval-dataset .\data\eval_questions.json --metrics ragas

# 自定义评估
python doc_rag.py evaluate --eval-dataset .\data\eval_questions.json --metrics custom --visualize
```

### 4. 其他命令
- `init`：初始化项目配置和目录结构
- `status`：显示系统状态和统计信息
- `clean`：清理临时文件和缓存
- `export`：导出向量数据库内容


# ==================== 文件规范 ====================
## 1. 项目结构组织
```
doc_rag/
├── src/                          # 源代码目录
│   ├── loaders/                  # 文档加载器模块
│   │   ├── base.py               # 加载器基类
│   │   ├── document_loader.py    # 文档加载统一入口
│   │   ├── loader_factory.py     # 加载器工厂
│   │   ├── pdf_loader.py         # PDF加载器
│   │   ├── word_loader.py        # Word加载器
│   │   ├── excel_loader.py       # Excel加载器
│   │   ├── ppt_loader.py         # PPT加载器
│   │   ├── caj_loader.py         # CAJ加载器
│   │   ├── html_loader.py        # HTML加载器
│   │   ├── text_loader.py        # 文本加载器
│   │   ├── rtf_loader.py         # RTF加载器
│   │   └── caj2pdf/              # CAJ转PDF工具
│   ├── cleaners/                 # 文本清洗模块
│   │   ├── base.py               # 清洗器基类
│   │   └── text_cleaner.py       # 文本清洗实现
│   ├── chunkers/                 # 文本分块模块
│   │   ├── base.py               # 分块器基类
│   │   └── recursive_chunker.py  # 递归分块实现
│   ├── dedupers/                 # 去重模块
│   │   ├── base.py               # 去重器基类
│   │   └── deduper.py            # 多级去重实现
│   ├── embedders/                # Embedding模块
│   │   ├── base.py               # Embedder基类
│   │   └── bge_embedder.py       # BGE模型实现
│   ├── vector_stores/            # 向量数据库模块
│   │   ├── base.py               # 向量存储基类
│   │   └── chroma_store.py       # Chroma实现
│   ├── retrievers/               # 检索模块
│   │   ├── base.py               # 检索器基类
│   │   └── vector_retriever.py   # 向量检索实现
│   ├── evaluators/               # 评估模块
│   │   ├── base.py               # 评估器基类
│   │   └── ragas_evaluator.py    # RAGAS评估实现
│   ├── utils/                    # 工具模块
│   │   ├── logger.py             # 日志工具
│   │   ├── file_utils.py         # 文件工具
│   │   ├── output_manager.py     # 输出管理器
│   │   └── incremental_tracker.py # 增量更新追踪器
│   ├── configs/                  # 配置文件
│   │   ├── config_manager.py     # 配置管理器
│   │   ├── default_config.yaml   # 默认配置
│   │   └── production_config.yaml # 生产配置
│   └── main.py                   # 主程序入口
├── tests/                        # 测试脚本与输出
│   ├── unit/                     # 单元测试
│   ├── outputs/                  # 测试输出
│   └── test_*.py                 # 测试脚本
├── models/                       # 模型文件目录
│   ├── bge-small-zh-v1.5/        # BGE小模型
│   └── bge-base-zh-v1.5/         # BGE基础模型
├── cache/                        # 缓存目录
│   ├── file_hashes.json          # 文件哈希记录（增量更新）
│   └── file_timestamps.json      # 文件时间戳记录
├── logs/                         # 日志文件目录
├── docs/                         # 项目文档
│   ├── loader_module.md          # 加载器模块文档
│   ├── output_control.md         # 输出控制文档
│   └── incremental_update.md     # 增量更新文档
├── data/                         # 数据文件目录
├── scripts/                      # 辅助脚本
├── requirements.txt              # 主环境依赖 (RAG)
├── requirements-ocr.txt          # OCR环境依赖 (OCR)
├── README.md                     # 项目说明
├── configs.yaml                  # 全局配置文件
└── .gitignore                    # Git忽略文件
```

## 2. 文件命名规范
### 中间输出文件
- 清洗后的文本：`{文件名}.cleaned.txt`
- 分块列表：`{文件名}.chunks.json`
- 去重报告：`{文件名}.dedup_report.json`
- Embedding向量：`{文件名}.embeddings.npy`
- 检索结果：`{查询哈希}.retrieval_results.json`
- 评估报告：`{时间戳}.eval_report.json`

### 配置文件
- 主配置文件：`config.yaml`
- 模型配置：`model_config.yaml`
- 清洗规则配置：`cleaning_rules.yaml`

## 3. 模块化设计原则
1. **单一职责**：每个模块/类只负责一个特定功能
2. **接口分离**：模块间通过明确定义的接口通信
3. **依赖注入**：通过配置注入依赖，便于测试和替换
4. **错误隔离**：模块错误不影响其他模块运行

## 4. 测试规范
1. **单元测试**：为每个核心函数/类编写单元测试，覆盖率>80%
2. **集成测试**：测试模块间的集成和端到端流程
3. **测试数据**：使用./data/目录下的测试样本进行测试
4. **测试输出**：测试结果保存在`tests/outputs/`目录，便于验收
5. **验收标准**：每个模块必须有明确的验收标准和输出文件

## 5. 输出文件要求
每个关键处理步骤必须生成可验收的输出文件：
1. **文档加载**：原始文本文件（.raw.txt）
2. **文本清洗**：清洗后的文本文件（.cleaned.txt）
3. **文本分块**：分块列表JSON文件（.chunks.json），包含分块文本和元数据
4. **文本去重**：去重报告JSON文件（.dedup_report.json），包含重复块统计
5. **向量嵌入**：Embedding向量文件（.embeddings.npy）和元数据文件（.embeddings_meta.json）
6. **向量存储**：向量数据库导出文件（.chroma_export.zip）
7. **检索结果**：检索结果JSON文件（.retrieval.json），包含查询、结果、分数
8. **评估报告**：评估报告JSON文件（.eval_report.json），包含各项指标得分

