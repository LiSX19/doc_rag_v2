"""
文档加载器模块

提供多种文档格式的加载和解析功能。
"""

from .base import BaseLoader
from .loader_factory import LoaderFactory, get_loader, register_all_loaders

# 导出所有加载器
from .pdf_loader import PDFLoader
from .word_loader import WordLoader
from .excel_loader import ExcelLoader
from .ppt_loader import PPTLoader
from .text_loader import TextLoader
from .html_loader import HTMLLoader
from .caj_loader import CAJLoader
from .rtf_loader import RTFLoader
from .document_loader import DocumentLoader

__all__ = [
    "BaseLoader",
    "LoaderFactory",
    "get_loader",
    "register_all_loaders",
    "PDFLoader",
    "WordLoader",
    "ExcelLoader",
    "PPTLoader",
    "TextLoader",
    "HTMLLoader",
    "CAJLoader",
    "RTFLoader",
    "DocumentLoader",
]
