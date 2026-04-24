"""
文本文件加载器

支持.txt、.md、.csv等纯文本格式。
"""

import csv
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .base import BaseLoader


class TextLoader(BaseLoader):
    """文本文件加载器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化文本加载器
        
        Args:
            config: 配置字典
        """
        super().__init__(config)
        
        self.encoding = self.config.get('encoding', 'utf-8')
        self._unstructured_available = self._check_unstructured()
    
    def _check_unstructured(self) -> bool:
        """检查Unstructured是否可用"""
        try:
            from unstructured.partition.text import partition_text
            from unstructured.partition.md import partition_md
            return True
        except ImportError:
            return False
    
    def supports(self, file_path: Union[str, Path]) -> bool:
        """检查是否支持该文件"""
        ext = Path(file_path).suffix.lower()
        return ext in ['.txt', '.md', '.csv', '.json', '.xml']
    
    def load(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        加载文本文件
        
        Args:
            file_path: 文本文件路径
            
        Returns:
            包含文档内容的字典
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        ext = file_path.suffix.lower()
        
        # CSV文件特殊处理
        if ext == '.csv':
            return self._load_csv(file_path)
        
        # Markdown文件
        if ext == '.md' and self._unstructured_available:
            try:
                return self._load_with_unstructured_md(file_path)
            except:
                pass
        
        # 普通文本文件
        if self._unstructured_available:
            try:
                return self._load_with_unstructured(file_path)
            except:
                pass
        
        # 直接读取
        return self._load_raw(file_path)
    
    def _load_with_unstructured(self, file_path: Path) -> Dict[str, Any]:
        """使用Unstructured加载文本"""
        from unstructured.partition.text import partition_text
        
        # 获取语言配置
        languages = self.config.get('loader.unstructured.languages', ['chi_sim', 'eng'])
        
        elements = partition_text(filename=str(file_path), languages=languages)
        
        texts = []
        for element in elements:
            text = str(element)
            if text.strip():
                texts.append(text)
        
        content = '\n\n'.join(texts)
        
        metadata = self.extract_metadata(file_path)
        metadata['parser'] = 'unstructured_text'
        
        return {
            'content': content,
            'metadata': metadata,
            'pages': [],
        }
    
    def _load_with_unstructured_md(self, file_path: Path) -> Dict[str, Any]:
        """使用Unstructured加载Markdown"""
        from unstructured.partition.md import partition_md
        
        # 获取语言配置
        languages = self.config.get('loader.unstructured.languages', ['chi_sim', 'eng'])
        
        elements = partition_md(filename=str(file_path), languages=languages)
        
        texts = []
        for element in elements:
            text = str(element)
            if text.strip():
                texts.append(text)
        
        content = '\n\n'.join(texts)
        
        metadata = self.extract_metadata(file_path)
        metadata['parser'] = 'unstructured_md'
        
        return {
            'content': content,
            'metadata': metadata,
            'pages': [],
        }
    
    def _load_raw(self, file_path: Path) -> Dict[str, Any]:
        """直接读取文本文件"""
        # 尝试多种编码
        encodings = [self.encoding, 'utf-8', 'gbk', 'gb2312', 'latin-1']
        
        content = None
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                break
            except UnicodeDecodeError:
                continue
        
        if content is None:
            raise RuntimeError(f"无法解码文件: {file_path}")
        
        metadata = self.extract_metadata(file_path)
        metadata['parser'] = 'raw_text'
        metadata['encoding'] = encoding
        
        return {
            'content': content,
            'metadata': metadata,
            'pages': [],
        }
    
    def _load_csv(self, file_path: Path) -> Dict[str, Any]:
        """加载CSV文件"""
        # 尝试多种编码
        encodings = [self.encoding, 'utf-8', 'gbk', 'gb2312']
        
        rows = []
        used_encoding = None
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding, newline='') as f:
                    reader = csv.reader(f)
                    for row in reader:
                        rows.append(' | '.join(row))
                used_encoding = encoding
                break
            except UnicodeDecodeError:
                continue
        
        if not rows:
            raise RuntimeError(f"无法解码CSV文件: {file_path}")
        
        content = '\n'.join(rows)
        
        metadata = self.extract_metadata(file_path)
        metadata['parser'] = 'csv'
        metadata['encoding'] = used_encoding
        metadata['row_count'] = len(rows)
        
        return {
            'content': content,
            'metadata': metadata,
            'pages': [],
        }
