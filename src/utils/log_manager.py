"""
日志管理模块

统一管理错误日志和过滤日志的读写操作。
取代 pipeline.py 和 pipeline_manager.py 中分散的日志写入代码。
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .logger import get_logger

logger = get_logger(__name__)


class ErrorLogger:
    """错误日志管理器，负责 error_log.json 的读写与合并"""

    def __init__(self, cache_dir: Optional[str] = None):
        self.log_path = Path(cache_dir or './cache') / 'error_log.json'
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, error_entry: Dict[str, Any]):
        """实时追加单条错误记录"""
        data = self._load()
        data['errors'].append(error_entry)
        data['total_errors'] = len(data['errors'])
        data['updated_at'] = datetime.now().isoformat()
        self._save(data)

    def merge(self, error_entries: List[Dict[str, Any]]):
        """合并一批错误记录（按文件路径+时间戳去重）"""
        if not error_entries:
            return
        data = self._load()
        seen = set()
        all_errors = []
        for error in data['errors'] + error_entries:
            key = (error.get('file_path', ''), error.get('timestamp', ''))
            if key not in seen:
                seen.add(key)
                all_errors.append(error)
        data['errors'] = all_errors
        data['total_errors'] = len(all_errors)
        data['updated_at'] = datetime.now().isoformat()
        self._save(data)

    def _load(self) -> Dict:
        if self.log_path.exists():
            try:
                with open(self.log_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载错误日志失败: {e}")
        return {'updated_at': '', 'total_errors': 0, 'errors': []}

    def _save(self, data: Dict):
        try:
            with open(self.log_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"保存错误日志失败: {e}")


class FilterLogger:
    """过滤日志管理器，负责 filter_log.json 的读写与合并"""

    def __init__(self, cache_dir: Optional[str] = None):
        self.log_path = Path(cache_dir or './cache') / 'filter_log.json'
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, filter_entry: Dict[str, Any]):
        """实时追加单条过滤记录"""
        data = self._load()
        data['filtered_files'].append(filter_entry)
        data['total_filtered'] = len(data['filtered_files'])
        data['updated_at'] = datetime.now().isoformat()
        self._save(data)

    def merge(self, filter_entries: List[Dict[str, Any]]):
        """合并一批过滤记录（按文件路径+时间戳去重）"""
        if not filter_entries:
            return
        data = self._load()
        seen = set()
        all_filtered = []
        for entry in data['filtered_files'] + filter_entries:
            key = (entry.get('file_path', ''), entry.get('timestamp', ''))
            if key not in seen:
                seen.add(key)
                all_filtered.append(entry)
        data['filtered_files'] = all_filtered
        data['total_filtered'] = len(all_filtered)
        data['updated_at'] = datetime.now().isoformat()
        self._save(data)

    def _load(self) -> Dict:
        if self.log_path.exists():
            try:
                with open(self.log_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载过滤日志失败: {e}")
        return {'updated_at': '', 'total_filtered': 0, 'filtered_files': []}

    def _save(self, data: Dict):
        try:
            with open(self.log_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"保存过滤日志失败: {e}")
