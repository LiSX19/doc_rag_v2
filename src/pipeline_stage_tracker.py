"""
Pipeline 全局阶段追踪器

跟踪 pipeline 的全局阶段（去重、编码存储）完成状态。
解决中断后重新运行时，文件已标记为 completed 但全局阶段未执行的问题。

设计说明：该模块仅服务于 pipeline 流程，不属于通用工具，
因此放在 src/ 根目录而非 src/utils/ 下。
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from src.utils import get_logger

logger = get_logger(__name__)

STAGE_IDLE = 'idle'
STAGE_FILE_PROCESSING = 'file_processing'
STAGE_DEDUP = 'dedup'
STAGE_ENCODE_STORE = 'encode_store'
STAGE_COMPLETE = 'complete'


class PipelineStageTracker:
    """Pipeline 全局阶段追踪器"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        perf_config = self.config.get('performance', {})
        inc_config = perf_config.get('incremental_update', {})
        self.stage_file = Path(inc_config.get('stage_file', './cache/pipeline_stage.json'))
        self.stage_file.parent.mkdir(parents=True, exist_ok=True)
        self._state: Dict[str, Any] = {}
        self._load()

    def _load(self):
        if self.stage_file.exists():
            try:
                with open(self.stage_file, 'r', encoding='utf-8') as f:
                    self._state = json.load(f)
            except Exception as e:
                logger.warning(f"加载 pipeline 阶段状态失败: {e}")
                self._state = {}

    def _save(self):
        try:
            with open(self.stage_file, 'w', encoding='utf-8') as f:
                json.dump(self._state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"保存 pipeline 阶段状态失败: {e}")

    def get_stage(self) -> str:
        return self._state.get('stage', STAGE_IDLE)

    def get_stats(self) -> Dict[str, Any]:
        return self._state.get('stats', {})

    def get_batch_id(self) -> str:
        return self._state.get('batch_id', '')

    def set_stage(self, stage: str, stats: Optional[Dict[str, Any]] = None, batch_id: str = ''):
        self._state['stage'] = stage
        self._state['updated_at'] = datetime.now().isoformat()
        if stats is not None:
            self._state['stats'] = stats
        if batch_id:
            self._state['batch_id'] = batch_id
        if stage == STAGE_IDLE:
            self._state['stats'] = {}
            self._state['batch_id'] = ''
        self._save()

    def is_interrupted(self) -> bool:
        stage = self.get_stage()
        return stage in (STAGE_DEDUP, STAGE_ENCODE_STORE)

    def has_dedup_done(self) -> bool:
        stage = self.get_stage()
        return stage in (STAGE_ENCODE_STORE, STAGE_COMPLETE)

    def has_encode_done(self) -> bool:
        return self.get_stage() == STAGE_COMPLETE

    def clear(self):
        self._state = {
            'stage': STAGE_IDLE,
            'updated_at': '',
            'batch_id': '',
            'stats': {},
        }
        self._save()
        logger.info("Pipeline 阶段状态已重置")
