"""
文档加载器基类
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional, Union


class BaseLoader(ABC):
    """文档加载器基类"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化加载器
        
        Args:
            config: 加载器配置
        """
        self.config = config or {}
    
    @abstractmethod
    def load(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        加载文档
        
        Args:
            file_path: 文件路径
            
        Returns:
            包含文档内容的字典，格式：
            {
                'content': str,  # 文档文本内容
                'metadata': dict,  # 文档元数据
                'pages': list,  # 分页内容（可选）
            }
        """
        pass
    
    @abstractmethod
    def supports(self, file_path: Union[str, Path]) -> bool:
        """
        检查是否支持该文件类型
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否支持
        """
        pass
    
    def extract_metadata(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        提取文件元数据
        
        Args:
            file_path: 文件路径
            
        Returns:
            元数据字典
        """
        file_path = Path(file_path)
        
        import os
        from datetime import datetime
        
        stat = os.stat(file_path)
        
        return {
            'source': str(file_path),
            'filename': file_path.name,
            'extension': file_path.suffix.lower(),
            'size_bytes': stat.st_size,
            'created_at': datetime.fromtimestamp(stat.st_ctime).isoformat(),
            'modified_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
        }
