"""
进度追踪器模块

提供通用进度条显示功能，支持主/副进度条、时间估算、ANSI 控制。
"""

import sys
from datetime import datetime
from typing import Any, Dict, Optional


class ProgressTracker:
    """进度追踪器"""

    def __init__(self, total: int, desc: str = "处理中", bar_length: int = 40, enabled: bool = True):
        self.total = total
        self.desc = desc
        self.bar_length = bar_length
        self.enabled = enabled
        self.current = 0
        self.start_time = datetime.now()
        self.sub_progress = None
        self._last_lines_count = 1

    def update(self, n: int = 1, current_item: str = ""):
        if not self.enabled:
            return
        self.current += n
        self._draw(current_item)

    def _draw(self, current_item: str = ""):
        progress = self.current / self.total if self.total > 0 else 1.0
        filled = int(self.bar_length * progress)
        bar = '█' * filled + '░' * (self.bar_length - filled)
        percentage = progress * 100

        elapsed = (datetime.now() - self.start_time).total_seconds()
        if self.current > 0:
            avg_time = elapsed / self.current
            remaining = avg_time * (self.total - self.current)
            time_str = f"耗时: {self._format_time(elapsed)} | 剩余: {self._format_time(remaining)}"
        else:
            time_str = f"耗时: {self._format_time(elapsed)}"

        item_str = current_item[:25] if current_item else ""

        self._clear_previous_lines()

        line1 = f"{self.desc}: [{bar}] {percentage:5.1f}% ({self.current}/{self.total}) {time_str}"
        if item_str:
            line1 += f" | 当前: {item_str:<25}"

        sys.stdout.write(line1)
        lines_count = 1

        if self.sub_progress:
            sub_line = self._format_sub_progress()
            if sub_line:
                sys.stdout.write("\n" + sub_line)
                lines_count = 2

        sys.stdout.flush()
        self._last_lines_count = lines_count

    def _format_sub_progress(self) -> str:
        if not self.sub_progress:
            return ""

        sub = self.sub_progress
        desc = sub.get('desc', '子任务')
        current = sub.get('current', 0)
        total = sub.get('total', 100)
        message = sub.get('message', '')

        if total <= 0:
            return f"  [{desc}] {message}"

        progress = current / total
        filled = int(self.bar_length * progress)
        bar = '█' * filled + '░' * (self.bar_length - filled)
        percentage = progress * 100

        line = f"  [{desc}] [{bar}] {percentage:5.1f}% ({current}/{total})"
        if message:
            line += f" {message}"
        return line

    def _clear_previous_lines(self):
        if self._last_lines_count <= 0:
            return

        for _ in range(self._last_lines_count - 1):
            sys.stdout.write('\033[F')

        for i in range(self._last_lines_count):
            sys.stdout.write('\r\033[2K')
            if i < self._last_lines_count - 1:
                sys.stdout.write('\033[B')

        for _ in range(self._last_lines_count - 1):
            sys.stdout.write('\033[F')

        sys.stdout.flush()

    def set_sub_progress(self, desc: str = "", current: int = 0, total: int = 0, message: str = ""):
        if not self.enabled:
            return
        self.sub_progress = {
            'desc': desc,
            'current': current,
            'total': total,
            'message': message,
        }
        self._draw()

    def clear_sub_progress(self):
        self.sub_progress = None
        self._draw()

    def close(self, clear_line: bool = False, message: str = ""):
        if not self.enabled:
            return
        if clear_line:
            self._clear_previous_lines()
        else:
            sys.stdout.write("\n")
        if message:
            sys.stdout.write(f"{message}\n")
        sys.stdout.flush()
        self._last_lines_count = 0

    @staticmethod
    def _format_time(seconds: float) -> str:
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            return f"{seconds/60:.1f}m"
        else:
            return f"{seconds/3600:.1f}h"
