"""
日志工具模块

提供结构化日志记录功能。
"""

import json
import logging
import sys
from pathlib import Path
from typing import Optional

import structlog


class JsonFormatter(logging.Formatter):
    """自定义JSON格式化器，确保中文不被转义"""
    
    def format(self, record):
        # 获取消息
        msg = record.getMessage()
        
        # 如果是JSON字符串，尝试解析并重新格式化
        try:
            data = json.loads(msg)
            # 使用 ensure_ascii=False 确保中文正常显示
            return json.dumps(data, ensure_ascii=False, separators=(',', ':'))
        except (json.JSONDecodeError, TypeError):
            # 不是JSON，直接返回原消息
            return msg


def setup_logging(
    level: str = "INFO",
    format_type: str = "structured",
    log_file: Optional[str] = None,
    console_output: bool = True,
    console_level: Optional[str] = None
):
    """
    配置日志系统
    
    Args:
        level: 全局日志级别 (DEBUG, INFO, WARNING, ERROR)
        format_type: 日志格式类型 (simple, structured)
        log_file: 日志文件路径
        console_output: 是否输出到控制台
        console_level: 控制台日志级别，None则使用level
    """
    # 确定控制台日志级别
    effective_console_level = console_level or level
    
    # 配置标准库logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper()),
    )
    
    # 配置structlog
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    
    if format_type == "structured":
        processors.append(structlog.processors.JSONRenderer(ensure_ascii=False))
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    root_logger = logging.getLogger()
    
    # 添加文件处理器
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(getattr(logging, level.upper()))
        
        if format_type == "structured":
            # 使用自定义JSON格式化器确保中文不被转义
            formatter = JsonFormatter()
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        file_handler.setFormatter(formatter)
        
        root_logger.addHandler(file_handler)
    
    # 配置控制台输出
    # 先移除现有的控制台处理器
    for handler in root_logger.handlers[:]:
        if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stdout:
            root_logger.removeHandler(handler)
    
    # 根据配置添加控制台处理器
    if console_output and effective_console_level.upper() != "NONE":
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, effective_console_level.upper()))
        
        if format_type == "structured":
            formatter = logging.Formatter('%(message)s')
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    获取logger实例
    
    Args:
        name: logger名称
        
    Returns:
        BoundLogger实例
    """
    return structlog.get_logger(name)
