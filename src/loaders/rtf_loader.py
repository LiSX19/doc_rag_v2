"""
RTF文件加载器

使用pywin32（Windows）处理RTF格式，支持重试机制和内存清理。
"""

import gc
import platform
import time
from pathlib import Path
from typing import Any, Dict, Optional, Union

from .base import BaseLoader


class RTFLoader(BaseLoader):
    """RTF加载器"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化RTF加载器

        Args:
            config: 配置字典，包含：
                - loader.rtf.max_retries: pywin32最大重试次数（默认3）
                - loader.rtf.retry_delay: 重试间隔（秒，默认2）
        """
        super().__init__(config)

        self._pywin32_available = self._check_pywin32()
        self._unstructured_available = self._check_unstructured()

        # 重试配置
        rtf_config = self.config.get('loader', {}).get('rtf', {})
        self.max_retries = rtf_config.get('max_retries', 3)
        self.retry_delay = rtf_config.get('retry_delay', 2)

    def _check_pywin32(self) -> bool:
        """检查pywin32是否可用（仅Windows）"""
        if platform.system() != 'Windows':
            return False
        try:
            import win32com.client
            return True
        except ImportError:
            return False

    def _check_unstructured(self) -> bool:
        """检查Unstructured是否可用"""
        try:
            from unstructured.partition.text import partition_text
            return True
        except ImportError:
            return False

    def supports(self, file_path: Union[str, Path]) -> bool:
        """检查是否支持该文件"""
        ext = Path(file_path).suffix.lower()
        return ext == '.rtf'

    def load(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        加载RTF文件

        Args:
            file_path: RTF文件路径

        Returns:
            包含文档内容的字典
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        # Windows上使用pywin32（带重试）
        if self._pywin32_available:
            try:
                return self._load_with_pywin32_retry(file_path)
            except Exception as e:
                # pywin32失败，尝试降级
                pass

        # 降级到Unstructured
        if self._unstructured_available:
            try:
                return self._load_with_unstructured(file_path)
            except Exception as e:
                pass

        # 最后尝试直接读取
        return self._load_raw(file_path)

    def _load_with_pywin32_retry(self, file_path: Path) -> Dict[str, Any]:
        """
        使用pywin32加载RTF（带重试机制）

        Args:
            file_path: RTF文件路径

        Returns:
            包含文档内容的字典
        """
        last_error = None

        for attempt in range(self.max_retries):
            try:
                return self._load_with_pywin32(file_path)
            except Exception as e:
                last_error = e
                error_msg = str(e)

                # 检查是否是RPC错误
                if '-2147023170' in error_msg or '远程过程调用' in error_msg:
                    if attempt < self.max_retries - 1:
                        print(f"[RTFLoader] pywin32调用失败，{self.retry_delay}秒后重试 ({attempt + 1}/{self.max_retries})...")
                        time.sleep(self.retry_delay)
                        continue

                # 其他错误直接抛出
                raise

        # 所有重试都失败了
        raise RuntimeError(f"pywin32加载RTF失败（已重试{self.max_retries}次）: {last_error}")

    def _load_with_pywin32(self, file_path: Path) -> Dict[str, Any]:
        """
        使用pywin32加载RTF（Windows only）

        使用Word应用程序打开RTF文件并提取文本。
        """
        import win32com.client

        word = None
        doc = None

        try:
            # 创建Word应用实例
            word = win32com.client.Dispatch("Word.Application")
            word.Visible = False
            word.DisplayAlerts = False  # 禁用警告对话框

            # 打开RTF文档
            doc = word.Documents.Open(
                str(file_path.absolute()),
                ReadOnly=True,
                AddToRecentFiles=False,
                Format=6  # 6 = wdOpenFormatAuto，自动识别格式
            )

            # 提取文本内容
            content = doc.Content.Text

            # 提取元数据
            metadata = self.extract_metadata(file_path)
            metadata['parser'] = 'pywin32_rtf'

            # 尝试提取作者
            try:
                metadata['author'] = doc.BuiltInDocumentProperties("Author").Value
            except:
                pass

            # 尝试提取标题
            try:
                metadata['title'] = doc.BuiltInDocumentProperties("Title").Value
            except:
                pass

            # 尝试提取页数
            try:
                metadata['page_count'] = doc.ComputeStatistics(2)  # 2 = wdStatisticPages
            except:
                pass

            return {
                'content': content,
                'metadata': metadata,
                'pages': [],
            }

        finally:
            # 确保关闭文档
            if doc:
                try:
                    doc.Close(SaveChanges=False)
                except:
                    pass

            # 确保退出Word应用
            if word:
                try:
                    word.Quit()
                except:
                    pass

            # 强制垃圾回收，释放COM对象
            gc.collect()

    def _load_with_unstructured(self, file_path: Path) -> Dict[str, Any]:
        """使用Unstructured加载RTF"""
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
        metadata['parser'] = 'unstructured_rtf'

        return {
            'content': content,
            'metadata': metadata,
            'pages': [],
        }

    def _load_raw(self, file_path: Path) -> Dict[str, Any]:
        """直接读取RTF文件"""
        # 尝试多种编码
        encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']

        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()

                metadata = self.extract_metadata(file_path)
                metadata['parser'] = 'raw_rtf'
                metadata['encoding'] = encoding

                return {
                    'content': content,
                    'metadata': metadata,
                    'pages': [],
                }
            except UnicodeDecodeError:
                continue

        raise RuntimeError(f"无法解码RTF文件: {file_path}")
