"""
任务文件表管理模块

用于创建和管理文件处理任务，记录每个文件的处理状态，支持断点续传和错误重试。
"""

import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .file_utils import FileUtils
from .logger import get_logger

logger = get_logger(__name__)


class FileStatus(Enum):
    """文件处理状态"""
    PENDING = "pending"           # 等待处理
    PROCESSING = "processing"     # 正在处理
    COMPLETED = "completed"       # 处理完成
    ERROR = "error"               # 处理出错
    SKIPPED = "skipped"           # 被跳过（未修改）
    FILTERED = "filtered"         # 被过滤（大小不足等）


class TaskFileManager:
    """任务文件表管理器
    
    功能：
    1. 创建任务文件表，记录所有待处理文件
    2. 跟踪每个文件的处理状态
    3. 支持按文件类型排序处理
    4. 支持断点续传（从上次中断处继续）
    5. 记录错误信息，支持错误重试
    """
    
    # 文件类型优先级（数字越小优先级越高）
    FILE_TYPE_PRIORITY = {
        '.txt': 1,      # 文本文件最简单，优先处理
        '.csv': 2,      # CSV文件
        '.json': 3,     # JSON文件
        '.html': 4,     # HTML文件
        '.rtf': 5,      # RTF文件
        '.doc': 6,      # Word文档（旧格式）
        '.docx': 7,     # Word文档（新格式）
        '.wps': 8,      # WPS文档
        '.ppt': 9,      # PPT（旧格式）
        '.pptx': 10,    # PPT（新格式）
        '.xls': 11,     # Excel（旧格式）
        '.xlsx': 12,    # Excel（新格式）
        '.pdf': 13,     # PDF文件（可能需要OCR，较慢）
        '.caj': 14,     # CAJ文件（需要转换，最慢）
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化任务文件管理器
        
        Args:
            config: 配置字典，包含：
                - task_file_manager.task_file: 任务文件路径
                - incremental_update.enabled: 是否启用增量更新
                - loader.filters.min_file_size: 最小文件大小（字节，默认1024）
        """
        self.config = config or {}
        
        # 任务文件路径
        task_config = self.config.get('task_file_manager', {})
        self.task_file = Path(task_config.get('task_file', './cache/task_files.json'))
        self.task_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 文件过滤器配置
        filter_config = self.config.get('loader', {}).get('filters', {})
        self.min_file_size = filter_config.get('min_file_size', 1024)  # 默认1KB
        
        # 增量更新配置
        inc_config = self.config.get('incremental_update', {})
        self.incremental_enabled = inc_config.get('enabled', True)
        
        # 加载任务文件表
        self.task_files: Dict[str, Dict[str, Any]] = {}
        self.batch_id: Optional[str] = None
        self._load_task_file()
    
    def _load_task_file(self):
        """加载任务文件表"""
        if self.task_file.exists():
            try:
                with open(self.task_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.batch_id = data.get('batch_id')
                    self.task_files = data.get('files', {})
                logger.debug(f"已加载任务文件表: {len(self.task_files)} 个文件")
            except Exception as e:
                logger.warning(f"加载任务文件表失败: {e}")
                self.task_files = {}
    
    def _save_task_file(self):
        """保存任务文件表"""
        try:
            data = {
                'batch_id': self.batch_id,
                'created_at': datetime.now().isoformat(),
                'files': self.task_files,
            }
            with open(self.task_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.debug(f"已保存任务文件表: {len(self.task_files)} 个文件")
        except Exception as e:
            logger.error(f"保存任务文件表失败: {e}")
    
    def filter_by_size(self, file_path: Union[str, Path]) -> tuple[bool, Optional[str]]:
        """
        根据文件大小过滤
        
        Args:
            file_path: 文件路径
            
        Returns:
            (是否通过过滤, 过滤原因)
            - 通过: (True, None)
            - 未通过: (False, 原因字符串)
        """
        file_path = Path(file_path)
        try:
            file_size = file_path.stat().st_size
            if file_size < self.min_file_size:
                reason = (
                    f"文件大小不足: {file_path.name}, "
                    f"大小: {file_size} 字节 ({file_size / 1024:.2f} KB), "
                    f"最小要求: {self.min_file_size} 字节 ({self.min_file_size / 1024:.1f} KB)"
                )
                logger.warning(f"文件被过滤（大小不足）: {file_path.name}")
                return False, reason
            return True, None
        except Exception as e:
            logger.warning(f"检查文件大小失败: {file_path}, 错误: {e}")
            return False, f"检查文件大小失败: {str(e)}"
    
    def create_task_plan(
        self,
        file_paths: List[Union[str, Path]],
        batch_id: str,
        incremental_tracker=None
    ) -> Dict[str, Any]:
        """
        创建任务计划
        
        Args:
            file_paths: 文件路径列表
            batch_id: 批次ID
            incremental_tracker: 增量更新追踪器（用于检查文件状态）
            
        Returns:
            任务统计信息
        """
        self.batch_id = batch_id
        
        # 检查是否是继续之前的任务
        existing_files = set(self.task_files.keys())
        is_resuming = len(existing_files) > 0 and self.batch_id == batch_id
        
        if is_resuming:
            logger.info(f"继续之前的任务: {batch_id}")
        else:
            logger.info(f"创建新任务计划: {batch_id}")
            self.task_files.clear()
        
        stats = {
            'total': len(file_paths),
            'new': 0,
            'modified': 0,
            'unchanged': 0,
            'error_skipped': 0,
            'resumed': 0,
            'filtered': 0,
        }
        
        for fp in file_paths:
            fp = Path(fp)
            file_key = str(fp.resolve())
            file_ext = fp.suffix.lower()
            
            # 首先检查文件大小
            passed_size_filter, filter_reason = self.filter_by_size(fp)
            if not passed_size_filter:
                # 文件大小不足，直接标记为filtered
                try:
                    file_hash = FileUtils.calculate_file_hash(fp, 'md5')
                except Exception as e:
                    logger.warning(f"计算文件哈希失败: {fp}, 错误: {e}")
                    file_hash = ""
                
                self.task_files[file_key] = {
                    'path': str(fp),
                    'filename': fp.name,
                    'extension': file_ext,
                    'hash': file_hash,
                    'status': FileStatus.FILTERED.value,
                    'priority': self.FILE_TYPE_PRIORITY.get(file_ext, 99),
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat(),
                    'error': filter_reason,
                    'retry_count': 0,
                }
                stats['filtered'] = stats.get('filtered', 0) + 1
                continue
            
            # 检查是否已存在于任务表中
            if file_key in self.task_files:
                # 检查状态，如果是已完成或出错，保持不变
                status = self.task_files[file_key]['status']
                if status in [FileStatus.COMPLETED.value, FileStatus.ERROR.value]:
                    # 使用增量追踪器检查文件是否被修改
                    if incremental_tracker:
                        need_process, reason = incremental_tracker.check_file(fp)
                        if need_process and reason == 'modified':
                            # 文件已修改，重置状态为pending
                            self.task_files[file_key]['status'] = FileStatus.PENDING.value
                            self.task_files[file_key]['error'] = None
                            stats['modified'] += 1
                        else:
                            stats['resumed'] += 1
                    else:
                        stats['resumed'] += 1
                    continue
                elif status == FileStatus.SKIPPED.value:
                    # 检查是否需要重新处理
                    if incremental_tracker:
                        need_process, reason = incremental_tracker.check_file(fp)
                        if need_process:
                            self.task_files[file_key]['status'] = FileStatus.PENDING.value
                            stats['modified'] += 1
                            continue
                    stats['resumed'] += 1
                    continue
                elif status == FileStatus.PROCESSING.value:
                    # 中断时正在处理的文件，重置为pending重新处理
                    logger.info(f"文件中断后重新处理: {fp.name}")
                    self.task_files[file_key]['status'] = FileStatus.PENDING.value
                    self.task_files[file_key]['error'] = None
                    stats['resumed'] += 1  # 计入继续处理，而不是新文件
                    continue
                else:
                    # 其他状态（pending, filtered），继续处理
                    stats['resumed'] += 1
                    continue
            
            # 新文件，添加到任务表
            try:
                file_hash = FileUtils.calculate_file_hash(fp, 'md5')
            except Exception as e:
                logger.warning(f"计算文件哈希失败: {fp}, 错误: {e}")
                file_hash = ""
            
            # 确定初始状态
            initial_status = FileStatus.PENDING.value
            if incremental_tracker:
                need_process, reason = incremental_tracker.check_file(fp)
                if not need_process:
                    # 文件不需要处理（未修改或在错误记录中）
                    initial_status = FileStatus.SKIPPED.value
                    if reason == 'error_skipped':
                        stats['error_skipped'] += 1
                    else:
                        stats['unchanged'] += 1
                else:
                    stats['new'] += 1
            else:
                stats['new'] += 1
            
            self.task_files[file_key] = {
                'path': str(fp),
                'filename': fp.name,
                'extension': file_ext,
                'hash': file_hash,
                'status': initial_status,
                'priority': self.FILE_TYPE_PRIORITY.get(file_ext, 99),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'error': None,
                'retry_count': 0,
            }
        
        self._save_task_file()
        
        # 输出统计信息
        logger.info(f"任务计划创建完成:")
        logger.info(f"  总计: {stats['total']} 个文件")
        if stats['new'] > 0:
            logger.info(f"  新文件: {stats['new']} 个")
        if stats['modified'] > 0:
            logger.info(f"  已修改: {stats['modified']} 个")
        if stats['unchanged'] > 0:
            logger.info(f"  未变化（跳过）: {stats['unchanged']} 个")
        if stats['error_skipped'] > 0:
            logger.info(f"  错误（跳过）: {stats['error_skipped']} 个")
        if stats['resumed'] > 0:
            logger.info(f"  继续处理: {stats['resumed']} 个")
        if stats['filtered'] > 0:
            logger.info(f"  被过滤（大小不足）: {stats['filtered']} 个")
        
        return stats
    
    def get_pending_files(self, sort_by_priority: bool = True) -> List[Path]:
        """
        获取待处理的文件列表
        
        Args:
            sort_by_priority: 是否按优先级排序
            
        Returns:
            待处理的文件路径列表
        """
        pending_files = []
        for file_key, file_info in self.task_files.items():
            if file_info['status'] in [FileStatus.PENDING.value, FileStatus.PROCESSING.value]:
                pending_files.append((file_info['priority'], file_info['path']))
        
        if sort_by_priority:
            # 按优先级排序（数字小的优先）
            pending_files.sort(key=lambda x: x[0])
        
        return [Path(fp) for _, fp in pending_files]
    
    def update_file_status(
        self,
        file_path: Union[str, Path],
        status: FileStatus,
        error: Optional[str] = None
    ):
        """
        更新文件处理状态
        
        Args:
            file_path: 文件路径
            status: 新状态
            error: 错误信息（如果出错）
        """
        file_path = Path(file_path)
        file_key = str(file_path.resolve())
        
        if file_key not in self.task_files:
            logger.warning(f"更新状态失败: 文件不在任务表中 {file_path}")
            return
        
        self.task_files[file_key]['status'] = status.value
        self.task_files[file_key]['updated_at'] = datetime.now().isoformat()
        
        if error:
            self.task_files[file_key]['error'] = error
            if status == FileStatus.ERROR:
                self.task_files[file_key]['retry_count'] = self.task_files[file_key].get('retry_count', 0) + 1
        
        # 立即保存
        self._save_task_file()
    
    def get_file_status(self, file_path: Union[str, Path]) -> Optional[FileStatus]:
        """
        获取文件处理状态
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件状态，如果文件不在任务表中则返回None
        """
        file_path = Path(file_path)
        file_key = str(file_path.resolve())
        
        if file_key not in self.task_files:
            return None
        
        status_str = self.task_files[file_key]['status']
        return FileStatus(status_str)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取任务统计信息
        
        Returns:
            统计信息字典
        """
        stats = {
            'total': len(self.task_files),
            'pending': 0,
            'processing': 0,
            'completed': 0,
            'error': 0,
            'skipped': 0,
            'filtered': 0,
        }
        
        for file_info in self.task_files.values():
            status = file_info['status']
            if status in stats:
                stats[status] += 1
        
        return stats
    
    def reset_errors(self) -> int:
        """
        重置所有错误文件为待处理状态
        
        Returns:
            重置的文件数量
        """
        count = 0
        for file_key, file_info in self.task_files.items():
            if file_info['status'] == FileStatus.ERROR.value:
                file_info['status'] = FileStatus.PENDING.value
                file_info['error'] = None
                file_info['retry_count'] = 0
                file_info['updated_at'] = datetime.now().isoformat()
                count += 1
        
        if count > 0:
            self._save_task_file()
            logger.info(f"已重置 {count} 个错误文件为待处理状态")
        
        return count
    
    def clear_task(self):
        """清除任务文件表"""
        self.task_files.clear()
        self.batch_id = None
        self._save_task_file()
        logger.info("已清除任务文件表")
    
    def is_task_completed(self) -> bool:
        """
        检查任务是否已完成
        
        Returns:
            是否所有文件都已处理完成（包括出错和被跳过的）
        """
        if not self.task_files:
            return True
        
        for file_info in self.task_files.values():
            if file_info['status'] in [FileStatus.PENDING.value, FileStatus.PROCESSING.value]:
                return False
        
        return True
