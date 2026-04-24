"""
配置管理模块

提供配置加载、管理和访问功能。
简化后的配置结构：
- src/configs/default_config.yaml: 全局默认配置（所有参数）
- ./config.yaml: 用户配置（关键参数，通过set命令修改）
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional, Union

import yaml


class ConfigManager:
    """配置管理器"""
    
    # 默认配置文件路径
    DEFAULT_CONFIG_PATH = Path(__file__).parent / "default_config.yaml"
    # 用户配置文件路径（项目根目录）
    USER_CONFIG_PATH = Path.cwd() / "config.yaml"
    
    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        """
        初始化配置管理器
        
        Args:
            config_path: 可选的自定义配置文件路径
        """
        self._config: Dict[str, Any] = {}
        
        # 第1步: 加载全局默认配置
        self._load_default_config()
        
        # 第2步: 加载用户配置（如果存在）
        if self.USER_CONFIG_PATH.exists():
            self._load_config(self.USER_CONFIG_PATH)
        
        # 第3步: 加载自定义配置（如果提供）
        if config_path:
            self._load_config(config_path)
    
    def _load_default_config(self):
        """加载全局默认配置"""
        if self.DEFAULT_CONFIG_PATH.exists():
            with open(self.DEFAULT_CONFIG_PATH, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f) or {}
    
    def _load_config(self, config_path: Union[str, Path]):
        """
        加载配置文件并合并
        
        Args:
            config_path: 配置文件路径
        """
        config_path = Path(config_path)
        if not config_path.exists():
            return
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}
        
        # 递归合并配置
        self._merge_config(self._config, config)
    
    def _merge_config(self, base: Dict, update: Dict):
        """
        递归合并配置字典
        
        Args:
            base: 基础配置
            update: 更新配置
        """
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键，支持点号分隔（如 'paths.input_dir'）
            default: 默认值
            
        Returns:
            配置值
        """
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any, save: bool = False):
        """
        设置配置值
        
        Args:
            key: 配置键，支持点号分隔
            value: 配置值
            save: 是否同时保存到用户配置文件（默认 False，只在内存中修改）
        """
        keys = key.split('.')
        config = self._config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
        
        # 只有显式指定 save=True 时才保存到用户配置文件
        if save:
            self.save_user_config()
    
    def get_all(self) -> Dict[str, Any]:
        """
        获取所有配置
        
        Returns:
            配置字典的副本
        """
        return self._config.copy()
    
    def save_user_config(self):
        """保存用户配置到 config.yaml"""
        # 定义关键的用户可配置项
        user_keys = [
            'paths.input_dir',
            'paths.output_dir',
            'paths.models_dir',
            'paths.logs_dir',
            'paths.cache_dir',
            'logging.level',
            'logging.console_output',
            'loader.parallel.enabled',
            'loader.parallel.max_workers',
            'loader.ocr.enabled',
            'cleaner.unstructured.enabled',
            'cleaner.quality_check.enabled',
            'cleaner.parallel.enabled',
            'chunker.chunk_size',
            'chunker.chunk_overlap',
            'chunker.post_process.min_chunk_length',
            'performance.max_workers',
            'performance.incremental_update.enabled',
            'output.mode',
            'output.stages',
        ]
        
        # 先加载现有的用户配置（保留用户手动添加的配置）
        existing_config = {}
        if self.USER_CONFIG_PATH.exists():
            try:
                with open(self.USER_CONFIG_PATH, 'r', encoding='utf-8') as f:
                    existing_config = yaml.safe_load(f) or {}
            except Exception:
                existing_config = {}
        
        # 更新关键配置项
        user_config = existing_config.copy()
        for key in user_keys:
            value = self.get(key)
            if value is not None:
                self._set_nested_value(user_config, key, value)
        
        # 保存到文件
        self.USER_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(self.USER_CONFIG_PATH, 'w', encoding='utf-8') as f:
            yaml.dump(user_config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    
    def _set_nested_value(self, config: Dict, key: str, value: Any):
        """设置嵌套配置值"""
        keys = key.split('.')
        target = config
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        target[keys[-1]] = value
    
    def save(self, file_path: Union[str, Path]):
        """
        保存完整配置到文件
        
        Args:
            file_path: 文件路径
        """
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(self._config, f, allow_unicode=True, default_flow_style=False)


# 全局配置管理器实例（懒加载）
_config_manager: Optional[ConfigManager] = None


def get_config(config_path: Optional[Union[str, Path]] = None) -> ConfigManager:
    """
    获取全局配置管理器实例
    
    Args:
        config_path: 可选的自定义配置文件路径
        
    Returns:
        ConfigManager实例
    """
    global _config_manager
    if _config_manager is None or config_path is not None:
        _config_manager = ConfigManager(config_path)
    return _config_manager
