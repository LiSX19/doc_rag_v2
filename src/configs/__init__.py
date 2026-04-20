"""
配置模块

提供配置加载和管理功能。
"""

from .config_manager import ConfigManager, get_config

__all__ = [
    "ConfigManager",
    "get_config",
]
