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
from ..utils.logger import get_logger

logger = get_logger(__name__)


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
        self._libreoffice_available = self._check_libreoffice()

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

    def _check_libreoffice(self) -> bool:
        """检查LibreOffice是否可用"""
        try:
            import subprocess
            # 检查LibreOffice是否安装
            import winreg
            try:
                # 尝试从注册表获取LibreOffice路径
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\LibreOffice\ LibreOffice 26\Installation") as key:
                    install_dir = winreg.QueryValueEx(key, "Path")[0]
                    soffice_path = Path(install_dir) / "program" / "soffice.exe"
                    if soffice_path.exists():
                        return True
            except Exception:
                pass
            
            # 检查默认路径
            default_paths = [
                r"C:\Program Files\LibreOffice\program\soffice.exe",
                r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"
            ]
            for path in default_paths:
                if Path(path).exists():
                    return True
            
            # 检查命令行
            result = subprocess.run(
                ['soffice', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError, TimeoutError):
            return False

    def supports(self, file_path: Union[str, Path]) -> bool:
        """检查是否支持该文件"""
        ext = Path(file_path).suffix.lower()
        return ext in ['.docx', '.doc', '.wps']

    def _is_fake_doc(self, file_path: Path) -> bool:
        """
        检测.doc文件是否是伪装的.docx文件

        Args:
            file_path: 文件路径

        Returns:
            True if the file is actually a .docx file with .doc extension
        """
        import zipfile
        try:
            with zipfile.ZipFile(str(file_path), 'r') as zf:
                # 检查是否包含docx特征文件
                if '[Content_Types].xml' in zf.namelist():
                    return True
            return False
        except Exception:
            # 如果打开失败，说明不是有效的zip/docx文件
            return False

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

        # .docx文件
        if ext == '.docx':
            # 直接使用python-docx，避免Unstructured的类型检查问题
            if self._python_docx_available:
                try:
                    return self._load_with_python_docx(file_path)
                except Exception as e:
                    logger.warning(f"python-docx解析.docx失败: {e}")

            # 如果python-docx失败，尝试使用zipfile备选方案
            try:
                return self._load_with_zipfile_fallback(file_path)
            except Exception as e:
                logger.warning(f"zipfile解析.docx失败: {e}")

        # .doc文件
        elif ext == '.doc':
            # 直接使用LibreOffice
            if self._libreoffice_available:
                return self._load_with_libreoffice(file_path)
            else:
                raise RuntimeError(f"LibreOffice不可用，无法解析.doc文件: {file_path}")

        # .wps文件（WPS格式，使用与.doc相同的处理流程）
        elif ext == '.wps':
            # 直接使用LibreOffice处理wps文件
            if self._libreoffice_available:
                try:
                    return self._load_with_libreoffice(file_path)
                except Exception as e:
                    logger.warning(f"LibreOffice解析.wps失败: {e}")
                    # 失败后尝试其他方法
                    pass

            # Windows上使用pywin32（带重试）
            if self._pywin32_available:
                return self._load_with_pywin32_retry(file_path, parser_name='wps')

        raise RuntimeError(f"无法解析Word文件: {file_path}")

    def _load_with_unstructured_docx(self, file_path: Path) -> Dict[str, Any]:
        """使用Unstructured加载.docx"""
        from unstructured.partition.docx import partition_docx

        # 获取语言配置
        languages = self.config.get('loader.unstructured.languages', ['chi_sim', 'eng'])

        elements = partition_docx(filename=str(file_path), languages=languages)

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

        # 获取语言配置
        languages = self.config.get('loader.unstructured.languages', ['chi_sim', 'eng'])

        elements = partition_doc(filename=str(file_path), languages=languages)

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

        # 获取语言配置
        languages = self.config.get('loader.unstructured.languages', ['chi_sim', 'eng'])

        # WPS格式与DOC类似，尝试使用doc解析器
        elements = partition_doc(filename=str(file_path), languages=languages)

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
        """使用python-docx加载.docx

        Args:
            file_path: 文件路径
        """
        import tempfile
        import shutil
        from docx import Document

        doc = None

        try:
            doc = Document(str(file_path))

            texts = []
            for para in doc.paragraphs:
                if para.text.strip():
                    texts.append(para.text)

            content = '\n\n'.join(texts)

            metadata = self.extract_metadata(file_path)
            metadata['parser'] = 'python-docx'

            try:
                metadata['author'] = doc.core_properties.author
            except Exception:
                pass

            try:
                metadata['title'] = doc.core_properties.title
            except Exception:
                pass

            return {
                'content': content,
                'metadata': metadata,
                'pages': [],
            }

        finally:
            pass

    def _load_with_zipfile_fallback(self, file_path: Path) -> Dict[str, Any]:
        """备选方案：使用zipfile和xml直接解析docx内容"""
        import zipfile
        import xml.etree.ElementTree as ET

        logger.info("尝试使用zipfile备选方案解析文档")

        texts = []
        with zipfile.ZipFile(str(file_path), 'r') as zf:
            # 尝试读取document.xml
            try:
                with zf.open('word/document.xml') as doc_xml:
                    tree = ET.parse(doc_xml)
                    root = tree.getroot()

                    # 命名空间
                    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

                    # 提取所有文本
                    for elem in root.iter():
                        if elem.text and elem.text.strip():
                            texts.append(elem.text.strip())
                        if elem.tail and elem.tail.strip():
                            texts.append(elem.tail.strip())
            except KeyError:
                logger.warning("无法找到word/document.xml")

        content = '\n\n'.join(texts)

        metadata = self.extract_metadata(file_path)
        metadata['parser'] = 'zipfile_fallback'

        return {
            'content': content,
            'metadata': metadata,
            'pages': [],
        }

    def _load_with_libreoffice(self, file_path: Path) -> Dict[str, Any]:
        """使用LibreOffice加载.doc文件（跨平台）"""
        import subprocess
        import tempfile
        import shutil
        
        temp_dir = None
        temp_txt = None
        
        try:
            # 找到LibreOffice可执行文件
            import winreg
            soffice_path = None
            
            # 尝试从注册表获取
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\LibreOffice\ LibreOffice 26\Installation") as key:
                    install_dir = winreg.QueryValueEx(key, "Path")[0]
                    soffice_path = Path(install_dir) / "program" / "soffice.exe"
            except Exception:
                pass
            
            # 检查默认路径
            if not soffice_path or not soffice_path.exists():
                default_paths = [
                    r"C:\Program Files\LibreOffice\program\soffice.exe",
                    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"
                ]
                for path in default_paths:
                    if Path(path).exists():
                        soffice_path = Path(path)
                        break
            
            if not soffice_path or not soffice_path.exists():
                # 尝试命令行
                try:
                    result = subprocess.run(
                        ['where', 'soffice'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        paths = result.stdout.strip().split('\n')
                        for path in paths:
                            p = Path(path)
                            if p.exists():
                                soffice_path = p
                                break
                except Exception:
                    pass
            
            if not soffice_path or not soffice_path.exists():
                raise RuntimeError(f"找不到LibreOffice可执行文件")
            
            # 创建临时目录
            temp_dir = Path(tempfile.mkdtemp())
            temp_txt = temp_dir / f"{file_path.stem}.txt"
            
            # 使用LibreOffice将.doc转换为.txt
            logger.info(f"使用LibreOffice将 {file_path.name} 转换为 .txt 格式")
            
            if platform.system() == 'Windows':
                # 使用直接命令（不通过PowerShell）
                cmd = [
                    str(soffice_path),
                    '--headless',
                    '--convert-to', 'txt',
                    '--outdir', str(temp_dir),
                    str(file_path)
                ]
                logger.info(f"执行命令: {' '.join(cmd)}")
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)
                )
            else:
                result = subprocess.run(
                    [
                        str(soffice_path),
                        '--headless',
                        '--convert-to', 'txt',
                        '--outdir', str(temp_dir),
                        str(file_path)
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30
                )

            if result.returncode != 0:
                raise RuntimeError(f"LibreOffice转换失败: {result.stderr}")

            # 检查转换是否成功
            if not temp_txt.exists():
                # 尝试查找生成的文件（可能有不同的命名）
                txt_files = list(temp_dir.glob('*.txt'))
                logger.info(f"在临时目录 {temp_dir} 中找到 {len(txt_files)} 个txt文件: {txt_files}")
                if not txt_files:
                    # 检查当前目录
                    current_dir_txt = list(Path.cwd().glob('*.txt'))
                    logger.info(f"在当前目录中找到 {len(current_dir_txt)} 个txt文件: {current_dir_txt}")
                    # 检查文件目录
                    file_dir_txt = list(file_path.parent.glob('*.txt'))
                    logger.info(f"在文件目录中找到 {len(file_dir_txt)} 个txt文件: {file_dir_txt}")
                    raise RuntimeError("LibreOffice转换后未找到生成的.txt文件")
                temp_txt = txt_files[0]
                logger.info(f"使用找到的txt文件: {temp_txt}")

            # 直接读取转换后的.txt文件内容
            # LibreOffice在中文Windows上可能输出GBK/GB2312编码，尝试多种编码
            content = self._read_text_with_encoding_fallback(temp_txt)

            # 提取元数据
            metadata = self.extract_metadata(file_path)
            metadata['parser'] = 'libreoffice_txt'

            return {
                'content': content,
                'metadata': metadata,
                'pages': [],
            }

        finally:
            # 清理临时文件
            if temp_dir and temp_dir.exists():
                try:
                    shutil.rmtree(temp_dir)
                    logger.info(f"清理临时目录: {temp_dir}")
                except Exception as e:
                    logger.warning(f"清理临时目录失败: {e}")

    def _read_text_with_encoding_fallback(self, file_path: Path) -> str:
        """尝试多种编码读取文本文件

        Args:
            file_path: 文件路径

        Returns:
            文件内容（解码成功时）
        """
        encodings = ['utf-8', 'gbk', 'gb2312', 'gb18030', 'latin-1']

        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding, errors='strict') as f:
                    content = f.read()
                logger.debug(f"成功使用 {encoding} 编码读取文件")
                return content
            except (UnicodeDecodeError, LookupError):
                continue

        logger.warning(f"所有编码尝试失败，使用 utf-8 + errors='ignore' 读取")
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()

    def _load_with_pywin32(self, file_path: Path, parser_name: str = 'doc') -> Dict[str, Any]:
        """使用pywin32加载.doc/.wps（Windows only）"""
        import win32com.client
        import pythoncom

        word = None
        doc = None

        # 初始化 COM（多线程/子进程必需）
        pythoncom.CoInitialize()

        try:
            # WPS 12.1 抢先版用 KWPS.Application，放第一位
            com_prog_ids = [
                "KWPS.Application",   # WPS 新版/抢先版
                "WPS.Application",    # WPS 旧版/正式版
                "Word.Application",   # Microsoft Word
            ]

            for prog_id in com_prog_ids:
                try:
                    word = win32com.client.Dispatch(prog_id)
                    logger.info(f"成功启动 {prog_id}")
                    break
                except Exception as e:
                    logger.warning(f"尝试 {prog_id} 失败: {e}")
                    word = None

            if not word:
                raise RuntimeError("无法启动任何Word/WPS组件")

            # WPS 不支持 Visible 属性，直接跳过不设置
            # word.Visible = False  # 注释掉或删除

            # DisplayAlerts 可尝试设置，失败则忽略
            try:
                word.DisplayAlerts = False
            except Exception as e:
                logger.warning(f"设置DisplayAlerts属性失败: {e}")

            # 打开文档
            try:
                doc = word.Documents.Open(
                    str(file_path.absolute()),
                    ReadOnly=True,
                                       AddToRecentFiles=False
                )
            except Exception as e:
                logger.warning(f"标准打开方式失败: {e}")
                # 简化打开方式
                doc = word.Documents.Open(str(file_path.absolute()))

            # 提取文本
            content = doc.Content.Text

            # 提取元数据
            metadata = self.extract_metadata(file_path)
            metadata['parser'] = f'pywin32_{parser_name}'

            # 尝试提取属性
            try:
                metadata['author'] = doc.BuiltInDocumentProperties("Author").Value
            except Exception:
                pass

            try:
                metadata['title'] = doc.BuiltInDocumentProperties("Title").Value
            except Exception:
                pass

            return {
                'content': content,
                'metadata': metadata,
                'pages': [],
            }

        finally:
            # 关闭文档
            if doc:
                try:
                    doc.Close(SaveChanges=False)
                except Exception as e:
                    logger.warning(f"关闭文档失败: {e}")

            # 退出应用
            if word:
                try:
                    word.Quit()
                except Exception as e:
                    logger.warning(f"退出应用失败: {e}")

            # 强制垃圾回收 + 释放 COM
            import gc
            gc.collect()
            pythoncom.CoUninitialize()

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
            # 尝试不同的COM组件
            com_prog_ids = [
                "Word.Application",  # Microsoft Word
                "KWPS.Application",  # WPS Word
                "WPS.Application"     # 另一种WPS格式
            ]

            for prog_id in com_prog_ids:
                try:
                    word = win32com.client.Dispatch(prog_id)
                    logger.info(f"成功启动 {prog_id}")
                    break
                except Exception as e:
                    logger.warning(f"尝试 {prog_id} 失败: {e}")
                    word = None

            if not word:
                raise RuntimeError("无法启动任何Word/WPS组件")

            # 尝试设置属性（WPS可能不支持某些属性）
            try:
                word.Visible = False
            except Exception as e:
                logger.warning(f"设置Visible属性失败: {e}")

            try:
                word.DisplayAlerts = False
            except Exception as e:
                logger.warning(f"设置DisplayAlerts属性失败: {e}")

            # 尝试打开文档
            try:
                # 尝试不同的打开方式
                try:
                    doc = word.Documents.Open(
                        str(file_path.absolute()),
                        ReadOnly=True,
                        AddToRecentFiles=False
                    )
                except Exception as e:
                    logger.warning(f"标准打开方式失败: {e}")
                    # 尝试简化的打开方式
                    doc = word.Documents.Open(str(file_path.absolute()))
            except Exception as e:
                raise RuntimeError(f"无法打开文档: {e}")

            # 提取文本
            try:
                content = doc.Content.Text
            except Exception as e:
                raise RuntimeError(f"无法提取文本: {e}")

            # 提取元数据
            metadata = self.extract_metadata(file_path)
            metadata['parser'] = f'pywin32_{parser_name}'

            # 尝试提取属性（可能不支持）
            try:
                metadata['author'] = doc.BuiltInDocumentProperties("Author").Value
            except Exception:
                pass

            try:
                metadata['title'] = doc.BuiltInDocumentProperties("Title").Value
            except Exception:
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
                except Exception as e:
                    logger.warning(f"关闭文档失败: {e}")

            if word:
                try:
                    word.Quit()
                except Exception as e:
                    logger.warning(f"退出应用失败: {e}")

            # 强制垃圾回收，释放COM对象
            import gc
            gc.collect()
