"""
文档加载统一入口

提供并行文档加载、元数据提取、缓存等功能。
支持文件大小过滤。
"""

import hashlib
import json
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from src.configs import ConfigManager
from src.utils import get_logger, OutputManager
from src.utils.file_utils import FileUtils
from src.utils.incremental_tracker import IncrementalTracker

from .loader_factory import LoaderFactory, get_loader

logger = get_logger(__name__)


class DocumentLoader:
    """文档加载器"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化文档加载器

        Args:
            config: 配置字典，包含：
                - loader.parallel.enabled: 是否启用并行处理
                - loader.parallel.max_workers: 最大工作进程数
                - loader.extract_metadata: 是否提取元数据
                - loader.filters.min_file_size: 最小文件大小（字节，默认1024）
                - paths.cache_dir: 缓存目录
        """
        self.config = config or {}

        # 并行处理配置
        parallel_config = self.config.get('loader', {}).get('parallel', {})
        self.parallel_enabled = parallel_config.get('enabled', True)
        self.max_workers = parallel_config.get('max_workers', 4)

        # 元数据提取
        self.extract_metadata = self.config.get('loader', {}).get('extract_metadata', True)

        # 文件过滤器配置
        filter_config = self.config.get('loader', {}).get('filters', {})
        self.min_file_size = filter_config.get('min_file_size', 1024)  # 默认1KB

        # 缓存配置
        self.cache_dir = Path(self.config.get('paths', {}).get('cache_dir', './cache'))
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # 支持的扩展名
        self.supported_extensions = LoaderFactory.get_supported_extensions()
        
        # 输出管理器
        self.output_manager = OutputManager(config)
        
        # 失败文件记录
        self.failed_files: List[Dict[str, Any]] = []
        self.filtered_files: List[Dict[str, Any]] = []
        
        # 增量更新追踪器
        self.incremental_tracker = IncrementalTracker(config)

        logger.info(f"文档加载器初始化完成，支持格式: {len(self.supported_extensions)} 种")
        logger.info(f"文件大小过滤器: 最小 {self.min_file_size} 字节 ({self.min_file_size / 1024:.1f} KB)")

    def _filter_by_size(self, file_path: Path) -> bool:
        """
        根据文件大小过滤

        Args:
            file_path: 文件路径

        Returns:
            True 表示文件大小符合要求，False 表示被过滤掉
        """
        try:
            file_size = file_path.stat().st_size
            if file_size < self.min_file_size:
                logger.warning(
                    f"文件被过滤（大小不足）: {file_path.name}, "
                    f"大小: {file_size} 字节 ({file_size / 1024:.2f} KB), "
                    f"最小要求: {self.min_file_size} 字节 ({self.min_file_size / 1024:.1f} KB)"
                )
                # 记录被过滤的文件
                self.filtered_files.append({
                    'file_path': str(file_path),
                    'filename': file_path.name,
                    'reason': 'size_too_small',
                    'file_size': file_size,
                    'min_size': self.min_file_size,
                    'timestamp': datetime.now().isoformat(),
                })
                return False
            return True
        except Exception as e:
            logger.error(f"检查文件大小时出错: {file_path}, 错误: {e}")
            # 记录检查失败的文件
            self.failed_files.append({
                'file_path': str(file_path),
                'filename': file_path.name,
                'reason': 'size_check_error',
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
            })
            return False

    def load_document(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        加载单个文档

        Args:
            file_path: 文件路径

        Returns:
            文档内容字典
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        # 检查文件大小
        if not self._filter_by_size(file_path):
            raise ValueError(
                f"文件大小不足: {file_path.name}, "
                f"最小要求: {self.min_file_size} 字节 ({self.min_file_size / 1024:.1f} KB)"
            )

        # 检查文件类型
        if not LoaderFactory.is_supported(file_path):
            ext = file_path.suffix.lower()
            raise ValueError(f"不支持的文件类型: {ext}，文件: {file_path}")

        logger.info(f"加载文档: {file_path.name}")

        # 获取加载器
        loader = get_loader(file_path, self.config)
        if loader is None:
            raise RuntimeError(f"无法获取文件加载器: {file_path}")

        # 加载文档
        try:
            result = loader.load(file_path)
            logger.info(f"文档加载成功: {file_path.name}, 内容长度: {len(result.get('content', ''))}")
            
            # 保存加载结果（根据配置决定是否保存）
            self.output_manager.save_loaded_document(
                filename=file_path.stem,
                content=result['content'],
                metadata=result['metadata']
            )
            
            return result
        except Exception as e:
            logger.error(f"文档加载失败: {file_path.name}, 错误: {e}")
            # 记录加载失败的文件
            self.failed_files.append({
                'file_path': str(file_path),
                'filename': file_path.name,
                'reason': 'load_error',
                'error': str(e),
                'error_type': type(e).__name__,
                'timestamp': datetime.now().isoformat(),
            })
            raise

    def load_documents(
        self,
        file_paths: List[Union[str, Path]],
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        incremental: bool = True
    ) -> List[Dict[str, Any]]:
        """
        批量加载文档

        Args:
            file_paths: 文件路径列表
            progress_callback: 进度回调函数，参数为(当前, 总数, 文件名)
            incremental: 是否使用增量更新模式（默认True）

        Returns:
            文档内容列表
        """
        if not file_paths:
            return []

        # 先进行大小过滤
        filtered_paths = []
        skipped_count = 0
        for fp in file_paths:
            fp = Path(fp)
            if self._filter_by_size(fp):
                filtered_paths.append(fp)
            else:
                skipped_count += 1

        if skipped_count > 0:
            logger.warning(f"批量加载时过滤了 {skipped_count} 个大小不足的文件")

        if not filtered_paths:
            logger.warning("所有文件都被过滤，没有可加载的文档")
            return []
        
        # 增量更新筛选
        if incremental and self.incremental_tracker.enabled:
            filtered_paths, inc_stats = self.incremental_tracker.filter_files(filtered_paths)
            
            if not filtered_paths:
                logger.info("所有文件都已是最新，无需处理")
                return []
        else:
            logger.info("全量更新模式：处理所有文件")

        total = len(filtered_paths)
        logger.info(f"开始批量加载 {total} 个文档（原始 {len(file_paths)} 个，过滤 {skipped_count} 个）")

        results = []

        if self.parallel_enabled and total > 1:
            # 并行处理
            results = self._load_parallel(filtered_paths, progress_callback)
        else:
            # 串行处理
            for i, file_path in enumerate(filtered_paths):
                if progress_callback:
                    progress_callback(i + 1, total, file_path.name)

                try:
                    result = self.load_document(file_path)
                    results.append(result)
                except Exception as e:
                    logger.error(f"加载失败: {file_path}, 错误: {e}")
                    # 记录失败的文件（已在 load_document 中记录，这里不再重复）
                    results.append({
                        'content': '',
                        'metadata': {'source': str(file_path), 'error': str(e)},
                        'pages': [],
                    })

        success_count = len([r for r in results if r.get('content')])
        logger.info(f"批量加载完成，成功: {success_count}/{total}")
        
        # 更新增量更新记录（只记录成功加载的文件）
        if incremental and self.incremental_tracker.enabled:
            successful_paths = [
                r['metadata']['source'] for r in results
                if r.get('content') and 'metadata' in r and 'source' in r['metadata']
            ]
            if successful_paths:
                self.incremental_tracker.update_records(successful_paths)
        
        return results

    def _load_parallel(
        self,
        file_paths: List[Union[str, Path]],
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> List[Dict[str, Any]]:
        """
        并行加载文档

        Args:
            file_paths: 文件路径列表
            progress_callback: 进度回调函数

        Returns:
            文档内容列表
        """
        total = len(file_paths)
        results = [None] * total
        completed = 0

        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_index = {
                executor.submit(_load_single_document_worker, str(fp), self.config): i
                for i, fp in enumerate(file_paths)
            }

            # 收集结果
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                file_path = file_paths[index]

                try:
                    result = future.result()
                    results[index] = result
                except Exception as e:
                    logger.error(f"并行加载失败: {file_path}, 错误: {e}")
                    results[index] = {
                        'content': '',
                        'metadata': {'source': str(file_path), 'error': str(e)},
                        'pages': [],
                    }

                completed += 1
                if progress_callback:
                    progress_callback(completed, total, Path(file_path).name)

        return results

    def load_directory(
        self,
        directory: Union[str, Path],
        extensions: Optional[List[str]] = None,
        recursive: bool = True,
        file_limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        加载目录中的所有文档

        Args:
            directory: 目录路径
            extensions: 文件扩展名过滤列表
            recursive: 是否递归子目录
            file_limit: 文件数量限制

        Returns:
            文档内容列表
        """
        directory = Path(directory)

        if not directory.exists():
            raise FileNotFoundError(f"目录不存在: {directory}")

        if not directory.is_dir():
            raise ValueError(f"路径不是目录: {directory}")

        # 获取文件列表
        if extensions is None:
            extensions = self.supported_extensions

        file_paths = FileUtils.list_files(directory, extensions, recursive)

        if file_limit:
            file_paths = file_paths[:file_limit]

        logger.info(f"从目录 {directory} 找到 {len(file_paths)} 个文档")

        return self.load_documents(file_paths)

    def get_supported_extensions(self) -> List[str]:
        """获取支持的文件扩展名列表"""
        return self.supported_extensions.copy()

    def is_supported(self, file_path: Union[str, Path]) -> bool:
        """检查文件类型是否被支持"""
        return LoaderFactory.is_supported(file_path)

    def get_failed_files(self) -> List[Dict[str, Any]]:
        """
        获取加载失败的文件列表
        
        Returns:
            失败文件信息列表
        """
        return self.failed_files.copy()

    def get_filtered_files(self) -> List[Dict[str, Any]]:
        """
        获取被过滤的文件列表
        
        Returns:
            被过滤文件信息列表
        """
        return self.filtered_files.copy()

    def save_failed_files_report(self, output_path: Optional[Union[str, Path]] = None) -> Path:
        """
        保存失败文件报告
        
        Args:
            output_path: 输出文件路径，默认为 outputs/failed_files_report_{timestamp}.json
            
        Returns:
            报告文件路径
        """
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = Path(self.config.get('paths', {}).get('output_dir', './outputs')) / f'failed_files_report_{timestamp}.json'
        else:
            output_path = Path(output_path)
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_failed': len(self.failed_files),
                'total_filtered': len(self.filtered_files),
                'total_issues': len(self.failed_files) + len(self.filtered_files),
            },
            'failed_files': self.failed_files,
            'filtered_files': self.filtered_files,
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"失败文件报告已保存: {output_path}")
        return output_path

    def clear_failed_records(self):
        """清空失败文件记录"""
        self.failed_files.clear()
        self.filtered_files.clear()
        logger.info("已清空失败文件记录")

    def set_incremental_mode(self, enabled: bool):
        """
        设置增量更新模式
        
        Args:
            enabled: 是否启用增量更新
        """
        self.incremental_tracker.enabled = enabled
        mode_str = "增量" if enabled else "全量"
        logger.info(f"已切换到{mode_str}更新模式")

    def clear_incremental_records(self):
        """清空增量更新记录（用于全量重建）"""
        self.incremental_tracker.clear_all_records()
        logger.info("已清空增量更新记录，下次将全量处理")

    def get_incremental_stats(self) -> Dict[str, Any]:
        """
        获取增量更新统计信息
        
        Returns:
            统计信息字典
        """
        return self.incremental_tracker.get_statistics()


def _load_single_document_worker(
    file_path: str,
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    工作进程函数：加载单个文档

    Args:
        file_path: 文件路径
        config: 配置字典

    Returns:
        文档内容字典
    """
    # 在工作进程中创建新的加载器实例
    loader = DocumentLoader(config)
    return loader.load_document(file_path)
