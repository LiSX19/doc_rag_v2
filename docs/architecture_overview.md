# DocRAG 项目架构概览文档

## 目录
1. [项目概述](#项目概述)
2. [系统架构图](#系统架构图)
3. [模块组件概述](#模块组件概述)
4. [数据处理流程](#数据处理流程)
5. [配置管理](#配置管理)
6. [性能优化](#性能优化)
7. [扩展开发](#扩展开发)
8. [部署与运维](#部署与运维)

---

## 项目概述

### 项目定位
DocRAG（Document Retrieval-Augmented Generation）是一个基于检索增强生成的文档处理系统，专为中文文档优化设计。系统能够从多种格式的文档中提取、处理和索引文本内容，构建可检索的知识库，支持智能问答和信息检索。

### 核心功能
1. **多格式文档支持**: 支持PDF、Word、Excel、PPT、CAJ等18种文档格式
2. **智能文本处理**: 提供清洗、分块、去重、编码的完整处理流水线
3. **向量知识库**: 构建基于向量的语义检索系统
4. **RAG评估**: 使用RAGAS框架评估检索质量
5. **增量更新**: 智能识别和处理新增或修改的文档
6. **可扩展架构**: 模块化设计，支持自定义处理阶段

### 技术栈
- **编程语言**: Python 3.8+
- **向量数据库**: ChromaDB
- **机器学习**: Hugging Face Transformers, Sentence-BERT
- **文档解析**: Unstructured, PyPDF2, python-docx
- **并行处理**: concurrent.futures, ThreadPoolExecutor
- **配置管理**: YAML配置文件，分层配置结构

---

## 系统架构图

### 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         DocRAG 系统架构                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │  输入层     │    │  处理层     │    │  存储层     │         │
│  │  ────────   │    │  ────────   │    │  ────────   │         │
│  │ • 文件扫描  │───▶│ • 文档加载  │───▶│ • 向量编码  │──┐      │
│  │ • 格式检测  │    │ • 文本清洗  │    │ • 向量存储  │  │      │
│  │ • 增量检查  │    │ • 文本分块  │    │ • 索引构建  │  │      │
│  └─────────────┘    │ • 文本去重  │    └─────────────┘  │      │
│                     └─────────────┘                   │      │
│                                                       │      │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │      │
│  │  检索层     │    │  评估层     │    │  应用层     │  │      │
│  │  ────────   │    │  ────────   │    │  ────────   │  │      │
│  │ • 向量检索  │◀───│ • RAG评估   │◀───│ • 查询接口  │◀─┘      │
│  │ • 重排序    │    │ • 指标计算  │    │ • 结果展示  │         │
│  │ • 结果过滤  │    │ • 报告生成  │    │ • API服务   │         │
│  └─────────────┘    └─────────────┘    └─────────────┘         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 数据流架构

```
原始文档
    │
    ▼
┌─────────────────┐
│   输入管理       │◀── 增量更新检查
│   • 文件扫描     │
│   • 格式过滤     │
│   • 优先级排序   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   文档处理流水线  │
│   ┌───────────┐ │
│   │ 文档加载   │─┼── 多格式解析
│   └───────────┘ │
│   ┌───────────┐ │
│   │ 文本清洗   │─┼── 结构清洗/编码修复
│   └───────────┘ │
│   ┌───────────┐ │
│   │ 文本分块   │─┼── 语义分块/元数据提取
│   └───────────┘ │
│   ┌───────────┐ │
│   │ 文本去重   │─┼── 多级去重算法
│   └───────────┘ │
│   ┌───────────┐ │
│   │ 向量编码   │─┼── 稠密/稀疏/混合编码
│   └───────────┘ │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   向量知识库     │
│   • 向量存储     │
│   • 索引构建     │
│   • 相似度检索   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   检索与评估     │
│   • 查询处理     │
│   • 结果重排序   │
│   • 质量评估     │
└────────┬────────┘
         │
         ▼
   应用输出
```

### 模块依赖关系

```
                    ┌──────────────┐
                    │   Pipeline   │
                    │   Manager    │
                    └──────┬───────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
    ┌────▼────┐      ┌────▼────┐      ┌─────▼─────┐
    │  Loader │      │ Cleaner │      │  Chunker  │
    └────┬────┘      └────┬────┘      └─────┬─────┘
         │                 │                 │
    ┌────▼─────────────────▼─────────────────▼────┐
    │              Chunk Manager                   │
    └────────────────────┬─────────────────────────┘
                         │
                    ┌────▼────┐
                    │ Deduper │
                    └────┬────┘
                         │
                    ┌────▼────┐
                    │ Encoder │
                    └────┬────┘
                         │
                    ┌────▼───────┐
                    │ Vector     │
                    │ Store      │
                    └────┬───────┘
                         │
                    ┌────▼────┐
                    │Retriever│
                    └────┬────┘
                         │
                    ┌────▼────┐
                    │Evaluator│
                    └─────────┘
```

---

## 模块组件概述

### 1. 输入层模块

| 模块 | 功能描述 | 核心类 |
|------|----------|--------|
| **Pipeline Manager** | 整体流程协调，模块生命周期管理 | `PipelineManager`, `build_pipeline()` |
| **文件扫描器** | 扫描输入目录，过滤支持格式，增量检查 | `FileScanner`, `IncrementalTracker` |
| **任务管理器** | 管理处理任务，错误恢复，进度追踪 | `TaskFileManager`, `ProgressTracker` |

### 2. 处理层模块

| 模块 | 功能描述 | 核心类 |
|------|----------|--------|
| **文档加载器 (Loader)** | 多格式文档解析，元数据提取 | `DocumentLoader`, `BaseLoader` |
| **文本清洗器 (Cleaner)** | 文本清洗和规范化 | `TextCleaner`, `BaseCleaner` |
| **文本分块器 (Chunker)** | 文本分割为语义块 | `RecursiveChunker`, `BaseChunker` |
| **分块管理器** | 分块数据库管理，增量更新 | `ChunkManager` |
| **去重器 (Deduper)** | 多级文本去重 | `Deduper`, `BaseDeduper` |
| **编码器 (Encoder)** | 文本向量化编码 | `BGEEncoder`, `BaseEncoder` |

### 3. 存储层模块

| 模块 | 功能描述 | 核心类 |
|------|----------|--------|
| **向量存储 (Vector Store)** | 向量数据库操作 | `ChromaStore`, `BaseVectorStore` |
| **缓存管理器** | 编码缓存，文件哈希缓存 | `CacheManager` |
| **输出管理器** | 处理结果输出和报告 | `OutputManager` |

### 4. 检索层模块

| 模块 | 功能描述 | 核心类 |
|------|----------|--------|
| **检索器 (Retriever)** | 向量检索，结果重排序 | `VectorRetriever`, `BaseRetriever` |
| **评估器 (Evaluator)** | RAG系统质量评估 | `RAGASEvaluator`, `BaseEvaluator` |

### 5. 工具模块

| 模块 | 功能描述 | 核心类/函数 |
|------|----------|-------------|
| **配置管理** | 分层配置管理 | `ConfigManager` |
| **日志系统** | 结构化日志记录 | `get_logger()` |
| **工具函数** | 通用工具函数 | `FileUtils`, `TextUtils` |
| **异常处理** | 统一异常处理 | `DocRAGError`, 各模块异常类 |

---

## 数据处理流程

### 1. 完整处理流程

```python
# 1. 初始化Pipeline管理器
manager = PipelineManager()

# 2. 构建知识库
stats = manager.build_knowledge_base(
    input_dir="./data/documents",
    incremental=True,
    file_limit=100
)

# 3. 执行检索
query = "人工智能的应用领域有哪些?"
results = manager.retrieve(query, top_k=5)

# 4. 评估系统
evaluation = manager.evaluate(
    questions=["问题1", "问题2"],
    contexts=[["上下文1"], ["上下文2"]],
    answers=["答案1", "答案2"]
)
```

### 2. 各阶段数据格式转换

```
原始文档 (各种格式)
    │
    ▼
加载阶段 → Document对象
    │   • content: str (文本内容)
    │   • metadata: dict (元数据)
    │   • file_path: Path (文件路径)
    │
    ▼
清洗阶段 → 清洗后文本
    │   • 规范化文本结构
    │   • 修复编码问题
    │   • 繁简转换
    │
    ▼
分块阶段 → TextChunk列表
    │   • chunk_id: str (块ID)
    │   • content: str (块内容)
    │   • metadata: dict (块元数据)
    │   • file_id: str (文件ID)
    │
    ▼
去重阶段 → DedupResult对象
    │   • chunks: List[TextChunk] (唯一块)
    │   • removed_chunks: List[TextChunk] (重复块)
    │   • stats: dict (统计信息)
    │
    ▼
编码阶段 → EncodedVector对象
    │   • chunk_id: str (块ID)
    │   • dense_vector: Optional[np.ndarray] (稠密向量)
    │   • sparse_vector: Optional[dict] (稀疏向量)
    │   • metadata: dict (编码元数据)
    │
    ▼
存储阶段 → 向量数据库记录
    │   • id: str (向量ID)
    │   • embedding: List[float] (向量)
    │   • document: str (文档内容)
    │   • metadata: dict (元数据)
    │
    ▼
检索阶段 → SearchResult对象
    │   • content: str (内容)
    │   • score: float (相似度分数)
    │   • metadata: dict (元数据)
    │   • chunk_id: str (块ID)
```

### 3. 增量更新流程

```python
# 增量更新算法
def incremental_update(input_dir):
    # 1. 扫描输入目录
    all_files = scan_files(input_dir)
    
    # 2. 过滤已处理文件（基于哈希或时间戳）
    new_files = filter_new_or_modified_files(all_files)
    
    if not new_files:
        return {"status": "no_changes", "files_processed": 0}
    
    # 3. 处理新文件
    stats = process_files(new_files)
    
    # 4. 更新哈希记录
    update_hash_records(new_files)
    
    # 5. 优化向量索引
    optimize_vector_index()
    
    return stats
```

---

## 配置管理

### 1. 配置结构层次

```
配置来源 (优先级从低到高)
├── default_config.yaml (全局默认配置)
├── config.yaml (用户配置)
├── 命令行参数
└── 代码中硬编码默认值
```

### 2. 主要配置分类

```yaml
# 路径配置
paths:
  input_dir: "./data"
  output_dir: "./outputs"
  models_dir: "./models"
  cache_dir: "./cache"

# 模块配置
loader:
  parallel:
    enabled: true
    max_workers: 4

cleaner:
  pipeline: ["structure", "encoding", "simplified"]

chunker:
  chunk_size: 500
  chunk_overlap: 50

encoder:
  type: "dense"  # dense/sparse/hybrid
  dense:
    model_name: "BAAI/bge-small-zh-v1.5"

# 性能配置
performance:
  incremental_update:
    enabled: true
    hash_file: "./cache/file_hashes.json"
```

### 3. 配置读取模式

```python
from src.configs import ConfigManager

# 初始化配置管理器
config = ConfigManager()

# 1. 点号分隔读取
input_dir = config.get('paths.input_dir')

# 2. 带默认值读取
chunk_size = config.get('chunker.chunk_size', 500)

# 3. 获取模块配置
loader_config = config.get('loader', {})

# 4. 获取所有配置
all_config = config.get_all()
```

---

## 性能优化

### 1. 并行处理策略

```python
# 文件级并行
def process_files_parallel(files, max_workers=4):
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for file in files:
            future = executor.submit(process_single_file, file)
            futures.append(future)
        
        results = []
        for future in as_completed(futures):
            results.append(future.result())
    
    return results

# 批处理优化
def encode_batch(chunks, batch_size=32):
    """批量编码优化"""
    encoded_vectors = []
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]
        batch_vectors = encoder.encode_batch(batch)
        encoded_vectors.extend(batch_vectors)
    
    return encoded_vectors
```

### 2. 缓存机制

```
缓存层次结构：
├── 文件哈希缓存 (file_hashes.json)
│   ├── 避免重复处理相同文件
│   └── 支持增量更新
├── 编码向量缓存 (cache/encodings/)
│   ├── 避免重复编码相同文本
│   └── 加速相似查询处理
├── 检索结果缓存
│   ├── 缓存频繁查询结果
│   └── TTL过期策略
└── 模型缓存
    ├── Hugging Face模型缓存
    └── 本地模型文件缓存
```

### 3. 内存管理

```python
class MemoryAwareProcessor:
    """内存感知处理器"""
    
    def __init__(self, max_memory_mb=4096):
        self.max_memory_mb = max_memory_mb
    
    def process_large_dataset(self, dataset):
        """处理大型数据集（内存优化）"""
        batch_size = self.calculate_optimal_batch_size()
        
        for i in range(0, len(dataset), batch_size):
            batch = dataset[i:i+batch_size]
            
            # 处理当前批次
            processed_batch = self.process_batch(batch)
            
            # 立即释放内存
            del batch
            gc.collect()
            
            yield processed_batch
```

### 4. 索引优化

```python
# 向量索引优化策略
def optimize_vector_store(vector_store):
    """优化向量存储性能"""
    
    # 1. 重建索引（定期执行）
    vector_store.rebuild_index()
    
    # 2. 压缩向量（减少存储空间）
    vector_store.compress_vectors(compression_rate=0.5)
    
    # 3. 清理过期数据
    vector_store.cleanup_old_vectors(days=30)
    
    # 4. 统计信息更新
    vector_store.update_statistics()
```

---

## 扩展开发

### 1. 添加新的文档格式支持

```python
from src.loaders.base import BaseLoader

class CustomFormatLoader(BaseLoader):
    """自定义格式加载器"""
    
    def __init__(self, config=None):
        super().__init__(config)
        self.supported_extensions = ['.custom']
    
    def load(self, file_path: Path) -> Optional[Document]:
        """加载自定义格式文档"""
        try:
            # 解析自定义格式
            content = self._parse_custom_format(file_path)
            
            # 提取元数据
            metadata = self._extract_metadata(file_path)
            
            return Document(
                content=content,
                metadata=metadata,
                file_path=file_path
            )
        except Exception as e:
            self.logger.error(f"加载失败: {file_path}, 错误: {e}")
            return None
    
    def _parse_custom_format(self, file_path: Path) -> str:
        """解析自定义格式的具体实现"""
        # 实现解析逻辑
        pass
```

### 2. 添加新的编码器类型

```python
from src.encoders.base import BaseEncoder

class CustomEncoder(BaseEncoder):
    """自定义编码器"""
    
    def __init__(self, config=None):
        super().__init__(config)
        self.model = self._load_model()
    
    def encode(self, text: str, chunk_id: str = None) -> EncodedVector:
        """编码单个文本"""
        # 实现编码逻辑
        vector = self.model.encode(text)
        
        return EncodedVector(
            chunk_id=chunk_id or generate_chunk_id(text),
            dense_vector=vector,
            metadata={
                'encoder_type': 'custom',
                'model_version': '1.0'
            }
        )
    
    def encode_batch(self, texts: List[str]) -> List[EncodedVector]:
        """批量编码"""
        # 实现批量编码优化
        pass
```

### 3. 自定义Pipeline阶段

```python
from src.pipeline import build_pipeline

def enhanced_pipeline(files_to_process, config, modules, custom_stages=None):
    """增强版Pipeline，支持自定义阶段"""
    
    # 标准处理阶段
    results = build_pipeline(files_to_process, config, modules)
    
    # 添加自定义处理阶段
    if custom_stages:
        for stage_name, stage_func in custom_stages.items():
            print(f"执行自定义阶段: {stage_name}")
            results = stage_func(results)
    
    return results

# 使用自定义Pipeline
custom_stages = {
    'post_processing': post_process_results,
    'quality_check': check_quality,
    'report_generation': generate_report
}

results = enhanced_pipeline(files, config, modules, custom_stages)
```

### 4. 插件系统架构

```
插件系统设计：
├── 插件管理器 (PluginManager)
│   ├── 插件发现和加载
│   ├── 依赖关系解析
│   └── 生命周期管理
├── 插件接口定义
│   ├── LoaderPlugin (文档加载插件)
│   ├── CleanerPlugin (清洗插件)
│   ├── EncoderPlugin (编码插件)
│   └── RetrieverPlugin (检索插件)
└── 插件配置
    ├── 插件元数据 (plugin.yaml)
    ├── 依赖声明
    └── 配置参数定义
```

---

## 部署与运维

### 1. 部署架构

```
生产环境部署架构：
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web前端/API    │───▶│   DocRAG服务     │───▶│   向量数据库     │
│   • 用户界面     │    │   • Pipeline    │    │   • ChromaDB    │
│   • REST API    │    │   • 检索服务     │    │   • 持久化存储   │
│   • 身份认证     │◀───│   • 缓存服务     │◀───│   • 备份恢复     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   对象存储       │    │   模型服务       │    │   监控系统       │
│   • 文档存储     │    │   • 模型仓库     │    │   • 性能指标     │
│   • 版本控制     │    │   • 模型更新     │    │   • 错误追踪     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 2. 监控指标

```yaml
监控指标配置：
performance_metrics:
  # 处理性能指标
  processing:
    - files_processed_per_minute
    - average_processing_time
    - memory_usage_mb
    - cpu_usage_percent
  
  # 检索性能指标  
  retrieval:
    - query_response_time_ms
    - cache_hit_rate
    - average_similarity_score
    - results_per_query
  
  # 质量指标
  quality:
    - ragas_faithfulness_score
    - ragas_relevance_score
    - user_feedback_score
    - error_rate
  
  # 系统健康指标
  system:
    - disk_usage_percent
    - database_connections
    - active_threads
    - uptime_days
```

### 3. 备份与恢复

```python
class BackupManager:
    """备份管理器"""
    
    def create_backup(self):
        """创建系统备份"""
        backup_data = {
            'timestamp': datetime.now().isoformat(),
            'vector_store': self.backup_vector_store(),
            'config': self.backup_config(),
            'cache': self.backup_cache(),
            'statistics': self.backup_statistics()
        }
        
        # 保存备份文件
        self.save_backup_file(backup_data)
        
        return backup_data
    
    def restore_backup(self, backup_file):
        """从备份恢复"""
        backup_data = self.load_backup_file(backup_file)
        
        # 恢复各组件
        self.restore_vector_store(backup_data['vector_store'])
        self.restore_config(backup_data['config'])
        self.restore_cache(backup_data['cache'])
        
        logger.info(f"系统已从备份恢复: {backup_data['timestamp']}")
```

### 4. 性能调优建议

```yaml
性能调优配置示例：
# 开发环境配置（注重快速迭代）
performance:
  max_workers: 2
  batch_size: 16
  cache:
    enabled: true
    size: "1GB"
  
# 生产环境配置（注重稳定性和性能）
performance:
  max_workers: 8
  batch_size: 64
  cache:
    enabled: true
    size: "10GB"
    redis:
      enabled: true
      host: "redis.local"
      port: 6379
  
# 大数据集配置（注重内存管理）
performance:
  max_workers: 4
  batch_size: 8
  memory:
    max_usage_mb: 8192
    cleanup_interval: 30
```

---

## 总结

### 架构优势

1. **模块化设计**: 各功能模块独立，便于维护和扩展
2. **配置驱动**: 通过配置文件灵活调整系统行为
3. **增量更新**: 智能识别变化，避免重复处理
4. **性能优化**: 并行处理、缓存机制、内存管理
5. **可扩展性**: 插件系统支持自定义功能扩展
6. **监控完善**: 全面的性能指标和健康检查

### 适用场景

1. **企业知识库**: 构建企业内部文档检索系统
2. **学术研究**: 处理学术论文和科研文档
3. **内容管理**: 媒体机构的内容检索和归档
4. **智能客服**: 基于文档的问答系统
5. **法律文档**: 法律条文和案例检索

### 未来扩展方向

1. **多模态支持**: 支持图像、表格等非文本内容
2. **分布式处理**: 支持集群部署和分布式计算
3. **实时更新**: 支持文档变更的实时索引
4. **智能推荐**: 基于用户行为的个性化推荐
5. **多语言支持**: 扩展多语言文档处理能力

---

## 相关文档链接

- [配置管理文档](config.md) - 详细配置参数说明
- [模块详细文档](.) - 各模块的详细说明
  - [Loader模块](loader_module.md)
  - [Cleaner模块](cleaner_module.md)
  - [Chunker模块](chunker_module.md)
  - [Encoder模块](encoder_module.md)
  - [Retriever模块](retriever_module.md)
  - [Pipeline模块](pipeline_module.md)
- [增量更新文档](incremental_update.md) - 增量更新功能说明
- [使用示例](config_usage.md) - 配置使用示例和最佳实践