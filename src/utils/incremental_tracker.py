"""
增量更新追踪模块

用于记录已处理文件的哈希值，支持全量更新和增量更新模式。
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from .file_utils import FileUtils
from .logger import get_logger

logger = get_logger(__name__)


class IncrementalTracker:
    """增量更新追踪器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化增量更新追踪器
        
        Args:
            config: 配置字典，包含：
                - incremental_update.enabled: 是否启用增量更新
                - incremental_update.hash_file: 哈希记录文件路径
                - incremental_update.timestamp_file: 时间戳记录文件路径
        """
        self.config = config or {}
        
        # 读取增量更新配置
        inc_config = self.config.get('incremental_update', {})
        self.enabled = inc_config.get('enabled', True)
        
        # 哈希记录文件
        self.hash_file = Path(inc_config.get('hash_file', './cache/file_hashes.json'))
        self.hash_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 时间戳记录文件
        self.timestamp_file = Path(inc_config.get('timestamp_file', './cache/file_timestamps.json'))
        self.timestamp_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 加载已记录的哈希值
        self.file_hashes: Dict[str, str] = {}
        self.file_timestamps: Dict[str, float] = {}
        self._load_records()
        
        logger.info(f"增量更新追踪器初始化完成，模式: {'增量' if self.enabled else '全量'}")
        if self.enabled:
            logger.info(f"已记录文件数: {len(self.file_hashes)}")
    
    def _load_records(self):
        """加载已记录的哈希值和时间戳"""
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
    
    def _save_records(self):
        """保存哈希值和时间戳记录"""
        try:
            # 保存哈希记录
            with open(self.hash_file, 'w', encoding='utf-8') as f:
                json.dump(self.file_hashes, f, ensure_ascii=False, indent=2)
            
            # 保存时间戳记录
            with open(self.timestamp_file, 'w', encoding='utf-8') as f:
                json.dump(self.file_timestamps, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"已保存 {len(self.file_hashes)} 条记录")
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
            - (True, "full_update"): 全量更新模式
        """
        file_path = Path(file_path)
        file_key = str(file_path.resolve())
        
        # 全量更新模式
        if not self.enabled:
            return True, "full_update"
        
        # 文件不存在于记录中（新文件）
        if file_key not in self.file_hashes:
            return True, "new"
        
        # 计算当前哈希值
        try:
            current_hash = FileUtils.calculate_file_hash(file_path, 'md5')
        except Exception as e:
            logger.warning(f"计算文件哈希失败: {file_path}, 错误: {e}")
            return True, "hash_error"
        
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
            统计信息包含：new, modified, unchanged, filtered 等分类
        """
        if force_full or not self.enabled:
            logger.info("全量更新模式：处理所有文件")
            return [Path(fp) for fp in file_paths], {
                'total': len(file_paths),
                'to_process': len(file_paths),
                'new': 0,
                'modified': 0,
                'unchanged': 0,
                'mode': 'full'
            }
        
        to_process = []
        stats = {
            'total': len(file_paths),
            'to_process': 0,
            'new': [],
            'modified': [],
            'unchanged': [],
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
                stats['unchanged'].append(str(fp))
        
        stats['to_process'] = len(to_process)
        
        # 输出统计信息
        logger.info(f"文件筛选完成:")
        logger.info(f"  总计: {stats['total']} 个")
        logger.info(f"  需要处理: {stats['to_process']} 个")
        logger.info(f"    - 新文件: {len(stats['new'])} 个")
        logger.info(f"    - 已修改: {len(stats['modified'])} 个")
        logger.info(f"  跳过（未变化）: {len(stats['unchanged'])} 个")
        
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
        
        if to_remove:
            logger.info(f"清理了 {len(to_remove)} 条无效记录")
            self._save_records()
    
    def clear_all_records(self):
        """清空所有记录（用于全量重建）"""
        self.file_hashes.clear()
        self.file_timestamps.clear()
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
