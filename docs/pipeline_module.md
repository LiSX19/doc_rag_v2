# Pipeline 模块详细说明文档

## 目录
1. [模块概述](#模块概述)
2. [文件结构](#文件结构)
3. [核心类与接口](#核心类与接口)
4. [Pipeline执行器](#pipeline执行器)
5. [Pipeline管理器](#pipeline管理器)
6. [处理流程](#处理流程)
7. [配置参数](#配置参数)
8. [使用示例](#使用示例)
9. [扩展开发](#扩展开发)

---

## 模块概述

Pipeline 模块是文档 RAG 系统的核心协调组件，负责将各个独立的功能模块（加载、清洗、分块、编码、存储等）串联起来，形成完整的文档处理流水线。该模块实现了从原始文档到向量知识库的端到端处理流程，支持增量更新、错误恢复和进度追踪。

### 主要功能

1. **端到端流程协调**: 协调各模块按正确顺序执行文档处理任务
2. **增量更新支持**: 智能识别已处理文件，避免重复计算
3. **错误恢复机制**: 处理过程中的错误捕获和恢复
4. **进度追踪**: 实时显示处理进度和统计信息
5. **资源配置管理**: 管理和分配计算资源
6. **结果验证**: 验证各阶段处理结果的正确性

### Pipeline工作流程

```
原始文档 (Raw Documents)
    │
    ├─> 1. 文件发现与筛选
    │      ├─ 扫描输入目录
    │      ├─ 过滤支持的文件格式
    │      ├─ 增量检查（跳过已处理文件）
    │      └─ 文件优先级排序
    │
    ├─> 2. 文档加载 (Loader)
    │      ├─ 多格式文档解析
    │      ├─ 元数据提取
    │      ├─ 文本内容提取
    │      └─ 加载结果缓存
    │
    ├─> 3. 文本清洗 (Cleaner)
    │      ├─ 结构清洗（HTML/XML标签移除）
    │      ├─ 编码修复
    │      ├─ 繁简转换
    │      ├─ OCR后处理（如启用）
    │      └─ 文本规范化
    │
    ├─> 4. 文本分块 (Chunker)
    │      ├─ 递归分块策略
    │      ├─ 语义边界保持
    │      ├─ 分块元数据生成
    │      └─ 分块结果管理
    │
    ├─> 5. 去重处理 (Deduper)
    │      ├─ 哈希去重（精确匹配）
    │      ├─ SimHash去重（近似匹配）
    │      ├─ Embedding去重（语义去重）
    │      └─ 重复块统计
    │
    ├─> 6. 向量编码 (Encoder)
    │      ├─ 稠密向量编码（默认）
    │      ├─ 稀疏向量编码（可选）
    │      ├─ 混合编码（可选）
    │      └─ 编码缓存管理
    │
    ├─> 7. 向量存储 (Vector Store)
    │      ├─ 向量数据库连接
    │      ├─ 批量向量存储
    │      ├─ 索引构建与优化
    │      └─ 存储结果验证
    │
    └─> 8. 结果汇总与报告
           ├─ 处理统计生成
           ├─ 错误日志收集
           ├─ 性能指标计算
           └─ 处理报告输出
```

---

## 文件结构

```
src/
├── pipeline.py              # Pipeline执行器（核心流程执行）
├── pipeline_manager.py      # Pipeline管理器（高级接口和协调）
└── pipeline_utils.py        # Pipeline工具函数（进度追踪、错误处理等）
```

---

## 核心类与接口

### 1. PipelineManager (Pipeline管理器)

高级接口，提供完整的知识库构建和管理功能：

```python
class PipelineManager:
    """Pipeline管理器
    
    负责协调各个模块完成文档处理流程。
    提供高级API，隐藏底层实现细节。
    """
    
    def __init__(self, config: ConfigManager):
        """
        初始化Pipeline管理器
        
        Args:
            config: 配置管理器
        """
    
    def build_knowledge_base(
        self,
        input_dir: Optional[str] = None,
        file_limit: Optional[int] = None,
        incremental: bool = True,
        is_ocr: bool = False,
        force_rebuild: bool = False
    ) -> Dict[str, Any]:
        """
        构建知识库完整流程
        
        Args:
            input_dir: 输入目录（默认使用配置中的input_dir）
            file_limit: 文件数量限制（None表示无限制）
            incremental: 是否增量更新
            is_ocr: 是否使用OCR清洗
            force_rebuild: 是否强制重建（忽略增量更新）
            
        Returns:
            处理统计信息
        """
    
    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        use_rerank: bool = True
    ) -> List[Dict[str, Any]]:
        """
        检索相关文档
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            use_rerank: 是否使用重排序
            
        Returns:
            检索结果列表
        """
    
    def evaluate(
        self,
        questions: List[str],
        contexts: List[List[str]],
        answers: List[str],
        ground_truths: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        评估RAG系统性能
        
        Args:
            questions: 问题列表
            contexts: 上下文列表
            answers: 答案列表
            ground_truths: 标准答案列表（可选）
            
        Returns:
            评估结果
        """
```

### 2. build_pipeline (Pipeline执行函数)

核心流程执行函数，实现具体的处理逻辑：

```python
def build_pipeline(
    files_to_process: List[Path],
    config: Dict[str, Any],
    task_file_manager,
    loader,
    cleaner,
    chunker,
    chunk_manager,
    deduper,
    encoder_manager,
    vector_store,
    output_manager,
    is_ocr: bool = False
) -> Dict[str, Any]:
    """
    执行构建知识库的完整流程
    
    Args:
        files_to_process: 待处理文件列表
        config: 配置字典
        task_file_manager: 任务文件管理器
        loader: 文档加载器
        cleaner: 文本清洗器
        chunker: 文本分块器
        chunk_manager: 分块管理器
        deduper: 去重器
        encoder_manager: 编码管理器
        vector_store: 向量数据库
        output_manager: 输出管理器
        is_ocr: 是否使用OCR清洗
        
    Returns:
        处理统计信息
    """
```

### 3. 懒加载属性 (Lazy Loading Properties)

PipelineManager 使用懒加载模式初始化各个模块，提高启动速度：

```python
class PipelineManager:
    # ... 初始化代码 ...
    
    @property
    def loader(self):
        """获取文档加载器（懒加载）"""
        if self._loader is None:
            from src.loaders import DocumentLoader
            self._loader = DocumentLoader(self.config.get_all())
        return self._loader
    
    @property
    def cleaner(self):
        """获取文本清洗器（懒加载）"""
        if self._cleaner is None:
            from src.cleaners import TextCleaner
            self._cleaner = TextCleaner(self.config.get_all())
        return self._cleaner
    
    @property
    def chunker(self):
        """获取文本分块器（懒加载）"""
        if self._chunker is None:
            from src.chunkers import RecursiveChunker
            self._chunker = RecursiveChunker(self.config.get_all())
        return self._chunker
    
    # ... 其他模块的懒加载属性 ...
```

---

## Pipeline执行器

### 1. 核心处理循环

Pipeline执行器采用分阶段的处理策略，每个文件独立处理，便于错误隔离和增量更新：

```python
def build_pipeline(files_to_process, config, ...):
    """Pipeline核心执行逻辑"""
    
    # 初始化统计信息
    stats = initialize_stats(files_to_process)
    
    # 创建进度追踪器
    progress = ProgressTracker(total=len(files_to_process))
    
    # 逐个文件处理
    for file_path in files_to_process:
        try:
            # 阶段1: 文档加载
            loaded_doc = loader.load(file_path)
            if loaded_doc:
                stats['loaded_files'] += 1
            
            # 阶段2: 文本清洗
            cleaned_text = cleaner.clean(loaded_doc.content)
            if cleaned_text:
                stats['cleaned_files'] += 1
            
            # 阶段3: 文本分块
            chunks = chunker.chunk(cleaned_text)
            if chunks:
                stats['chunked_files'] += 1
                stats['total_chunks'] += len(chunks)
            
            # 阶段4: 去重处理
            dedup_result = deduper.deduplicate(chunks)
            unique_chunks = dedup_result.chunks
            stats['deduped_files'] += 1
            stats['unique_chunks'] += len(unique_chunks)
            stats['removed_chunks'] += len(dedup_result.removed_chunks)
            
            # 阶段5: 向量编码
            encoded_vectors = encoder_manager.encode_chunks(unique_chunks)
            stats['encoded_chunks'] += len(encoded_vectors)
            
            # 阶段6: 向量存储
            vector_store.add(encoded_vectors)
            stats['stored_chunks'] += len(encoded_vectors)
            
        except Exception as e:
            # 错误处理
            stats['errors'].append({
                'file': str(file_path),
                'error': str(e),
                'stage': determine_failed_stage(e)
            })
            logger.error(f"处理文件失败: {file_path}, 错误: {e}")
        
        # 更新进度
        progress.update(1, file_path.name)
    
    # 生成最终报告
    final_stats = generate_final_report(stats)
    return final_stats
```

### 2. 错误处理机制

Pipeline实现了多层错误处理机制，确保单个文件的失败不会影响整个流程：

```python
def process_single_file(file_path, modules, stats):
    """处理单个文件（包含错误处理）"""
    error_info = None
    
    try:
        # 尝试处理文件
        result = _process_file_internal(file_path, modules)
        return result
        
    except LoaderError as e:
        error_info = {'stage': 'loading', 'error': str(e)}
        logger.warning(f"文档加载失败: {file_path}, 错误: {e}")
        
    except CleanerError as e:
        error_info = {'stage': 'cleaning', 'error': str(e)}
        logger.warning(f"文本清洗失败: {file_path}, 错误: {e}")
        
    except ChunkerError as e:
        error_info = {'stage': 'chunking', 'error': str(e)}
        logger.warning(f"文本分块失败: {file_path}, 错误: {e}")
        
    except Exception as e:
        error_info = {'stage': 'unknown', 'error': str(e)}
        logger.error(f"未知错误: {file_path}, 错误: {e}")
    
    # 记录错误并尝试恢复
    if error_info:
        stats['errors'].append({
            'file': str(file_path),
            **error_info,
            'timestamp': datetime.now().isoformat()
        })
        
        # 尝试从错误中恢复（如跳过当前文件继续处理）
        return None
    
    return None
```

### 3. 进度追踪

Pipeline提供详细的进度追踪功能，包括进度条、时间估计和性能指标：

```python
class ProgressTracker:
    """进度追踪器"""
    
    def __init__(self, total: int, desc: str = "处理进度"):
        self.total = total
        self.desc = desc
        self.start_time = time.time()
        self.completed = 0
        self.current_file = ""
        
    def update(self, n: int = 1, current_file: str = ""):
        """更新进度"""
        self.completed += n
        self.current_file = current_file
        
        # 计算进度百分比
        percentage = (self.completed / self.total) * 100
        
        # 计算已用时间和预计剩余时间
        elapsed = time.time() - self.start_time
        if self.completed > 0:
            time_per_item = elapsed / self.completed
            remaining = (self.total - self.completed) * time_per_item
            remaining_str = f"{remaining:.0f}s"
        else:
            remaining_str = "计算中..."
        
        # 显示进度信息
        self._display_progress(percentage, remaining_str)
    
    def _display_progress(self, percentage: float, remaining: str):
        """显示进度信息"""
        bar_length = 40
        filled_length = int(bar_length * percentage / 100)
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        
        sys.stdout.write(
            f"\r{self.desc}: |{bar}| {percentage:.1f}% "
            f"({self.completed}/{self.total}) "
            f"剩余: {remaining}  当前: {self.current_file[:30]}"
        )
        sys.stdout.flush()
```

---

## Pipeline管理器

### 1. 高级接口设计

PipelineManager 提供简化的高级接口，隐藏底层复杂性：

```python
class PipelineManager:
    """高级Pipeline管理器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化Pipeline管理器
        
        Args:
            config_path: 配置文件路径（None使用默认配置）
        """
        # 加载配置
        self.config = ConfigManager(config_path)
        
        # 初始化输出管理器
        self.output_manager = OutputManager(self.config.get_all())
        
        # 懒加载模块
        self._modules = {}
    
    def build_knowledge_base(self, **kwargs) -> Dict[str, Any]:
        """
        一键构建知识库（简化接口）
        
        Example:
            manager = PipelineManager()
            stats = manager.build_knowledge_base(
                input_dir="./data",
                incremental=True
            )
        """
        # 参数处理
        input_dir = kwargs.get('input_dir') or self.config.get('paths.input_dir')
        file_limit = kwargs.get('file_limit')
        incremental = kwargs.get('incremental', True)
        is_ocr = kwargs.get('is_ocr', False)
        force_rebuild = kwargs.get('force_rebuild', False)
        
        # 执行构建流程
        result = self._build_knowledge_base_internal(
            input_dir, file_limit, incremental, is_ocr, force_rebuild
        )
        
        return result
    
    def query(self, question: str, **kwargs) -> Dict[str, Any]:
        """
        一键查询（简化接口）
        
        Example:
            manager = PipelineManager()
            result = manager.query(
                "什么是机器学习？",
                top_k=5,
                use_rerank=True
            )
        """
        # 执行检索
        results = self.retriever.retrieve(question, **kwargs)
        
        # 格式化结果
        formatted_results = self._format_retrieval_results(results)
        
        return {
            'question': question,
            'results': formatted_results,
            'timestamp': datetime.now().isoformat()
        }
```

### 2. 模块生命周期管理

PipelineManager 负责管理各个模块的生命周期：

```python
class PipelineManager:
    """模块生命周期管理"""
    
    def initialize_modules(self):
        """初始化所有模块"""
        modules_to_init = [
            'loader', 'cleaner', 'chunker', 'chunk_manager',
            'deduper', 'encoder_manager', 'vector_store', 'retriever'
        ]
        
        for module_name in modules_to_init:
            try:
                # 通过属性访问触发懒加载
                getattr(self, module_name)
                logger.info(f"模块初始化完成: {module_name}")
            except Exception as e:
                logger.error(f"模块初始化失败: {module_name}, 错误: {e}")
                raise
    
    def cleanup_modules(self):
        """清理模块资源"""
        for module_name, module_instance in self._modules.items():
            if hasattr(module_instance, 'close'):
                try:
                    module_instance.close()
                    logger.info(f"模块资源释放: {module_name}")
                except Exception as e:
                    logger.warning(f"模块资源释放失败: {module_name}, 错误: {e}")
    
    def reset_modules(self):
        """重置模块（用于重新初始化）"""
        self.cleanup_modules()
        self._modules.clear()
        self.initialize_modules()
```

### 3. 配置管理

PipelineManager 提供统一的配置管理接口：

```python
class PipelineManager:
    """配置管理"""
    
    def update_config(self, config_updates: Dict[str, Any]):
        """
        更新配置
        
        Args:
            config_updates: 配置更新字典
        
        Example:
            manager.update_config({
                'paths.input_dir': './new_data',
                'chunker.chunk_size': 500,
                'encoder.type': 'hybrid'
            })
        """
        # 更新配置管理器
        self.config.update(config_updates)
        
        # 重新初始化受影响的模块
        self._reinitialize_affected_modules(config_updates)
    
    def _reinitialize_affected_modules(self, config_updates: Dict[str, Any]):
        """重新初始化受配置更新影响的模块"""
        affected_modules = set()
        
        # 根据配置键确定受影响的模块
        config_key_to_module = {
            'paths.': ['loader', 'output_manager'],
            'loader.': ['loader'],
            'cleaner.': ['cleaner'],
            'chunker.': ['chunker', 'chunk_manager'],
            'deduper.': ['deduper'],
            'encoder.': ['encoder_manager'],
            'vector_store.': ['vector_store'],
            'retriever.': ['retriever']
        }
        
        for config_key, modules in config_key_to_module.items():
            for update_key in config_updates.keys():
                if update_key.startswith(config_key):
                    affected_modules.update(modules)
        
        # 重新初始化受影响的模块
        for module_name in affected_modules:
            if hasattr(self, f"_{module_name}"):
                setattr(self, f"_{module_name}", None)  # 重置懒加载属性
                logger.info(f"重新初始化模块: {module_name}")
    
    def get_config_summary(self) -> Dict[str, Any]:
        """获取配置摘要"""
        return {
            'paths': self.config.get('paths', {}),
            'modules': {
                'loader': self.config.get('loader', {}),
                'cleaner': self.config.get('cleaner', {}),
                'chunker': self.config.get('chunker', {}),
                'deduper': self.config.get('deduper', {}),
                'encoder': self.config.get('encoder', {}),
                'vector_store': self.config.get('vector_store', {}),
                'retriever': self.config.get('retriever', {})
            },
            'performance': self.config.get('performance', {}),
            'logging': self.config.get('logging', {})
        }
```

---

## 处理流程

### 1. 完整处理流程

Pipeline 实现了从原始文档到检索就绪的完整处理流程：

```python
def complete_pipeline_flow(input_dir: str) -> Dict[str, Any]:
    """
    完整Pipeline流程示例
    """
    # 1. 初始化Pipeline管理器
    manager = PipelineManager()
    
    # 2. 构建知识库
    build_stats = manager.build_knowledge_base(
        input_dir=input_dir,
        incremental=True,
        file_limit=100
    )
    
    # 3. 验证知识库
    validation_result = manager.validate_knowledge_base()
    
    # 4. 执行测试查询
    test_queries = [
        "什么是机器学习？",
        "深度学习与机器学习的区别",
        "监督学习有哪些方法"
    ]
    
    query_results = []
    for query in test_queries:
        result = manager.query(query, top_k=3)
        query_results.append(result)
    
    # 5. 生成报告
    report = {
        'build': build_stats,
        'validation': validation_result,
        'queries': query_results,
        'summary': {
            'total_documents': build_stats.get('total_files', 0),
            'total_chunks': build_stats.get('total_chunks', 0),
            'unique_chunks': build_stats.get('unique_chunks', 0),
            'vector_store_count': manager.vector_store.count(),
            'processing_time': build_stats.get('processing_time', 0)
        }
    }
    
    return report
```

### 2. 增量更新流程

Pipeline 支持智能增量更新，避免重复处理：

```python
def incremental_update_flow(manager: PipelineManager, new_files_dir: str):
    """
    增量更新流程
    """
    # 1. 检查现有知识库状态
    has_data = manager.check_vector_store()
    if not has_data:
        logger.info("知识库为空，执行完整构建")
        return manager.build_knowledge_base(input_dir=new_files_dir, incremental=False)
    
    # 2. 识别新文件或修改过的文件
    all_files = manager.scan_input_directory(new_files_dir)
    files_to_process = manager.filter_new_or_modified_files(all_files)
    
    if not files_to_process:
        logger.info("没有新文件或修改过的文件需要处理")
        return {'status': 'no_changes', 'files_processed': 0}
    
    # 3. 执行增量更新
    logger.info(f"发现 {len(files_to_process)} 个新/修改文件需要处理")
    
    stats = manager.build_knowledge_base(
        input_dir=new_files_dir,
        incremental=True,
        file_limit=None  # 处理所有新文件
    )
    
    # 4. 更新索引和统计
    manager.vector_store.optimize_index()
    manager.update_statistics()
    
    return stats
```

### 3. 错误恢复流程

Pipeline 实现了健壮的错误恢复机制：

```python
def resilient_pipeline_flow(manager: PipelineManager, input_dir: str):
    """
    具有错误恢复能力的Pipeline流程
    """
    max_retries = 3
    retry_delay = 5  # 秒
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Pipeline执行尝试 {attempt + 1}/{max_retries}")
            
            # 执行Pipeline
            result = manager.build_knowledge_base(
                input_dir=input_dir,
                incremental=True
            )
            
            # 检查是否有错误
            errors = result.get('errors', [])
            if errors:
                logger.warning(f"Pipeline完成但有 {len(errors)} 个错误")
                
                # 尝试修复可恢复的错误
                fixed_errors = manager.attempt_error_recovery(errors)
                if fixed_errors:
                    logger.info(f"成功修复了 {len(fixed_errors)} 个错误")
            
            return result
            
        except PipelineFatalError as e:
            logger.error(f"Pipeline致命错误: {e}")
            raise  # 致命错误，直接抛出
            
        except PipelineTemporaryError as e:
            logger.warning(f"Pipeline临时错误: {e}")
            
            if attempt < max_retries - 1:
                # 等待后重试
                logger.info(f"等待 {retry_delay} 秒后重试...")
                time.sleep(retry_delay)
                
                # 重置模块并重试
                manager.reset_modules()
                continue
            else:
                logger.error("达到最大重试次数，Pipeline失败")
                raise
    
    # 不应该到达这里
    raise PipelineError("Pipeline执行失败")
```

---

## 配置参数

### 1. Pipeline全局配置
```yaml
# Pipeline基础配置
pipeline:
  # 执行模式
  mode: "standard"            # standard/debug/production
  max_workers: 4              # 最大工作线程数
  batch_size: 10              # 批处理大小
  
  # 错误处理配置
  error_handling:
    max_retries: 3            # 最大重试次数
    retry_delay: 5            # 重试延迟（秒）
    continue_on_error: true   # 出错时是否继续
    log_errors: true          # 是否记录错误
  
  # 性能监控配置
  monitoring:
    enabled: true             # 是否启用监控
    log_interval: 60          # 日志记录间隔（秒）
    metrics: ["throughput", "latency", "memory"]
  
  # 进度报告配置
  progress:
    enabled: true             # 是否显示进度条
    update_interval: 1        # 更新间隔（秒）
    detailed: false           # 是否显示详细信息
```

### 2. 增量更新配置
```yaml
pipeline:
  incremental:
    enabled: true             # 是否启用增量更新
    strategy: "hash_based"    # 增量策略: hash_based/timestamp
    
    # 哈希策略配置
    hash_based:
      algorithm: "md5"        # 哈希算法: md5/sha256
      cache_dir: "./cache/file_hashes"
      cleanup_old: true       # 是否清理旧哈希
    
    # 时间戳策略配置
    timestamp_based:
      field: "mtime"          # 时间戳字段: mtime/ctime
      tolerance: 2            # 时间容差（秒）
    
    # 文件监控配置
    file_monitoring:
      enabled: false          # 是否启用文件监控
      poll_interval: 300      # 轮询间隔（秒）
      watch_directories: ["./data"]
```

### 3. 资源管理配置
```yaml
pipeline:
  resources:
    # 内存管理
    memory:
      max_usage_mb: 4096      # 最大内存使用（MB）
      warning_threshold: 0.8  # 内存警告阈值
      cleanup_interval: 60    # 内存清理间隔（秒）
    
    # CPU管理
    cpu:
      max_workers: 4          # 最大工作线程数
      affinity: []            # CPU亲和性（空表示自动）
    
    # GPU管理（如果可用）
    gpu:
      enabled: false          # 是否使用GPU
      device_ids: [0]         # GPU设备ID
      memory_fraction: 0.8    # GPU内存使用比例
    
    # 磁盘管理
    disk:
      temp_dir: "./temp"      # 临时目录
      max_temp_size_mb: 1024  # 最大临时文件大小（MB）
      cleanup_on_exit: true   # 退出时清理临时文件
```

### 4. 日志和报告配置
```yaml
pipeline:
  logging:
    # 日志级别
    level: "INFO"             # 日志级别: DEBUG/INFO/WARNING/ERROR
    console_level: "INFO"     # 控制台日志级别
    file_level: "DEBUG"       # 文件日志级别
    
    # 日志输出
    console_output: true      # 是否输出到控制台
    file_output: true         # 是否输出到文件
    file_path: "./logs/pipeline.log"
    
    # 日志格式
    format: "detailed"        # 日志格式: simple/detailed/json
    
  reporting:
    # 报告生成
    generate_report: true     # 是否生成处理报告
    report_format: "json"     # 报告格式: json/html/markdown
    report_path: "./reports"
    
    # 报告内容
    include_stats: true       # 是否包含统计信息
    include_errors: true      # 是否包含错误信息
    include_performance: true # 是否包含性能指标
    include_samples: true     # 是否包含样本数据
```

---

## 使用示例

### 1. 基本使用
```python
from src.pipeline_manager import PipelineManager

# 初始化Pipeline管理器
manager = PipelineManager()

# 构建知识库（完整流程）
stats = manager.build_knowledge_base(
    input_dir="./data/documents",
    file_limit=100,          # 限制处理100个文件
    incremental=True,        # 启用增量更新
    is_ocr=False            # 不启用OCR
)

print("Pipeline执行完成!")
print(f"处理统计:")
print(f"  总文件数: {stats['total_files']}")
print(f"  成功加载: {stats['loaded_files']}")
print(f"  成功清洗: {stats['cleaned_files']}")
print(f"  总文本块: {stats['total_chunks']}")
print(f"  唯一文本块: {stats['unique_chunks']}")
print(f"  重复文本块: {stats['removed_chunks']}")
print(f"  编码向量: {stats['encoded_chunks']}")
print(f"  存储向量: {stats['stored_chunks']}")
print(f"  错误数量: {len(stats['errors'])}")

# 执行检索测试
query = "人工智能的应用领域有哪些?"
results = manager.query(query, top_k=5)

print(f"\n查询结果: '{query}'")
for i, result in enumerate(results['results']):
    print(f"{i+1}. [相似度: {result['score']:.3f}] {result['content'][:100]}...")
```

### 2. 增量更新示例
```python
from src.pipeline_manager import PipelineManager
import time

# 初始化Pipeline管理器
manager = PipelineManager()

# 首次构建知识库
print("首次构建知识库...")
first_build_stats = manager.build_knowledge_base(
    input_dir="./data",
    incremental=False,  # 完整构建
    file_limit=None
)
print(f"首次构建完成，处理了 {first_build_stats['total_files']} 个文件")

# 等待一段时间，添加新文件
time.sleep(10)

# 增量更新（只处理新文件或修改过的文件）
print("\n执行增量更新...")
incremental_stats = manager.build_knowledge_base(
    input_dir="./data",
    incremental=True,  # 增量更新
    file_limit=None
)

if incremental_stats['total_files'] > 0:
    print(f"增量更新完成，处理了 {incremental_stats['total_files']} 个新/修改文件")
else:
    print("没有需要更新的文件")

# 检查向量数据库状态
vector_count = manager.vector_store.count()
print(f"向量数据库中的文档数量: {vector_count}")
```

### 3. 批量处理示例
```python
from src.pipeline_manager import PipelineManager
from concurrent.futures import ThreadPoolExecutor

def process_batch(batch_id: int, file_list: List[str]):
    """处理一个文件批次"""
    manager = PipelineManager()
    
    print(f"开始处理批次 {batch_id} ({len(file_list)} 个文件)")
    
    stats = manager.build_knowledge_base(
        input_dir=None,  # 使用文件列表而不是目录
        file_list=file_list,
        incremental=False
    )
    
    return {
        'batch_id': batch_id,
        'stats': stats,
        'success': len(stats['errors']) == 0
    }

# 准备批量处理
all_files = [...]  # 所有待处理文件列表
batch_size = 20
batches = [all_files[i:i+batch_size] for i in range(0, len(all_files), batch_size)]

# 并行处理批次
results = []
with ThreadPoolExecutor(max_workers=4) as executor:
    # 提交批次处理任务
    future_to_batch = {
        executor.submit(process_batch, i, batch): i
        for i, batch in enumerate(batches)
    }
    
    # 收集结果
    for future in as_completed(future_to_batch):
        batch_id = future_to_batch[future]
        try:
            result = future.result()
            results.append(result)
            print(f"批次 {batch_id} 处理完成")
        except Exception as e:
            print(f"批次 {batch_id} 处理失败: {e}")

# 汇总结果
total_files = sum(len(batch) for batch in batches)
successful_batches = sum(1 for r in results if r['success'])
total_chunks = sum(r['stats']['total_chunks'] for r in results)

print(f"\n批量处理完成!")
print(f"总文件数: {total_files}")
print(f"成功批次: {successful_batches}/{len(batches)}")
print(f"总文本块数: {total_chunks}")
```

### 4. 自定义Pipeline
```python
from src.pipeline import build_pipeline
from src.pipeline_manager import PipelineManager
from src.utils import TaskFileManager, OutputManager

# 自定义Pipeline配置
custom_config = {
    'paths': {
        'input_dir': './custom_data',
        'output_dir': './custom_outputs'
    },
    'chunker': {
        'chunk_size': 500,
        'chunk_overlap': 50
    },
    'encoder': {
        'type': 'hybrid',
        'hybrid': {
            'dense_weight': 0.7,
            'sparse_weight': 0.3
        }
    }
}

# 初始化各个模块
manager = PipelineManager(custom_config)

# 获取各个模块实例
loader = manager.loader
cleaner = manager.cleaner
chunker = manager.chunker
chunk_manager = manager.chunk_manager
deduper = manager.deduper
encoder_manager = manager.encoder_manager
vector_store = manager.vector_store

# 自定义任务文件管理器
task_file_manager = TaskFileManager(
    config=custom_config,
    output_dir='./custom_cache'
)

# 自定义输出管理器
output_manager = OutputManager(custom_config)

# 扫描输入文件
input_dir = custom_config['paths']['input_dir']
supported_extensions = loader.get_supported_extensions()
files_to_process = FileUtils.list_files(
    Path(input_dir), 
    supported_extensions, 
    recursive=True
)

# 限制文件数量（测试用）
files_to_process = files_to_process[:10]

print(f"开始处理 {len(files_to_process)} 个文件")

# 执行自定义Pipeline
stats = build_pipeline(
    files_to_process=files_to_process,
    config=custom_config,
    task_file_manager=task_file_manager,
    loader=loader,
    cleaner=cleaner,
    chunker=chunker,
    chunk_manager=chunk_manager,
    deduper=deduper,
    encoder_manager=encoder_manager,
    vector_store=vector_store,
    output_manager=output_manager,
    is_ocr=False
)

print(f"自定义Pipeline执行完成!")
print(f"统计信息: {stats}")
```

### 5. 错误处理和恢复
```python
from src.pipeline_manager import PipelineManager
from src.exceptions import PipelineError, RetryableError

def safe_pipeline_execution(config_path: str):
    """安全的Pipeline执行（包含错误处理和恢复）"""
    manager = None
    
    try:
        # 初始化管理器
        manager = PipelineManager(config_path)
        
        # 执行Pipeline
        stats = manager.build_knowledge_base(
            input_dir="./data",
            incremental=True
        )
        
        # 检查错误
        errors = stats.get('errors', [])
        if errors:
            print(f"警告: Pipeline完成但有 {len(errors)} 个错误")
            
            # 记录错误
            for error in errors:
                print(f"  文件: {error['file']}, 错误: {error['error']}")
            
            # 尝试从错误中恢复
            recovered = manager.recover_from_errors(errors)
            if recovered:
                print(f"成功恢复了 {len(recovered)} 个错误")
        
        return stats
        
    except RetryableError as e:
        print(f"可重试错误: {e}")
        
        # 实现重试逻辑
        for attempt in range(3):
            try:
                print(f"重试尝试 {attempt + 1}/3")
                time.sleep(2 ** attempt)  # 指数退避
                
                if manager:
                    manager.reset_modules()
                
                stats = manager.build_knowledge_base(
                    input_dir="./data",
                    incremental=True
                )
                return stats
                
            except RetryableError as retry_error:
                print(f"重试失败: {retry_error}")
                if attempt == 2:
                    raise PipelineError(f"重试多次后仍然失败: {retry_error}")
        
    except PipelineError as e:
        print(f"Pipeline错误: {e}")
        raise
        
    finally:
        # 清理资源
        if manager:
            try:
                manager.cleanup_modules()
            except Exception as cleanup_error:
                print(f"资源清理失败: {cleanup_error}")

# 执行安全的Pipeline
try:
    stats = safe_pipeline_execution("./config.yaml")
    print(f"Pipeline执行成功!")
except Exception as e:
    print(f"Pipeline执行失败: {e}")
```

---

## 扩展开发

### 1. 添加新的处理阶段

**步骤 1**: 创建新的处理阶段
```python
from typing import List, Dict, Any
from src.chunkers.base import TextChunk

class CustomProcessingStage:
    """自定义处理阶段示例"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.custom_param = config.get('custom_stage.param', 'default')
    
    def process(self, chunks: List[TextChunk]) -> List[TextChunk]:
        """处理文本块"""
        processed_chunks = []
        
        for chunk in chunks:
            # 自定义处理逻辑
            processed_content = self._custom_transform(chunk.content)
            
            # 创建新的文本块
            processed_chunk = TextChunk(
                content=processed_content,
                chunk_id=chunk.chunk_id,
                metadata={
                    **chunk.metadata,
                    'custom_processed': True,
                    'original_length': len(chunk.content),
                    'processed_length': len(processed_content)
                }
            )
            processed_chunks.append(processed_chunk)
        
        return processed_chunks
    
    def _custom_transform(self, text: str) -> str:
        """自定义文本转换"""
        # 示例：添加前缀
        prefix = self.config.get('custom_stage.prefix', '')
        return f"{prefix}{text}"
```

**步骤 2**: 集成到Pipeline
```python
from src.pipeline import build_pipeline

def enhanced_build_pipeline(
    files_to_process: List[Path],
    config: Dict[str, Any],
    task_file_manager,
    loader,
    cleaner,
    chunker,
    chunk_manager,
    deduper,
    encoder_manager,
    vector_store,
    output_manager,
    is_ocr: bool = False,
    custom_stage = None  # 新增参数
) -> Dict[str, Any]:
    """
    增强版Pipeline，支持自定义处理阶段
    """
    # ... 原有处理逻辑 ...
    
    # 在去重后，编码前插入自定义处理阶段
    if custom_stage and unique_chunks:
        print("执行自定义处理阶段...")
        processed_chunks = custom_stage.process(unique_chunks)
        unique_chunks = processed_chunks
        
        # 更新统计
        stats['custom_processed_chunks'] = len(processed_chunks)
    
    # ... 后续处理逻辑 ...
    
    return stats
```

**步骤 3**: 更新PipelineManager支持
```python
class EnhancedPipelineManager(PipelineManager):
    """增强版Pipeline管理器，支持自定义阶段"""
    
    def __init__(self, config=None):
        super().__init__(config)
        self._custom_stage = None
    
    @property
    def custom_stage(self):
        """获取自定义处理阶段（懒加载）"""
        if self._custom_stage is None:
            custom_config = self.config.get('custom_stage', {})
            if custom_config.get('enabled', False):
                from custom_module import CustomProcessingStage
                self._custom_stage = CustomProcessingStage(self.config.get_all())
        return self._custom_stage
    
    def build_knowledge_base(self, **kwargs):
        """重写构建方法，支持自定义阶段"""
        # 使用增强版Pipeline函数
        from enhanced_pipeline import enhanced_build_pipeline
        
        # ... 原有逻辑 ...
        
        # 调用增强版Pipeline
        stats = enhanced_build_pipeline(
            # ... 原有参数 ...
            custom_stage=self.custom_stage
        )
        
        return stats
```

### 2. 实现并行Pipeline

```python
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import List, Dict, Any
import multiprocessing

class ParallelPipeline:
    """并行Pipeline执行器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.num_processes = config.get('pipeline.parallel.num_processes', 
                                       multiprocessing.cpu_count())
        
    def execute_parallel(self, files_to_process: List[Path]) -> Dict[str, Any]:
        """并行执行Pipeline"""
        # 将文件分片
        file_slices = self._split_files(files_to_process)
        
        # 准备进程池
        all_stats = []
        with ProcessPoolExecutor(max_workers=self.num_processes) as executor:
            # 提交并行任务
            future_to_slice = {
                executor.submit(self._process_slice, slice_files