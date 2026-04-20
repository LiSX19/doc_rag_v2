"""
CAJ文档加载器

使用caj2pdf工具将CAJ转换为PDF后，使用PDFLoader解析。
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .base import BaseLoader


class CAJLoader(BaseLoader):
    """CAJ加载器 - 使用caj2pdf工具转换为PDF后，使用PDFLoader解析"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化CAJ加载器

        Args:
            config: 配置字典，包含：
                - caj2pdf_dir: caj2pdf工具目录路径
        """
        super().__init__(config)

        # caj2pdf工具目录（相对于src/loaders）
        default_caj2pdf_dir = Path(__file__).parent / "caj2pdf"
        self.caj2pdf_dir = Path(self.config.get('caj2pdf_dir', default_caj2pdf_dir))
        self.caj2pdf_script = self.caj2pdf_dir / "caj2pdf"

        self._caj2pdf_available = self._check_caj2pdf()

    def _check_caj2pdf(self) -> bool:
        """检查caj2pdf工具是否可用"""
        if not self.caj2pdf_dir.exists():
            return False
        if not self.caj2pdf_script.exists():
            return False

        # 尝试运行帮助命令
        try:
            result = subprocess.run(
                ["python", str(self.caj2pdf_script), "--help"],
                capture_output=True,
                timeout=5,
                cwd=str(self.caj2pdf_dir)
            )
            return result.returncode == 0
        except:
            return False

    def supports(self, file_path: Union[str, Path]) -> bool:
        """检查是否支持该文件"""
        return Path(file_path).suffix.lower() == '.caj'

    def load(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        加载CAJ文档

        流程：
        1. 使用caj2pdf将CAJ转换为PDF
        2. 使用PDFLoader加载PDF提取文本

        Args:
            file_path: CAJ文件路径

        Returns:
            包含文档内容的字典
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        if not self._caj2pdf_available:
            raise RuntimeError(
                f"caj2pdf工具不可用。请确保已克隆到: {self.caj2pdf_dir}\n"
                "克隆命令: git clone https://github.com/caj2pdf/caj2pdf.git"
            )

        # 创建临时PDF文件
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            pdf_path = tmp.name

        try:
            # 第一步：使用caj2pdf将CAJ转换为PDF
            self._convert_caj_to_pdf(file_path, pdf_path)

            # 第二步：使用PDFLoader加载PDF
            from .pdf_loader import PDFLoader
            pdf_loader = PDFLoader(self.config)
            result = pdf_loader.load(pdf_path)

            # 更新元数据
            result['metadata']['original_format'] = 'caj'
            result['metadata']['parser'] = f"caj2pdf+{result['metadata'].get('parser', 'unknown')}"

            return result

        except Exception as e:
            raise RuntimeError(f"CAJ文件解析失败: {e}")

        finally:
            # 清理临时PDF文件
            if os.path.exists(pdf_path):
                os.remove(pdf_path)

    def _convert_caj_to_pdf(self, caj_path: Path, pdf_path: str):
        """
        使用caj2pdf将CAJ转换为PDF

        Args:
            caj_path: CAJ文件路径
            pdf_path: 输出PDF路径
        """
        try:
            result = subprocess.run(
                [
                    "python",
                    str(self.caj2pdf_script),
                    "convert",
                    str(caj_path),
                    "-o", pdf_path
                ],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(self.caj2pdf_dir)
            )

            if result.returncode != 0:
                raise RuntimeError(f"CAJ转换失败: {result.stderr}")

            if not os.path.exists(pdf_path):
                raise RuntimeError("CAJ转换失败：未生成PDF文件")

        except subprocess.TimeoutExpired:
            raise RuntimeError("CAJ转换超时")
        except FileNotFoundError as e:
            raise RuntimeError(f"找不到caj2pdf工具: {e}")
