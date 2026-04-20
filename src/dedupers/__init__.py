"""
去重模块

提供多级文本去重功能。
"""

from .base import BaseDeduper
from .deduper import Deduper

__all__ = [
    "BaseDeduper",
    "Deduper",
]
