"""
增量更新追踪模块

用于记录已处理文件的哈希值，支持全量更新和增量更新模式。
支持断点续传和错误文件过滤。
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from .file_utils import FileUtils
from .logger import get_logger

logger = get_logger(__name__)


class IncrementalTracker:
    """增量更新追踪器
    
    支持功能：
    1. 增量更新 - 只处理新文件和修改过的文件
    2. 断点续传 - 记录处理进度，中断后可从上次位置继续
    3. 错误过滤 - 记录处理失败的文件，下次运行时跳过（除非文件被修改）
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化增量更新追踪器
        
        Args:
            config: 配置字典，包含：
                - incremental_update.enabled: 是否启用增量更新
                - incremental_update.hash_file: 哈希记录文件路径
                - incremental_update.timestamp_file: 时间戳记录文件路径
                - incremental_update.error_file: 错误记录文件路径
                - incremental_update.progress_file: 进度记录文件路径
        """
        self.config = config or {}
        
        # 读取增量更新配置（从performance.incremental_update读取）
        performance_config = self.config.get('performance', {})
        inc_config = performance_config.get('incremental_update', {})
        self.enabled = inc_config.get('enabled', True)
        
        # 哈希记录文件
        self.hash_file = Path(inc_config.get('hash_file', './cache/file_hashes.json'))
        self.hash_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 时间戳记录文件
        self.timestamp_file = Path(inc_config.get('timestamp_file', './cache/file_timestamps.json'))
        self.timestamp_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 错误记录文件
        self.error_file = Path(inc_config.get('error_file', './cache/file_errors.json'))
        self.error_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 进度记录文件（用于断点续传）
        self.progress_file = Path(inc_config.get('progress_file', './cache/progress.json'))
        self.progress_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 加载已记录的哈希值
        self.file_hashes: Dict[str, str] = {}
        self.file_timestamps: Dict[str, float] = {}
        self.file_errors: Dict[str, Dict[str, Any]] = {}  # 错误记录
        self.progress: Dict[str, Any] = {}  # 进度记录
        self._load_records()
        
        logger.info(f"增量更新追踪器初始化完成，模式: {'增量' if self.enabled else '全量'}")
        if self.enabled:
            logger.info(f"已记录文件数: {len(self.file_hashes)}")
    
    def _load_records(self):
        """加载已记录的哈希值、时间戳、错误和进度"""
        # 加载哈希记录
        if self.hash_file.exists():
            try:
                with open(self.hash_file, 'r', encoding='utf-8') as f:
                    self.file_hashes = json.load(f)
                logger.debug(f"已加载 {len(self.file_hashes)} 条哈希记录")
            except Exception as e:
                logger.warning(f"加载哈希记录失败: {e}")
                self.file_hashes = {}
        
        # 加载时间戳记录
        if self.timestamp_file.exists():
            try:
                with open(self.timestamp_file, 'r', encoding='utf-8') as f:
                    self.file_timestamps = json.load(f)
                logger.debug(f"已加载 {len(self.file_timestamps)} 条时间戳记录")
            except Exception as e:
                logger.warning(f"加载时间戳记录失败: {e}")
                self.file_timestamps = {}
        
        # 加载错误记录
        if self.error_file.exists():
            try:
                with open(self.error_file, 'r', encoding='utf-8') as f:
                    self.file_errors = json.load(f)
                logger.debug(f"已加载 {len(self.file_errors)} 条错误记录")
            except Exception as e:
                logger.warning(f"加载错误记录失败: {e}")
                self.file_errors = {}
        
        # 加载进度记录
        if self.progress_file.exists():
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    self.progress = json.load(f)
                logger.debug(f"已加载进度记录: {self.progress}")
            except Exception as e:
                logger.warning(f"加载进度记录失败: {e}")
                self.progress = {}
    
    def _save_records(self):
        """保存哈希值、时间戳、错误和进度记录"""
        try:
            # 保存哈希记录（如果为空则删除文件）
            if self.file_hashes:
                with open(self.hash_file, 'w', encoding='utf-8') as f:
                    json.dump(self.file_hashes, f, ensure_ascii=False, indent=2)
            elif self.hash_file.exists():
                self.hash_file.unlink()
            
            # 保存时间戳记录（如果为空则删除文件）
            if self.file_timestamps:
                with open(self.timestamp_file, 'w', encoding='utf-8') as f:
                    json.dump(self.file_timestamps, f, ensure_ascii=False, indent=2)
            elif self.timestamp_file.exists():
                self.timestamp_file.unlink()
            
            # 保存错误记录（如果为空则删除文件）
            if self.file_errors:
                with open(self.error_file, 'w', encoding='utf-8') as f:
                    json.dump(self.file_errors, f, ensure_ascii=False, indent=2)
            elif self.error_file.exists():
                self.error_file.unlink()
            
            # 保存进度记录（如果为空则删除文件）
            if self.progress:
                with open(self.progress_file, 'w', encoding='utf-8') as f:
                    json.dump(self.progress, f, ensure_ascii=False, indent=2)
            elif self.progress_file.exists():
                self.progress_file.unlink()
            
            logger.debug(f"已保存 {len(self.file_hashes)} 条哈希记录, {len(self.file_errors)} 条错误记录")
        except Exception as e:
            logger.error(f"保存记录失败: {e}")
    
    def check_file(self, file_path: Union[str, Path]) -> Tuple[bool, str]:
        """
        检查文件是否需要处理
        
        Args:
            file_path: 文件路径
            
        Returns:
            (是否需要处理, 原因)
            - (True, "new"): 新文件
            - (True, "modified"): 文件已修改
            - (False, "unchanged"): 文件未变化
            - (False, "error_skipped"): 之前处理出错且文件未修改，跳过
            - (True, "full_update"): 全量更新模式
        """
        file_path = Path(file_path)
        file_key = str(file_path.resolve())
        
        # 全量更新模式
        if not self.enabled:
            return True, "full_update"
        
        # 计算当前哈希值
        try:
            current_hash = FileUtils.calculate_file_hash(file_path, 'md5')
        except Exception as e:
            logger.warning(f"计算文件哈希失败: {file_path}, 错误: {e}")
            return True, "hash_error"
        
        # 检查是否有错误记录
        if file_key in self.file_errors:
            error_record = self.file_errors[file_key]
            # 检查文件是否已修改（通过比较哈希值）
            if error_record.get('hash') == current_hash:
                # 文件未修改，跳过
                return False, "error_skipped"
            else:
                # 文件已修改，清除错误记录，重新处理
                del self.file_errors[file_key]
                self._save_records()
                return True, "modified"
        
        # 文件不存在于记录中（新文件）
        if file_key not in self.file_hashes:
            return True, "new"
        
        # 比较哈希值
        if current_hash != self.file_hashes[file_key]:
            return True, "modified"
        
        return False, "unchanged"
    
    def filter_files(
        self,
        file_paths: List[Union[str, Path]],
        force_full: bool = False
    ) -> Tuple[List[Path], Dict[str, List[str]]]:
        """
        筛选需要处理的文件
        
        Args:
            file_paths: 文件路径列表
            force_full: 是否强制全量更新
            
        Returns:
            (需要处理的文件列表, 统计信息)
            统计信息包含：new, modified, unchanged, error_skipped 等分类
        """
        if force_full or not self.enabled:
            logger.info("全量更新模式：处理所有文件")
            return [Path(fp) for fp in file_paths], {
                'total': len(file_paths),
                'to_process': len(file_paths),
                'new': 0,
                'modified': 0,
                'unchanged': 0,
                'error_skipped': 0,
                'mode': 'full'
            }
        
        to_process = []
        stats = {
            'total': len(file_paths),
            'to_process': 0,
            'new': [],
            'modified': [],
            'unchanged': [],
            'error_skipped': [],
            'hash_error': [],
        }
        
        for fp in file_paths:
            fp = Path(fp)
            need_process, reason = self.check_file(fp)
            
            if need_process:
                to_process.append(fp)
                if reason == 'new':
                    stats['new'].append(str(fp))
                elif reason == 'modified':
                    stats['modified'].append(str(fp))
                elif reason == 'hash_error':
                    stats['hash_error'].append(str(fp))
            else:
                if reason == 'error_skipped':
                    stats['error_skipped'].append(str(fp))
                else:
                    stats['unchanged'].append(str(fp))
        
        stats['to_process'] = len(to_process)
        
        # 输出统计信息
        logger.info(f"文件筛选完成:")
        logger.info(f"  总计: {stats['total']} 个")
        logger.info(f"  需要处理: {stats['to_process']} 个")
        logger.info(f"    - 新文件: {len(stats['new'])} 个")
        logger.info(f"    - 已修改: {len(stats['modified'])} 个")
        logger.info(f"  跳过（未变化）: {len(stats['unchanged'])} 个")
        if stats['error_skipped']:
            logger.info(f"  跳过（之前出错）: {len(stats['error_skipped'])} 个")
        
        return to_process, stats
    
    def update_record(self, file_path: Union[str, Path]):
        """
        更新文件记录
        
        Args:
            file_path: 文件路径
        """
        file_path = Path(file_path)
        file_key = str(file_path.resolve())
        
        try:
            # 计算并保存哈希值
            file_hash = FileUtils.calculate_file_hash(file_path, 'md5')
            self.file_hashes[file_key] = file_hash
            
            # 保存时间戳
            self.file_timestamps[file_key] = file_path.stat().st_mtime
            
        except Exception as e:
            logger.warning(f"更新文件记录失败: {file_path}, 错误: {e}")
    
    def update_records(self, file_paths: List[Union[str, Path]]):
        """
        批量更新文件记录
        
        Args:
            file_paths: 文件路径列表
        """
        logger.info(f"更新 {len(file_paths)} 个文件的记录")
        for fp in file_paths:
            self.update_record(fp)
        self._save_records()
        logger.info("文件记录更新完成")
    
    def remove_record(self, file_path: Union[str, Path]):
        """
        删除文件记录
        
        Args:
            file_path: 文件路径
        """
        file_path = Path(file_path)
        file_key = str(file_path.resolve())
        
        if file_key in self.file_hashes:
            del self.file_hashes[file_key]
        if file_key in self.file_timestamps:
            del self.file_timestamps[file_key]
        if file_key in self.file_errors:
            del self.file_errors[file_key]
    
    def record_error(self, file_path: Union[str, Path], error_message: str):
        """
        记录文件处理错误
        
        Args:
            file_path: 文件路径
            error_message: 错误信息
        """
        file_path = Path(file_path)
        file_key = str(file_path.resolve())
        
        try:
            # 计算文件哈希（用于后续检查文件是否修改）
            file_hash = FileUtils.calculate_file_hash(file_path, 'md5')
            
            self.file_errors[file_key] = {
                'error': error_message,
                'hash': file_hash,
                'timestamp': datetime.now().isoformat(),
            }
            self._save_records()
            logger.debug(f"已记录错误: {file_path}")
        except Exception as e:
            logger.warning(f"记录错误失败: {file_path}, 错误: {e}")
    
    def get_error_files(self) -> List[str]:
        """
        获取有错误记录的文件列表
        
        Returns:
            文件路径列表
        """
        return list(self.file_errors.keys())
    
    def clear_error_records(self):
        """清空所有错误记录"""
        self.file_errors.clear()
        self._save_records()
        logger.info("已清空所有错误记录")
    
    # ========== 进度记录方法（断点续传） ==========
    
    def save_progress(self, batch_id: str, processed_files: List[str], total_files: int):
        """
        保存处理进度
        
        Args:
            batch_id: 批次ID（通常是输入目录的哈希或时间戳）
            processed_files: 已处理的文件路径列表
            total_files: 总文件数
        """
        self.progress = {
            'batch_id': batch_id,
            'processed_files': processed_files,
            'total_files': total_files,
            'last_update': datetime.now().isoformat(),
            'completed': len(processed_files) >= total_files,
        }
        self._save_records()
        logger.debug(f"已保存进度: {len(processed_files)}/{total_files}")
    
    def load_progress(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """
        加载处理进度
        
        Args:
            batch_id: 批次ID
            
        Returns:
            进度信息字典，如果没有记录则返回None
        """
        if not self.progress or self.progress.get('batch_id') != batch_id:
            return None
        return self.progress
    
    def get_processed_files(self, batch_id: str) -> List[str]:
        """
        获取已处理的文件列表
        
        Args:
            batch_id: 批次ID
            
        Returns:
            已处理的文件路径列表
        """
        progress = self.load_progress(batch_id)
        if progress:
            return progress.get('processed_files', [])
        return []
    
    def clear_progress(self):
        """清除进度记录"""
        self.progress = {}
        self._save_records()
        logger.info("已清除进度记录")
    
    def clean_orphaned_records(self, valid_paths: Optional[List[Union[str, Path]]] = None):
        """
        清理无效的记录（文件已不存在）
        
        Args:
            valid_paths: 有效的文件路径列表，如果为 None 则检查文件是否存在
        """
        if valid_paths is not None:
            valid_set = {str(Path(fp).resolve()) for fp in valid_paths}
            to_remove = [
                key for key in self.file_hashes
                if key not in valid_set
            ]
        else:
            to_remove = [
                key for key in self.file_hashes
                if not Path(key).exists()
            ]
        
        for key in to_remove:
            del self.file_hashes[key]
            if key in self.file_timestamps:
                del self.file_timestamps[key]
            if key in self.file_errors:
                del self.file_errors[key]
        
        if to_remove:
            logger.info(f"清理了 {len(to_remove)} 条无效记录")
            self._save_records()
    
    def clear_all_records(self):
        """清空所有记录（用于全量重建）"""
        self.file_hashes.clear()
        self.file_timestamps.clear()
        self.file_errors.clear()
        self.progress.clear()
        self._save_records()
        logger.info("已清空所有文件记录")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            统计信息字典
        """
        return {
            'enabled': self.enabled,
            'total_recorded': len(self.file_hashes),
            'hash_file': str(self.hash_file),
            'timestamp_file': str(self.timestamp_file),
            'last_update': datetime.fromtimestamp(
                max(self.file_timestamps.values()) if self.file_timestamps else 0
            ).isoformat() if self.file_timestamps else None,
        }
    
    def get_recorded_files(self) -> List[str]:
        """
        获取已记录的文件列表
        
        Returns:
            文件路径列表
        """
        return list(self.file_hashes.keys())
