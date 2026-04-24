"""
Pipeline 工具模块
"""

import sys
from datetime import datetime
from typing import Optional


class ProgressTracker:
    """进度追踪器"""

    def __init__(self, total: int, desc: str = "处理中", bar_length: int = 40, enabled: bool = True):
        """
        初始化进度追踪器

        Args:
            total: 总任务数
            desc: 描述文本
            bar_length: 进度条长度
            enabled: 是否启用
        """
        self.total = total
        self.desc = desc
        self.bar_length = bar_length
        self.enabled = enabled
        self.current = 0
        self.start_time = datetime.now()
        self.sub_progress = None
        self._last_lines_count = 1

    def update(self, n: int = 1, current_item: str = ""):
        """
        更新进度

        Args:
            n: 进度增量
            current_item: 当前处理项名称
        """
        if not self.enabled:
            return

        self.current += n
        self._draw(current_item)

    def _draw(self, current_item: str = ""):
        """绘制进度条"""
        progress = self.current / self.total if self.total > 0 else 1.0
        filled = int(self.bar_length * progress)
        bar = '█' * filled + '░' * (self.bar_length - filled)
        percentage = progress * 100

        # 计算耗时和预估剩余时间
        elapsed = (datetime.now() - self.start_time).total_seconds()
        if self.current > 0:
            avg_time = elapsed / self.current
            remaining = avg_time * (self.total - self.current)
            time_str = f"耗时: {self._format_time(elapsed)} | 剩余: {self._format_time(remaining)}"
        else:
            time_str = f"耗时: {self._format_time(elapsed)}"

        # 截断当前项名称
        item_str = current_item[:30] if current_item else ""

        # 先清除之前的输出行
        self._clear_previous_lines()

        # 构建并输出主进度条
        line1 = f"{self.desc}: [{bar}] {percentage:5.1f}% ({self.current}/{self.total}) {time_str}"
        if item_str:
            line1 += f" | 当前: {item_str:<30}"

        sys.stdout.write(line1)
        lines_count = 1

        # 如果有副进度条，输出副进度条
        if self.sub_progress:
            sub_line = self._format_sub_progress()
            if sub_line:
                sys.stdout.write("\n" + sub_line)
                lines_count = 2

        sys.stdout.flush()
        self._last_lines_count = lines_count

    def _format_sub_progress(self) -> str:
        """格式化副进度条"""
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
        """清除之前的输出行"""
        if self._last_lines_count <= 0:
            return

        # 回到第一行
        for _ in range(self._last_lines_count - 1):
            sys.stdout.write('\033[F')  # 光标上移

        # 清除所有行
        for _ in range(self._last_lines_count):
            sys.stdout.write('\r\033[K')  # 回到行首并清除
            if _ < self._last_lines_count - 1:
                sys.stdout.write('\033[B')  # 光标下移（除了最后一行）

        # 回到第一行
        for _ in range(self._last_lines_count - 1):
            sys.stdout.write('\033[F')

        sys.stdout.flush()

    def set_sub_progress(self, desc: str = "", current: int = 0, total: int = 0, message: str = ""):
        """
        设置副进度条

        Args:
            desc: 副进度条描述
            current: 当前进度
            total: 总进度
            message: 进度消息
        """
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
        """清除副进度条"""
        self.sub_progress = None
        self._draw()

    def close(self, message: str = ""):
        """关闭进度条"""
        if not self.enabled:
            return

        sys.stdout.write("\n")
        if message:
            sys.stdout.write(f"{message}\n")
        sys.stdout.flush()
        self._last_lines_count = 0

    @staticmethod
    def _format_time(seconds: float) -> str:
        """格式化时间显示"""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            return f"{seconds/60:.1f}m"
        else:
            return f"{seconds/3600:.1f}h"


def print_stats(stats: dict):
    """打印处理统计信息"""
    print("\n" + "=" * 60)
    print("处理完成统计")
    print("=" * 60)
    print(f"总文件数: {stats.get('total_files', 0)}")
    print(f"成功加载: {stats.get('loaded_files', 0)}")
    print(f"成功清洗: {stats.get('cleaned_files', 0)}")
    print(f"成功分块: {stats.get('chunked_files', 0)}")
    print(f"成功去重: {stats.get('deduped_files', 0)}")
    print(f"总分块数: {stats.get('total_chunks', 0)}")
    print(f"唯一分块数: {stats.get('unique_chunks', 0)}")
    print(f"去重分块数: {stats.get('removed_chunks', 0)}")
    print(f"编码分块数: {stats.get('encoded_chunks', 0)}")
    print(f"存储分块数: {stats.get('stored_chunks', 0)}")

    total_chunks = stats.get('total_chunks', 0)
    removed_chunks = stats.get('removed_chunks', 0)
    if total_chunks > 0:
        dedup_rate = removed_chunks / total_chunks * 100
        print(f"去重率: {dedup_rate:.1f}%")

    errors = stats.get('errors', [])
    print(f"错误数: {len(errors)}")

    if errors:
        print("\n错误详情:")
        for error in errors[:10]:  # 只显示前10个错误
            print(f"  - {error}")
        if len(errors) > 10:
            print(f"  ... 还有 {len(errors) - 10} 个错误")
