"""
交互式配置模块

提供交互式命令行界面，让用户配置系统参数。
简化版本：只配置关键参数，保存到用户配置文件 config.yaml
"""

import click
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable


class ConfigItem:
    """配置项定义"""
    
    def __init__(
        self,
        key: str,
        name: str,
        description: str,
        default: Any,
        value_type: str = "string",
        choices: Optional[List[str]] = None,
        validator: Optional[Callable] = None,
        category: str = "general"
    ):
        """
        初始化配置项
        
        Args:
            key: 配置键名（如 paths.input_dir）
            name: 显示名称
            description: 详细说明
            default: 默认值
            value_type: 值类型 (string, int, float, bool, choice, path)
            choices: 可选值列表（仅用于choice类型）
            validator: 验证函数
            category: 配置分类
        """
        self.key = key
        self.name = name
        self.description = description
        self.default = default
        self.value_type = value_type
        self.choices = choices
        self.validator = validator
        self.category = category
    
    def prompt(self) -> Any:
        """交互式提示用户输入"""
        print(f"\n{'='*60}")
        print(f"【{self.name}】")
        print(f"{'='*60}")
        print(f"说明: {self.description}")
        print(f"默认值: {self.default}")
        
        if self.value_type == "bool":
            return self._prompt_bool()
        elif self.value_type == "choice":
            return self._prompt_choice()
        elif self.value_type == "int":
            return self._prompt_int()
        elif self.value_type == "path":
            return self._prompt_path()
        else:
            return self._prompt_string()
    
    def _prompt_bool(self) -> bool:
        """提示布尔值"""
        default_str = "Y" if self.default else "N"
        while True:
            value = click.prompt(
                f"是否启用? (Y/N)",
                default=default_str,
                show_default=True
            ).strip().upper()
            if value in ['Y', 'YES', '是']:
                return True
            elif value in ['N', 'NO', '否']:
                return False
            print("请输入 Y 或 N")
    
    def _prompt_choice(self) -> str:
        """提示选择项"""
        print("\n可选值:")
        for i, choice in enumerate(self.choices, 1):
            marker = "【默认】" if choice == self.default else ""
            print(f"  {i}. {choice} {marker}")
        
        while True:
            value = click.prompt(
                "请选择（输入数字或名称）",
                default=str(self.choices.index(self.default) + 1) if self.default in self.choices else "1",
                show_default=True
            ).strip()
            
            # 尝试解析为数字
            try:
                idx = int(value) - 1
                if 0 <= idx < len(self.choices):
                    return self.choices[idx]
            except ValueError:
                pass
            
            # 直接匹配名称
            if value in self.choices:
                return value
            
            print(f"无效选择，请重新输入")
    
    def _prompt_int(self) -> int:
        """提示整数"""
        while True:
            try:
                value = click.prompt(
                    "请输入整数",
                    default=str(self.default),
                    show_default=True
                )
                result = int(value)
                if self.validator and not self.validator(result):
                    print("输入值验证失败，请重新输入")
                    continue
                return result
            except ValueError:
                print("请输入有效的整数")
    
    def _prompt_path(self) -> str:
        """提示路径"""
        while True:
            value = click.prompt(
                "请输入路径",
                default=str(self.default),
                show_default=True
            ).strip()
            
            # 展开用户目录
            path = Path(value).expanduser()
            
            if self.validator and not self.validator(path):
                print("路径验证失败，请重新输入")
                continue
            
            return str(path)
    
    def _prompt_string(self) -> str:
        """提示字符串"""
        value = click.prompt(
            "请输入",
            default=str(self.default),
            show_default=True
        ).strip()
        
        if self.validator and not self.validator(value):
            print("输入值验证失败，使用默认值")
            return self.default
        
        return value


class InteractiveConfigurator:
    """交互式配置器 - 只配置关键参数"""
    
    # 关键配置项列表（与ConfigManager中的user_keys保持一致）
    CONFIG_ITEMS = [
        # 路径配置
        ConfigItem(
            key="paths.input_dir",
            name="输入目录",
            description="指定要处理的文档所在目录",
            default="./data",
            value_type="path",
            category="paths"
        ),
        ConfigItem(
            key="paths.output_dir",
            name="输出目录",
            description="指定处理结果的输出目录",
            default="./outputs",
            value_type="path",
            category="paths"
        ),
        ConfigItem(
            key="paths.models_dir",
            name="模型目录",
            description="存放Embedding模型的目录",
            default="./models",
            value_type="path",
            category="paths"
        ),
        
        # 日志配置
        ConfigItem(
            key="logging.level",
            name="日志级别",
            description="设置日志输出级别：DEBUG显示所有信息，INFO显示一般信息，WARNING只显示警告和错误",
            default="INFO",
            value_type="choice",
            choices=["DEBUG", "INFO", "WARNING", "ERROR"],
            category="logging"
        ),
        ConfigItem(
            key="logging.console_output",
            name="控制台日志输出",
            description="是否将日志输出到控制台",
            default=True,
            value_type="bool",
            category="logging"
        ),
        
        # 文档加载配置
        ConfigItem(
            key="loader.parallel.enabled",
            name="并行加载",
            description="启用并行处理以加速文档加载",
            default=True,
            value_type="bool",
            category="loader"
        ),
        ConfigItem(
            key="loader.parallel.max_workers",
            name="加载线程数",
            description="并行加载的最大线程数（1-16）",
            default=2,
            value_type="int",
            validator=lambda x: 1 <= x <= 16,
            category="loader"
        ),
        ConfigItem(
            key="loader.ocr.enabled",
            name="OCR支持",
            description="启用OCR功能处理扫描版PDF",
            default=True,
            value_type="bool",
            category="loader"
        ),
        
        # 文本清洗配置
        ConfigItem(
            key="cleaner.unstructured.enabled",
            name="Unstructured结构清洗",
            description="启用Unstructured库进行高级结构清洗",
            default=True,
            value_type="bool",
            category="cleaner"
        ),
        ConfigItem(
            key="cleaner.quality_check.enabled",
            name="质量检查",
            description="清洗后进行质量检查",
            default=True,
            value_type="bool",
            category="cleaner"
        ),
        ConfigItem(
            key="cleaner.parallel.enabled",
            name="并行清洗",
            description="启用并行处理加速文本清洗",
            default=False,
            value_type="bool",
            category="cleaner"
        ),
        
        # 文本分块配置
        ConfigItem(
            key="chunker.chunk_size",
            name="分块大小",
            description="每个文本块的最大字符数（100-2000）",
            default=500,
            value_type="int",
            validator=lambda x: 100 <= x <= 2000,
            category="chunker"
        ),
        ConfigItem(
            key="chunker.chunk_overlap",
            name="分块重叠长度",
            description="相邻文本块之间的重叠字符数（0-200）",
            default=50,
            value_type="int",
            validator=lambda x: 0 <= x <= 200,
            category="chunker"
        ),
        ConfigItem(
            key="chunker.post_process.min_chunk_length",
            name="最小分块长度",
            description="过滤掉小于此长度的文本块",
            default=20,
            value_type="int",
            validator=lambda x: x >= 0,
            category="chunker"
        ),
        
        # 性能配置
        ConfigItem(
            key="performance.max_workers",
            name="最大工作线程数",
            description="系统整体最大并行工作线程数",
            default=2,
            value_type="int",
            validator=lambda x: 1 <= x <= 16,
            category="performance"
        ),
        ConfigItem(
            key="performance.incremental_update.enabled",
            name="增量更新",
            description="启用增量更新，只处理新增或修改的文件",
            default=True,
            value_type="bool",
            category="performance"
        ),
    ]
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化配置器
        
        Args:
            config: 当前配置字典
        """
        self.config = config
        self.values = {}
    
    def run(self, category: Optional[str] = None) -> Dict[str, Any]:
        """
        运行交互式配置
        
        Args:
            category: 指定配置分类，None表示配置所有
            
        Returns:
            用户修改的配置字典
        """
        print("\n" + "="*60)
        print(" DocRAG 交互式配置 ")
        print("="*60)
        print("\n提示: 直接按回车使用默认值，输入新值进行修改\n")
        
        # 筛选要配置的项目
        items = self.CONFIG_ITEMS
        if category:
            items = [item for item in items if item.category == category]
        
        # 交互式配置每个项目
        for item in items:
            # 获取当前值（从配置中读取）
            current_value = self._get_nested_config(item.key)
            if current_value is not None:
                item.default = current_value
            
            # 提示用户输入
            value = item.prompt()
            self.values[item.key] = value
        
        # 确认保存
        print("\n" + "="*60)
        print("配置摘要")
        print("="*60)
        for key, value in self.values.items():
            print(f"  {key}: {value}")
        
        if click.confirm("\n是否保存以上配置?", default=True):
            return self.values
        else:
            return {}
    
    def _get_nested_config(self, key: str) -> Any:
        """获取嵌套配置值"""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return None
        
        return value


def show_current_config(config: Dict[str, Any], format: str = "text"):
    """
    显示当前配置
    
    Args:
        config: 配置字典
        format: 输出格式 (text, yaml)
    """
    if format == "yaml":
        import yaml
        print(yaml.dump(config, allow_unicode=True, default_flow_style=False, sort_keys=False))
    else:
        # 文本格式
        print("\n" + "="*60)
        print(" 当前配置 ")
        print("="*60)
        
        def print_dict(d: Dict, indent: int = 0):
            for key, value in d.items():
                if isinstance(value, dict):
                    print("  " * indent + f"{key}:")
                    print_dict(value, indent + 1)
                else:
                    print("  " * indent + f"{key}: {value}")
        
        print_dict(config)


def get_config_categories() -> List[str]:
    """获取所有配置分类"""
    return [
        "paths",        # 路径配置
        "logging",      # 日志配置
        "loader",       # 文档加载配置
        "cleaner",      # 文本清洗配置
        "chunker",      # 文本分块配置
        "performance",  # 性能配置
    ]
