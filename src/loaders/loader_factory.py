"""
文档加载器工厂

提供加载器注册和获取功能。
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union

from .base import BaseLoader


class LoaderFactory:
    """加载器工厂类"""
    
    _loaders: Dict[str, Type[BaseLoader]] = {}
    
    @classmethod
    def register(cls, extension: str, loader_class: Type[BaseLoader]):
        """
        注册加载器
        
        Args:
            extension: 文件扩展名（如 '.pdf'）
            loader_class: 加载器类
        """
        extension = extension.lower()
        if not extension.startswith('.'):
            extension = f'.{extension}'
        
        cls._loaders[extension] = loader_class
    
    @classmethod
    def get_loader(
        cls,
        file_path: Union[str, Path],
        config: Optional[Dict[str, Any]] = None
    ) -> Optional[BaseLoader]:
        """
        获取适合该文件的加载器
        
        Args:
            file_path: 文件路径
            config: 加载器配置
            
        Returns:
            加载器实例，如果没有找到则返回None
        """
        file_path = Path(file_path)
        extension = file_path.suffix.lower()
        
        loader_class = cls._loaders.get(extension)
        if loader_class:
            return loader_class(config)
        
        return None
    
    @classmethod
    def get_supported_extensions(cls) -> list:
        """
        获取支持的文件扩展名列表
        
        Returns:
            扩展名列表
        """
        return list(cls._loaders.keys())
    
    @classmethod
    def is_supported(cls, file_path: Union[str, Path]) -> bool:
        """
        检查文件类型是否被支持
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否支持
        """
        file_path = Path(file_path)
        extension = file_path.suffix.lower()
        return extension in cls._loaders


# 便捷函数
def get_loader(file_path: Union[str, Path], config: Optional[Dict[str, Any]] = None) -> Optional[BaseLoader]:
    """
    获取加载器
    
    Args:
        file_path: 文件路径
        config: 加载器配置
        
    Returns:
        加载器实例
    """
    return LoaderFactory.get_loader(file_path, config)


# 注册所有加载器
def register_all_loaders():
    """注册所有内置加载器"""
    from .pdf_loader import PDFLoader
    from .word_loader import WordLoader
    from .excel_loader import ExcelLoader
    from .ppt_loader import PPTLoader
    from .text_loader import TextLoader
    from .html_loader import HTMLLoader
    from .caj_loader import CAJLoader
    
    # PDF
    LoaderFactory.register('.pdf', PDFLoader)
    
    # Word
    LoaderFactory.register('.docx', WordLoader)
    LoaderFactory.register('.doc', WordLoader)
    LoaderFactory.register('.wps', WordLoader)
    
    # Excel
    LoaderFactory.register('.xlsx', ExcelLoader)
    LoaderFactory.register('.xls', ExcelLoader)
    
    # PowerPoint
    LoaderFactory.register('.pptx', PPTLoader)
    LoaderFactory.register('.ppt', PPTLoader)
    LoaderFactory.register('.ppsx', PPTLoader)
    
    # Text
    LoaderFactory.register('.txt', TextLoader)
    LoaderFactory.register('.md', TextLoader)
    LoaderFactory.register('.csv', TextLoader)
    LoaderFactory.register('.json', TextLoader)
    LoaderFactory.register('.xml', TextLoader)
    
    # RTF
    from .rtf_loader import RTFLoader
    LoaderFactory.register('.rtf', RTFLoader)
    
    # HTML
    LoaderFactory.register('.html', HTMLLoader)
    LoaderFactory.register('.htm', HTMLLoader)
    
    # CAJ
    LoaderFactory.register('.caj', CAJLoader)


# 自动注册
register_all_loaders()
