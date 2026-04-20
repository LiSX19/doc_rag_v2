"""
文件工具模块

提供文件操作相关工具函数。
"""

import hashlib
import json
import pickle
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


class FileUtils:
    """文件工具类"""
    
    @staticmethod
    def calculate_file_hash(file_path: Union[str, Path], algorithm: str = "md5") -> str:
        """
        计算文件哈希值
        
        Args:
            file_path: 文件路径
            algorithm: 哈希算法 (md5, sha256)
            
        Returns:
            哈希值字符串
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        hash_obj = hashlib.md5() if algorithm == "md5" else hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hash_obj.update(chunk)
        
        return hash_obj.hexdigest()
    
    @staticmethod
    def calculate_content_hash(content: str, algorithm: str = "md5") -> str:
        """
        计算内容哈希值
        
        Args:
            content: 文本内容
            algorithm: 哈希算法
            
        Returns:
            哈希值字符串
        """
        hash_obj = hashlib.md5() if algorithm == "md5" else hashlib.sha256()
        hash_obj.update(content.encode('utf-8'))
        return hash_obj.hexdigest()
    
    @staticmethod
    def save_json(data: Any, file_path: Union[str, Path], ensure_ascii: bool = False, indent: int = 2):
        """
        保存数据为JSON文件
        
        Args:
            data: 要保存的数据
            file_path: 文件路径
            ensure_ascii: 是否转义非ASCII字符
            indent: 缩进空格数
        """
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=ensure_ascii, indent=indent)
    
    @staticmethod
    def load_json(file_path: Union[str, Path]) -> Any:
        """
        加载JSON文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            加载的数据
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    @staticmethod
    def save_pickle(data: Any, file_path: Union[str, Path]):
        """
        保存数据为pickle文件
        
        Args:
            data: 要保存的数据
            file_path: 文件路径
        """
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'wb') as f:
            pickle.dump(data, f)
    
    @staticmethod
    def load_pickle(file_path: Union[str, Path]) -> Any:
        """
        加载pickle文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            加载的数据
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        with open(file_path, 'rb') as f:
            return pickle.load(f)
    
    @staticmethod
    def save_text(content: str, file_path: Union[str, Path]):
        """
        保存文本文件
        
        Args:
            content: 文本内容
            file_path: 文件路径
        """
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    @staticmethod
    def load_text(file_path: Union[str, Path]) -> str:
        """
        加载文本文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            文本内容
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    @staticmethod
    def get_file_extension(file_path: Union[str, Path]) -> str:
        """
        获取文件扩展名（小写）
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件扩展名（包含点，如.pdf）
        """
        return Path(file_path).suffix.lower()
    
    @staticmethod
    def get_file_name(file_path: Union[str, Path], with_extension: bool = True) -> str:
        """
        获取文件名
        
        Args:
            file_path: 文件路径
            with_extension: 是否包含扩展名
            
        Returns:
            文件名
        """
        path = Path(file_path)
        if with_extension:
            return path.name
        return path.stem
    
    @staticmethod
    def list_files(
        directory: Union[str, Path],
        extensions: Optional[List[str]] = None,
        recursive: bool = True
    ) -> List[Path]:
        """
        列出目录中的文件
        
        Args:
            directory: 目录路径
            extensions: 文件扩展名过滤列表（如 ['.pdf', '.docx']）
            recursive: 是否递归子目录
            
        Returns:
            文件路径列表
        """
        directory = Path(directory)
        if not directory.exists():
            return []
        
        if extensions:
            extensions = [ext.lower() if ext.startswith('.') else f'.{ext.lower()}' 
                         for ext in extensions]
        
        files = []
        pattern = "**/*" if recursive else "*"
        
        for file_path in directory.glob(pattern):
            if file_path.is_file():
                if extensions is None or file_path.suffix.lower() in extensions:
                    files.append(file_path)
        
        return sorted(files)
    
    @staticmethod
    def ensure_dir(directory: Union[str, Path]) -> Path:
        """
        确保目录存在，不存在则创建
        
        Args:
            directory: 目录路径
            
        Returns:
            目录路径
        """
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)
        return path
