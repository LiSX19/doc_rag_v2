"""
Word文档加载器

支持.docx和.doc格式，Unstructured处理失败时使用pywin32（Windows）。
添加了重试机制处理COM调用失败问题。
"""

import os
import platform
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .base import BaseLoader


class WordLoader(BaseLoader):
    """Word加载器"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化Word加载器

        Args:
            config: 配置字典，包含：
                - loader.word.max_retries: pywin32最大重试次数（默认3）
                - loader.word.retry_delay: 重试间隔（秒，默认2）
        """
        super().__init__(config)

        self._unstructured_available = self._check_unstructured()
        self._pywin32_available = self._check_pywin32()
        self._python_docx_available = self._check_python_docx()

        # 重试配置
        word_config = self.config.get('loader', {}).get('word', {})
        self.max_retries = word_config.get('max_retries', 3)
        self.retry_delay = word_config.get('retry_delay', 2)

    def _check_unstructured(self) -> bool:
        """检查Unstructured是否可用"""
        try:
            from unstructured.partition.docx import partition_docx
            from unstructured.partition.doc import partition_doc
            return True
        except ImportError:
            return False

    def _check_pywin32(self) -> bool:
        """检查pywin32是否可用（仅Windows）"""
        if platform.system() != 'Windows':
            return False
        try:
            import win32com.client
            return True
        except ImportError:
            return False

    def _check_python_docx(self) -> bool:
        """检查python-docx是否可用"""
        try:
            import docx
            return True
        except ImportError:
            return False

    def supports(self, file_path: Union[str, Path]) -> bool:
        """检查是否支持该文件"""
        ext = Path(file_path).suffix.lower()
        return ext in ['.docx', '.doc', '.wps']

    def load(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        加载Word文档

        Args:
            file_path: Word文件路径

        Returns:
            包含文档内容的字典
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        ext = file_path.suffix.lower()

        # .docx文件优先使用Unstructured
        if ext == '.docx':
            if self._unstructured_available:
                try:
                    return self._load_with_unstructured_docx(file_path)
                except Exception as e:
                    pass

            # 降级到python-docx
            if self._python_docx_available:
                return self._load_with_python_docx(file_path)

        # .doc文件
        elif ext == '.doc':
            if self._unstructured_available:
                try:
                    return self._load_with_unstructured_doc(file_path)
                except Exception as e:
                    pass

            # Windows上使用pywin32（带重试）
            if self._pywin32_available:
                return self._load_with_pywin32_retry(file_path)

        # .wps文件（WPS格式，使用与.doc相同的处理流程）
        elif ext == '.wps':
            if self._unstructured_available:
                try:
                    # 尝试使用Unstructured的doc解析器处理wps
                    return self._load_with_unstructured_wps(file_path)
                except Exception as e:
                    pass

            # Windows上使用pywin32（带重试）
            if self._pywin32_available:
                return self._load_with_pywin32_retry(file_path, parser_name='wps')

        raise RuntimeError(f"无法解析Word文件: {file_path}")

    def _load_with_unstructured_docx(self, file_path: Path) -> Dict[str, Any]:
        """使用Unstructured加载.docx"""
        from unstructured.partition.docx import partition_docx

        elements = partition_docx(filename=str(file_path))

        texts = []
        for element in elements:
            text = str(element)
            if text.strip():
                texts.append(text)

        content = '\n\n'.join(texts)

        metadata = self.extract_metadata(file_path)
        metadata['parser'] = 'unstructured_docx'

        return {
            'content': content,
            'metadata': metadata,
            'pages': [],
        }

    def _load_with_unstructured_doc(self, file_path: Path) -> Dict[str, Any]:
        """使用Unstructured加载.doc"""
        from unstructured.partition.doc import partition_doc

        elements = partition_doc(filename=str(file_path))

        texts = []
        for element in elements:
            text = str(element)
            if text.strip():
                texts.append(text)

        content = '\n\n'.join(texts)

        metadata = self.extract_metadata(file_path)
        metadata['parser'] = 'unstructured_doc'

        return {
            'content': content,
            'metadata': metadata,
            'pages': [],
        }

    def _load_with_unstructured_wps(self, file_path: Path) -> Dict[str, Any]:
        """使用Unstructured加载.wps（尝试使用doc解析器）"""
        from unstructured.partition.doc import partition_doc

        # WPS格式与DOC类似，尝试使用doc解析器
        elements = partition_doc(filename=str(file_path))

        texts = []
        for element in elements:
            text = str(element)
            if text.strip():
                texts.append(text)

        content = '\n\n'.join(texts)

        metadata = self.extract_metadata(file_path)
        metadata['parser'] = 'unstructured_wps'

        return {
            'content': content,
            'metadata': metadata,
            'pages': [],
        }

    def _load_with_python_docx(self, file_path: Path) -> Dict[str, Any]:
        """使用python-docx加载.docx"""
        from docx import Document

        doc = Document(str(file_path))

        texts = []
        for para in doc.paragraphs:
            if para.text.strip():
                texts.append(para.text)

        content = '\n\n'.join(texts)

        metadata = self.extract_metadata(file_path)
        metadata['parser'] = 'python-docx'

        # 提取元数据
        try:
            metadata['author'] = doc.core_properties.author
        except:
            pass

        try:
            metadata['title'] = doc.core_properties.title
        except:
            pass

        return {
            'content': content,
            'metadata': metadata,
            'pages': [],
        }

    def _load_with_pywin32_retry(self, file_path: Path, parser_name: str = 'doc') -> Dict[str, Any]:
        """
        使用pywin32加载.doc/.wps（带重试机制）

        Args:
            file_path: .doc或.wps文件路径
            parser_name: 解析器名称标识（'doc'或'wps'）

        Returns:
            包含文档内容的字典
        """
        last_error = None

        for attempt in range(self.max_retries):
            try:
                return self._load_with_pywin32(file_path, parser_name)
            except Exception as e:
                last_error = e
                error_msg = str(e)

                # 检查是否是RPC错误
                if '-2147023170' in error_msg or '远程过程调用' in error_msg:
                    if attempt < self.max_retries - 1:
                        print(f"[WordLoader] pywin32调用失败，{self.retry_delay}秒后重试 ({attempt + 1}/{self.max_retries})...")
                        time.sleep(self.retry_delay)
                        continue

                # 其他错误直接抛出
                raise

        # 所有重试都失败了
        raise RuntimeError(f"pywin32加载失败（已重试{self.max_retries}次）: {last_error}")

    def _load_with_pywin32(self, file_path: Path, parser_name: str = 'doc') -> Dict[str, Any]:
        """使用pywin32加载.doc/.wps（Windows only）"""
        import win32com.client

        word = None
        doc = None

        try:
            word = win32com.client.Dispatch("Word.Application")
            word.Visible = False
            word.DisplayAlerts = False  # 禁用警告对话框

            # 打开文档
            doc = word.Documents.Open(
                str(file_path.absolute()),
                ReadOnly=True,
                AddToRecentFiles=False
            )

            # 提取文本
            content = doc.Content.Text

            # 提取元数据
            metadata = self.extract_metadata(file_path)
            metadata['parser'] = f'pywin32_{parser_name}'

            try:
                metadata['author'] = doc.BuiltInDocumentProperties("Author").Value
            except:
                pass

            try:
                metadata['title'] = doc.BuiltInDocumentProperties("Title").Value
            except:
                pass

            return {
                'content': content,
                'metadata': metadata,
                'pages': [],
            }

        finally:
            # 确保关闭文档和Word应用
            if doc:
                try:
                    doc.Close(SaveChanges=False)
                except:
                    pass

            if word:
                try:
                    word.Quit()
                except:
                    pass

            # 强制垃圾回收，释放COM对象
            import gc
            gc.collect()
