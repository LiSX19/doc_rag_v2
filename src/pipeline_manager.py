"""
DocRAG Pipeline 管理器

负责协调各个模块完成文档处理流程。
"""

from typing import Any, Dict, List, Optional
from pathlib import Path
from datetime import datetime
import json

from src.configs import ConfigManager
from src.utils import get_logger, OutputManager
from src.utils.file_utils import FileUtils
from src.utils.incremental_tracker import IncrementalTracker
from src.utils.pipeline_tracker import PipelineStageTracker, STAGE_FILE_PROCESSING, STAGE_DEDUP, STAGE_ENCODE_STORE
from src.utils.task_file_manager import TaskFileManager, FileStatus

logger = get_logger(__name__)


class PipelineManager:
    """Pipeline管理器，协调各模块完成文档处理"""

    def __init__(self, config: ConfigManager):
        """
        初始化Pipeline管理器

        Args:
            config: 配置管理器
        """
        self.config = config
        self.output_manager = OutputManager(config.get_all())

        # 初始化各模块（懒加载）
        self._loader = None
        self._cleaner = None
        self._chunker = None
        self._chunk_manager = None
        self._incremental_tracker = None
        self._deduper = None
        self._encoder_manager = None
        self._task_file_manager = None
        self._pipeline_tracker = None
        self._embedder = None
        self._vector_store = None
        self._retriever = None

    @property
    def loader(self):
        """获取文档加载器"""
        if self._loader is None:
            from src.loaders import DocumentLoader
            self._loader = DocumentLoader(self.config.get_all())
        return self._loader

    @property
    def cleaner(self):
        """获取文本清洗器"""
        if self._cleaner is None:
            from src.cleaners import TextCleaner
            self._cleaner = TextCleaner(self.config.get_all())
        return self._cleaner

    @property
    def chunker(self):
        """获取文本分块器"""
        if self._chunker is None:
            from src.chunkers import RecursiveChunker
            self._chunker = RecursiveChunker(self.config.get_all())
        return self._chunker

    @property
    def chunk_manager(self):
        """获取分块管理器"""
        if self._chunk_manager is None:
            from src.chunkers import ChunkManager
            self._chunk_manager = ChunkManager(self.config.get_all())
        return self._chunk_manager

    @property
    def incremental_tracker(self):
        """获取增量更新追踪器"""
        if self._incremental_tracker is None:
            self._incremental_tracker = IncrementalTracker(self.config.get_all())
        return self._incremental_tracker

    @property
    def pipeline_tracker(self):
        """获取 Pipeline 全局阶段追踪器"""
        if self._pipeline_tracker is None:
            self._pipeline_tracker = PipelineStageTracker(self.config.get_all())
        return self._pipeline_tracker

    @property
    def deduper(self):
        """获取去重器"""
        if self._deduper is None:
            from src.dedupers import Deduper
            self._deduper = Deduper(self.config.get_all())
        return self._deduper

    @property
    def encoder_manager(self):
        """获取编码管理器"""
        if self._encoder_manager is None:
            from src.encoders import EncoderManager
            self._encoder_manager = EncoderManager(self.config.get_all())
        return self._encoder_manager

    @property
    def task_file_manager(self):
        """获取任务文件管理器"""
        if self._task_file_manager is None:
            self._task_file_manager = TaskFileManager(self.config.get_all())
        return self._task_file_manager

    @property
    def embedder(self):
        """获取Embedding模型（现在使用DenseEncoder替代BGEEmbedder）"""
        if self._embedder is None:
            from src.encoders import DenseEncoder
            self._embedder = DenseEncoder(self.config.get_all())
            # 确保模型已加载
            self._embedder.initialize()
        return self._embedder

    @property
    def vector_store(self):
        """获取向量数据库"""
        if self._vector_store is None:
            from src.vector_stores import ChromaStore
            self._vector_store = ChromaStore(self.config.get_all())
            self._vector_store.initialize()
        return self._vector_store

    @property
    def retriever(self):
        """获取检索器"""
        if self._retriever is None:
            from src.retrievers import VectorRetriever
            self._retriever = VectorRetriever(
                embedder=self.embedder,
                vector_store=self.vector_store,
                config=self.config.get_all()
            )
        return self._retriever

    def scan_files(self, input_dir: str) -> List[Path]:
        """
        扫描目录获取所有支持的文件

        Args:
            input_dir: 输入目录

        Returns:
            文件路径列表
        """
        from src.loaders import LoaderFactory

        input_path = Path(input_dir)
        if not input_path.exists():
            raise FileNotFoundError(f"输入目录不存在: {input_dir}")

        supported_extensions = LoaderFactory.get_supported_extensions()
        files = FileUtils.list_files(input_path, supported_extensions, recursive=True)

        return files

    def check_vector_store(self) -> bool:
        """
        检查向量数据库是否有数据

        Returns:
            True if vector store has data, False otherwise
        """
        try:
            count = self.vector_store.collection.count()
            return count > 0
        except Exception:
            return False

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
            input_dir: 输入目录
            file_limit: 文件数量限制
            incremental: 是否增量更新
            is_ocr: 是否使用OCR清洗
            force_rebuild: 是否强制重建

        Returns:
            处理统计信息
        """
        from src.pipeline import build_pipeline, _append_filter_log, _run_dedup_and_encode

        input_path = input_dir or self.config.get('paths.input_dir', './data')
        input_path = Path(input_path).resolve()

        # 强制重建时清除 Pipeline 阶段状态
        if force_rebuild:
            self.pipeline_tracker.clear()

        print(f"\n📁 扫描输入目录: {input_path}")

        # 扫描文件
        all_files = self.scan_files(input_path)

        if not all_files:
            print("❌ 没有找到需要处理的文件")
            return {'status': 'error', 'message': '没有找到需要处理的文件'}

        print(f"📊 发现 {len(all_files)} 个文件")

        # 检查向量数据库状态
        has_vector_data = self.check_vector_store()
        if has_vector_data:
            print(f"✅ 向量数据库已有数据")
        else:
            print(f"⚠️  向量数据库为空")

        # 创建任务计划
        print(f"\n📝 正在建立文件处理清单...")
        batch_id = str(input_path)
        task_stats = self.task_file_manager.create_task_plan(
            file_paths=all_files,
            batch_id=batch_id,
            incremental_tracker=self.incremental_tracker if incremental else None
        )

        # 实时写入过滤日志
        for file_key, file_info in self.task_file_manager.task_files.items():
            if file_info.get('status') == 'filtered':
                _append_filter_log({
                    'timestamp': file_info.get('updated_at') or file_info.get('created_at') or datetime.now().isoformat(),
                    'file_path': file_info.get('path', ''),
                    'module': 'filter',
                    'reason': file_info.get('error', '文件被过滤')
                })

        # 显示任务统计
        print(f"\n📋 文件处理清单:")
        print(f"   总计: {task_stats.get('total', 0)} 个文件")
        if task_stats.get('new', 0) > 0:
            print(f"   🆕 新文件: {task_stats['new']} 个")
        if task_stats.get('modified', 0) > 0:
            print(f"   📝 已修改: {task_stats['modified']} 个")
        if task_stats.get('unchanged', 0) > 0:
            print(f"   ⏭️  未修改: {task_stats['unchanged']} 个")
        if task_stats.get('resumed', 0) > 0:
            print(f"   🔄 继续处理: {task_stats['resumed']} 个")
        if task_stats.get('filtered', 0) > 0:
            print(f"   🚫 被过滤: {task_stats['filtered']} 个")
        if task_stats.get('error_skipped', 0) > 0:
            print(f"   ⚠️  错误跳过: {task_stats['error_skipped']} 个")

        # 获取待处理文件
        files_to_process = self.task_file_manager.get_pending_files(sort_by_priority=True)

        # 应用文件数量限制
        if file_limit and len(files_to_process) > file_limit:
            files_to_process = files_to_process[:file_limit]

        if not files_to_process:
            # 优先检查 Pipeline 阶段追踪器：是否有中断的全局阶段需要恢复
            pipeline_stage = self.pipeline_tracker.get_stage()
            if pipeline_stage in (STAGE_FILE_PROCESSING, STAGE_DEDUP, STAGE_ENCODE_STORE):
                print(f"\n🔄 检测到上一次运行在 '{pipeline_stage}' 阶段中断，正在恢复...")
                saved_stats = self.pipeline_tracker.get_stats()
                if saved_stats and saved_stats.get('chunked_files', 0) > 0:
                    stats = _run_dedup_and_encode(
                        chunk_manager=self.chunk_manager,
                        deduper=self.deduper,
                        encoder_manager=self.encoder_manager,
                        vector_store=self.vector_store,
                        stats=saved_stats,
                        pipeline_tracker=self.pipeline_tracker,
                    )
                    # 保存增量更新记录
                    self.incremental_tracker._save_records()
                    # 保存错误记录到文件
                    self._save_error_log(stats)
                    return stats
                else:
                    print(f"⚠️  保存的状态中没有分块记录，无法恢复")
                    self.pipeline_tracker.clear()

            # 没有待处理文件但向量数据库为空，需要重新处理（无恢复手段时）
            if not has_vector_data:
                logger.warning("向量数据库为空，将重新处理所有文件")
                self.pipeline_tracker.clear()
                reset_count = 0
                for file_key in self.task_file_manager.task_files:
                    status = self.task_file_manager.task_files[file_key]['status']
                    if status in [FileStatus.COMPLETED.value, FileStatus.SKIPPED.value, FileStatus.PROCESSING.value]:
                        self.task_file_manager.task_files[file_key]['status'] = FileStatus.PENDING.value
                        self.task_file_manager.task_files[file_key]['error'] = None
                        reset_count += 1
                if reset_count > 0:
                    print(f"🔄 向量数据库为空，重置 {reset_count} 个文件为待处理状态")
                self.task_file_manager._save_task_file()
                files_to_process = self.task_file_manager.get_pending_files(sort_by_priority=True)

            if not files_to_process:
                self._save_error_log({'errors': []})
                return {
                    'status': 'success',
                    'message': '没有需要处理的文件',
                    'total_files': len(all_files),
                    'vector_store_has_data': has_vector_data
                }

        # 执行构建流程
        stats = build_pipeline(
            files_to_process=files_to_process,
            config=self.config.get_all(),
            task_file_manager=self.task_file_manager,
            loader=self.loader,
            cleaner=self.cleaner,
            chunker=self.chunker,
            chunk_manager=self.chunk_manager,
            deduper=self.deduper,
            encoder_manager=self.encoder_manager,
            vector_store=self.vector_store,
            output_manager=self.output_manager,
            is_ocr=is_ocr,
            pipeline_tracker=self.pipeline_tracker,
        )

        # 保存增量更新记录
        self.incremental_tracker._save_records()

        # 保存错误记录到文件
        self._save_error_log(stats)

        return stats

    def _save_error_log(self, stats: Dict[str, Any]):
        """保存错误记录到文件"""
        errors = stats.get('errors', [])
        
        # 辅助函数：从错误信息推断模块
        def infer_module_from_error(error_msg: str) -> str:
            error_msg_lower = error_msg.lower()
            if any(keyword in error_msg_lower for keyword in ['未生成分块', 'chunk', '分块']):
                return 'chunker'
            elif any(keyword in error_msg_lower for keyword in ['加载失败', 'load', '加载']):
                return 'loader'
            elif any(keyword in error_msg_lower for keyword in ['清洗失败', 'clean', '清洗']):
                return 'cleaner'
            elif any(keyword in error_msg_lower for keyword in ['编码失败', 'encode', '编码']):
                return 'encoder'
            elif any(keyword in error_msg_lower for keyword in ['存储失败', 'store', '存储']):
                return 'vector_store'
            else:
                return 'unknown'
        
        # 收集任务文件表中的错误文件（状态为error）
        task_file_errors = []
        # 收集过滤的文件
        filtered_files = []
        for file_key, file_info in self.task_file_manager.task_files.items():
            status = file_info.get('status')
            if status == 'error':
                error_msg = file_info.get('error', '处理失败')
                task_file_errors.append({
                    'timestamp': file_info.get('updated_at') or file_info.get('created_at') or datetime.now().isoformat(),
                    'file_path': file_info.get('path', ''),
                    'module': infer_module_from_error(error_msg),
                    'reason': error_msg
                })
            elif status == 'filtered':
                filtered_files.append({
                    'timestamp': file_info.get('updated_at') or file_info.get('created_at') or datetime.now().isoformat(),
                    'file_path': file_info.get('path', ''),
                    'module': 'filter',
                    'reason': file_info.get('error', '文件被过滤')
                })
        
        # 合并所有错误：本次处理的错误 + 任务文件表中的错误
        all_errors_from_stats = errors + task_file_errors
        
        # 如果没有错误也没有过滤文件，直接返回
        if not all_errors_from_stats and not filtered_files:
            return
        
        # 保存错误日志
        if all_errors_from_stats:
            error_log_path = Path('./cache/error_log.json')
            error_log_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 读取已有的错误记录
            existing_errors = []
            if error_log_path.exists():
                try:
                    with open(error_log_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        existing_errors = data.get('errors', [])
                except Exception:
                    pass
            
            # 合并错误记录（去重：基于文件路径和时间戳）
            seen = set()
            all_errors = []
            for error in existing_errors + all_errors_from_stats:
                key = (error.get('file_path', ''), error.get('timestamp', ''))
                if key not in seen:
                    seen.add(key)
                    all_errors.append(error)
            
            # 保存错误记录
            error_log = {
                'updated_at': datetime.now().isoformat(),
                'total_errors': len(all_errors),
                'errors': all_errors
            }
            
            try:
                with open(error_log_path, 'w', encoding='utf-8') as f:
                    json.dump(error_log, f, ensure_ascii=False, indent=2)
                print(f"\n⚠️  发现 {len(all_errors_from_stats)} 个错误（包含 {len(task_file_errors)} 个历史错误），已记录到: {error_log_path}")
            except Exception as e:
                logger.error(f"保存错误日志失败: {e}")
        
        # 保存过滤日志
        if filtered_files:
            filter_log_path = Path('./cache/filter_log.json')
            filter_log_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 读取已有的过滤记录
            existing_filtered = []
            if filter_log_path.exists():
                try:
                    with open(filter_log_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        existing_filtered = data.get('filtered_files', [])
                except Exception:
                    pass
            
            # 合并过滤记录（去重：基于文件路径）
            seen = set()
            all_filtered = []
            for filtered in existing_filtered + filtered_files:
                key = (filtered.get('file_path', ''), filtered.get('timestamp', ''))
                if key not in seen:
                    seen.add(key)
                    all_filtered.append(filtered)
            
            # 保存过滤记录
            filter_log = {
                'updated_at': datetime.now().isoformat(),
                'total_filtered': len(all_filtered),
                'filtered_files': all_filtered
            }
            
            try:
                with open(filter_log_path, 'w', encoding='utf-8') as f:
                    json.dump(filter_log, f, ensure_ascii=False, indent=2)
                print(f"🔍  发现 {len(filtered_files)} 个过滤文件，已记录到: {filter_log_path}")
            except Exception as e:
                logger.error(f"保存过滤日志失败: {e}")

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        检索知识库

        Args:
            query: 查询问题
            top_k: 返回结果数量
            threshold: 相似度阈值

        Returns:
            检索结果
        """
        # 检查向量数据库
        if not self.check_vector_store():
            return {
                'status': 'error',
                'message': '向量数据库为空，请先运行 build 命令构建知识库'
            }

        # 执行检索
        results = self.retriever.retrieve(query, top_k=top_k)

        # 应用阈值过滤
        if threshold:
            results = [r for r in results if r.score >= threshold]

        return {
            'status': 'success',
            'query': query,
            'total_results': len(results),
            'results': [
                {
                    'content': r.content,
                    'score': float(r.score),
                    'metadata': r.metadata
                }
                for r in results
            ]
        }
