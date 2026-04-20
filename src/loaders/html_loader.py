"""
HTML文档加载器

支持.html和.htm格式。
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .base import BaseLoader


class HTMLLoader(BaseLoader):
    """HTML加载器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化HTML加载器
        
        Args:
            config: 配置字典
        """
        super().__init__(config)
        
        self._unstructured_available = self._check_unstructured()
        self._bs4_available = self._check_bs4()
    
    def _check_unstructured(self) -> bool:
        """检查Unstructured是否可用"""
        try:
            from unstructured.partition.html import partition_html
            return True
        except ImportError:
            return False
    
    def _check_bs4(self) -> bool:
        """检查BeautifulSoup是否可用"""
        try:
            from bs4 import BeautifulSoup
            return True
        except ImportError:
            return False
    
    def supports(self, file_path: Union[str, Path]) -> bool:
        """检查是否支持该文件"""
        ext = Path(file_path).suffix.lower()
        return ext in ['.html', '.htm']
    
    def load(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        加载HTML文档
        
        Args:
            file_path: HTML文件路径
            
        Returns:
            包含文档内容的字典
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 优先使用Unstructured
        if self._unstructured_available:
            try:
                return self._load_with_unstructured(file_path)
            except Exception as e:
                pass
        
        # 使用BeautifulSoup
        if self._bs4_available:
            return self._load_with_bs4(file_path)
        
        # 直接读取
        return self._load_raw(file_path)
    
    def _load_with_unstructured(self, file_path: Path) -> Dict[str, Any]:
        """使用Unstructured加载HTML"""
        from unstructured.partition.html import partition_html
        
        elements = partition_html(filename=str(file_path))
        
        texts = []
        for element in elements:
            text = str(element)
            if text.strip():
                texts.append(text)
        
        content = '\n\n'.join(texts)
        
        metadata = self.extract_metadata(file_path)
        metadata['parser'] = 'unstructured_html'
        
        return {
            'content': content,
            'metadata': metadata,
            'pages': [],
        }
    
    def _load_with_bs4(self, file_path: Path) -> Dict[str, Any]:
        """使用BeautifulSoup加载HTML"""
        from bs4 import BeautifulSoup
        
        # 尝试多种编码
        encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
        soup = None
        used_encoding = None
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    soup = BeautifulSoup(f, 'html.parser')
                used_encoding = encoding
                break
            except UnicodeDecodeError:
                continue
        
        if soup is None:
            raise RuntimeError(f"无法解码HTML文件: {file_path}")
        
        # 移除script和style标签
        for script in soup(["script", "style"]):
            script.decompose()
        
        # 获取文本
        text = soup.get_text()
        
        # 清理空白
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        content = '\n'.join(chunk for chunk in chunks if chunk)
        
        # 提取标题
        title = ''
        if soup.title:
            title = soup.title.string
        elif soup.find('h1'):
            title = soup.find('h1').get_text()
        
        metadata = self.extract_metadata(file_path)
        metadata['parser'] = 'beautifulsoup'
        metadata['encoding'] = used_encoding
        if title:
            metadata['title'] = title.strip()
        
        return {
            'content': content,
            'metadata': metadata,
            'pages': [],
        }
    
    def _load_raw(self, file_path: Path) -> Dict[str, Any]:
        """直接读取HTML文件"""
        encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
        
        content = None
        used_encoding = None
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                used_encoding = encoding
                break
            except UnicodeDecodeError:
                continue
        
        if content is None:
            raise RuntimeError(f"无法解码HTML文件: {file_path}")
        
        metadata = self.extract_metadata(file_path)
        metadata['parser'] = 'raw_html'
        metadata['encoding'] = used_encoding
        
        return {
            'content': content,
            'metadata': metadata,
            'pages': [],
        }
