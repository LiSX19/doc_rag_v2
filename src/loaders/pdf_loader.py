"""
PDF文档加载器

使用Unstructured进行PDF解析，失败时通过子进程调用OCR环境进行OCR识别。
支持无超时限制和进度监控。
"""

import os
import sys
import json
import subprocess
import tempfile
import time
import threading
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable

from .base import BaseLoader
from ..utils.logger import get_logger

# 过滤PDF处理相关的非关键警告
warnings.filterwarnings('ignore', message='.*stroke color.*')
warnings.filterwarnings('ignore', message='.*non-stroke color.*')

logger = get_logger(__name__)


class PDFLoader(BaseLoader):
    """PDF加载器"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化PDF加载器

        Args:
            config: 配置字典，包含：
                - ocr.enabled: 是否启用OCR降级
                - ocr.conda_env: OCR环境名称 (默认: OCR)
                - ocr.conda_path: conda可执行文件路径
                - ocr.progress_callback: 进度回调函数 (current, total, message)
        """
        super().__init__(config)

        ocr_config = self.config.get('ocr', {})
        self.ocr_enabled = ocr_config.get('enabled', True)
        self.ocr_conda_env = ocr_config.get('conda_env', 'OCR')
        
        # 获取conda路径，如果配置中未设置或为空，则自动查找
        conda_path_config = ocr_config.get('conda_path', None)
        if conda_path_config:
            self.ocr_conda_path = conda_path_config
        else:
            self.ocr_conda_path = self._find_conda()
            
        self.ocr_progress_callback = ocr_config.get('progress_callback', None)

        self._unstructured_available = self._check_unstructured()

    def _find_conda(self) -> str:
        """查找conda可执行文件路径"""
        # 常见conda路径（Windows）
        possible_paths = [
            r"C:\ProgramData\miniconda3\Scripts\conda.exe",
            r"C:\ProgramData\anaconda3\Scripts\conda.exe",
            os.path.expandvars(r"C:\Users\%USERNAME%\miniconda3\Scripts\conda.exe"),
            os.path.expandvars(r"C:\Users\%USERNAME%\anaconda3\Scripts\conda.exe"),
            os.path.expandvars(r"%USERPROFILE%\miniconda3\Scripts\conda.exe"),
            os.path.expandvars(r"%USERPROFILE%\anaconda3\Scripts\conda.exe"),
            os.path.expanduser(r"~\miniconda3\Scripts\conda.exe"),
            os.path.expanduser(r"~\anaconda3\Scripts\conda.exe"),
            "/opt/miniconda3/bin/conda",
            "/opt/anaconda3/bin/conda",
            "~/miniconda3/bin/conda",
            "~/anaconda3/bin/conda",
        ]

        for path in possible_paths:
            expanded_path = os.path.expandvars(os.path.expanduser(path))
            if os.path.exists(expanded_path):
                logger.info(f"找到conda: {expanded_path}")
                return expanded_path

        # 尝试从PATH中查找（Windows）
        if sys.platform == 'win32':
            try:
                result = subprocess.run(
                    ["where", "conda"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                conda_path = result.stdout.strip().split('\n')[0].strip()
                if conda_path:
                    logger.info(f"从PATH找到conda: {conda_path}")
                    return conda_path
            except Exception as e:
                logger.warning(f"从PATH查找conda失败: {e}")

        # 尝试从PATH中查找（Linux/Mac）
        try:
            result = subprocess.run(
                ["which", "conda"],
                capture_output=True,
                text=True,
                check=True,
            )
            conda_path = result.stdout.strip().split('\n')[0].strip()
            if conda_path:
                logger.info(f"从PATH找到conda: {conda_path}")
                return conda_path
        except Exception as e:
            logger.warning(f"从PATH查找conda失败: {e}")

        # 默认返回conda（希望它在PATH中）
        logger.warning("未找到conda可执行文件，使用默认'conda'命令")
        return "conda"

    def _check_unstructured(self) -> bool:
        """检查Unstructured是否可用"""
        try:
            from unstructured.partition.pdf import partition_pdf
            return True
        except ImportError:
            return False

    def supports(self, file_path: Union[str, Path]) -> bool:
        """检查是否支持该文件"""
        return Path(file_path).suffix.lower() == '.pdf'

    def load(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        加载PDF文档

        Args:
            file_path: PDF文件路径

        Returns:
            包含文档内容的字典
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        # 尝试使用Unstructured解析
        if self._unstructured_available:
            try:
                return self._load_with_unstructured(file_path)
            except Exception as e:
                if not self.ocr_enabled:
                    raise RuntimeError(f"Unstructured解析失败且OCR未启用: {e}")

        # 降级到OCR（通过子进程调用OCR环境）
        if self.ocr_enabled:
            return self._load_with_ocr_subprocess(file_path)

        raise RuntimeError("无法解析PDF文件：Unstructured和OCR都不可用")

    def _load_with_unstructured(self, file_path: Path) -> Dict[str, Any]:
        """使用Unstructured加载PDF"""
        from unstructured.partition.pdf import partition_pdf

        # 获取语言配置，默认中文和英文
        languages = self.config.get('loader.unstructured.languages', ['chi_sim', 'eng'])

        # 首先尝试fast模式（纯文本，不需要OCR）
        try:
            elements = partition_pdf(
                filename=str(file_path),
                strategy="fast",
                languages=languages,
            )
        except Exception as e:
            # fast模式失败，尝试hi_res模式
            elements = partition_pdf(
                filename=str(file_path),
                strategy="hi_res",
                extract_images_in_pdf=False,
                infer_table_structure=True,
                languages=languages,
            )

        # 提取文本
        texts = []
        pages = []
        current_page = 1
        page_texts = []

        for element in elements:
            text = str(element)
            if text.strip():
                texts.append(text)

                # 尝试获取页码
                page_number = getattr(element.metadata, 'page_number', current_page)
                if page_number != current_page:
                    if page_texts:
                        pages.append({
                            'page_num': current_page,
                            'content': '\n'.join(page_texts)
                        })
                    page_texts = []
                    current_page = page_number

                page_texts.append(text)

        # 添加最后一页
        if page_texts:
            pages.append({
                'page_num': current_page,
                'content': '\n'.join(page_texts)
            })

        content = '\n\n'.join(texts)

        # 如果内容为空，可能需要OCR
        if not content.strip() and self.ocr_enabled:
            raise RuntimeError("PDF内容为空，可能是扫描版PDF，需要OCR")

        # 提取元数据
        metadata = self.extract_metadata(file_path)
        metadata['page_count'] = len(pages)
        metadata['parser'] = 'unstructured'

        return {
            'content': content,
            'metadata': metadata,
            'pages': pages,
        }

    def _monitor_progress(self, progress_file: str, stop_event: threading.Event, total_pages: int = 0):
        """
        监控OCR进度，使用进度条显示

        Args:
            progress_file: 进度文件路径
            stop_event: 停止事件
            total_pages: 总页数
        """
        last_progress = None
        file_name = getattr(self, '_current_ocr_file', 'Unknown')

        while not stop_event.is_set():
            try:
                if os.path.exists(progress_file):
                    with open(progress_file, 'r', encoding='utf-8') as f:
                        progress_data = json.load(f)

                    # 避免重复汇报相同的进度
                    if progress_data != last_progress:
                        last_progress = progress_data

                        current = progress_data.get('current', 0)
                        total = progress_data.get('total', total_pages)
                        percentage = progress_data.get('percentage', 0)
                        message = progress_data.get('message', '')

                        # 调用回调函数
                        if self.ocr_progress_callback:
                            self.ocr_progress_callback(current, total, message)

                        # 记录进度到日志（避免干扰主程序进度条）
                        if total > 0 and current % 5 == 0:  # 每5%记录一次，避免日志过多
                            logger.debug(f"[OCR进度] {percentage:.1f}% | {message} | {file_name}")

            except:
                pass

            time.sleep(0.5)  # 每0.5秒检查一次

    def _load_with_ocr_subprocess(self, file_path: Path) -> Dict[str, Any]:
        """
        通过子进程调用OCR环境进行OCR识别（无超时限制，支持进度监控）

        Args:
            file_path: PDF文件路径

        Returns:
            包含文档内容的字典
        """
        # 记录当前处理的文件名
        self._current_ocr_file = file_path.name
        
        # 创建临时输出文件
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.json',
            delete=False,
            encoding='utf-8'
        ) as tmp:
            output_path = tmp.name

        # 创建进度监控文件
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.progress',
            delete=False,
            encoding='utf-8'
        ) as tmp:
            progress_path = tmp.name

        process = None
        monitor_thread = None
        stop_event = threading.Event()

        try:
            # 获取ocr_processor.py路径
            processor_path = Path(__file__).parent / "ocr_processor.py"
            
            # 获取CPU限制配置
            performance_config = self.config.get('performance', {})
            max_workers = performance_config.get('max_workers', 2)

            # 构建conda run命令
            conda_path = str(self.ocr_conda_path)
            
            # 启动进度监控线程
            monitor_thread = threading.Thread(
                target=self._monitor_progress,
                args=(progress_path, stop_event)
            )
            monitor_thread.daemon = True
            monitor_thread.start()

            # 构建命令 - 直接使用OCR环境的Python解释器，避免conda run的输出干扰
            if sys.platform == 'win32':
                # Windows: 直接使用conda envs目录下的python.exe
                # 从conda路径推导环境路径
                if conda_path and conda_path != "conda":
                    # conda.exe 在 Scripts 目录下，环境在 envs 目录下
                    conda_base = os.path.dirname(os.path.dirname(conda_path))
                    ocr_python = os.path.join(conda_base, "envs", self.ocr_conda_env, "python.exe")
                else:
                    # 使用默认路径
                    ocr_python = f"C:\\ProgramData\\miniconda3\\envs\\{self.ocr_conda_env}\\python.exe"
                
                # 检查Python解释器是否存在
                if not os.path.exists(ocr_python):
                    logger.warning(f"未找到OCR环境Python: {ocr_python}，尝试使用conda run")
                    # 回退到conda run
                    cmd = [
                        conda_path if conda_path else "conda", "run",
                        "-n", str(self.ocr_conda_env),
                        "python",
                        str(processor_path),
                        str(file_path),
                        str(output_path),
                        str(progress_path),
                        str(max_workers),
                    ]
                    use_shell = False
                else:
                    # 使用直接路径
                    cmd = [
                        ocr_python,
                        str(processor_path),
                        str(file_path),
                        str(output_path),
                        str(progress_path),
                        str(max_workers),
                    ]
                    use_shell = False
            else:
                # Linux/Mac: 使用conda run
                cmd = [
                    conda_path if conda_path else "conda", "run",
                    "-n", str(self.ocr_conda_env),
                    "python",
                    str(processor_path),
                    str(file_path),
                    str(output_path),
                    str(progress_path),
                    str(max_workers),
                ]
                use_shell = False
            
            logger.info(f"OCR命令: {cmd}")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=use_shell,
            )

            # 等待子进程完成
            stdout, stderr = process.communicate()

            # 停止进度监控
            stop_event.set()
            if monitor_thread:
                monitor_thread.join(timeout=2)

            # 检查子进程返回码
            if process.returncode != 0:
                logger.error(f"OCR子进程返回错误码: {process.returncode}")
                logger.error(f"OCR stderr: {stderr}")
                logger.error(f"OCR stdout: {stdout}")
                raise RuntimeError(f"OCR子进程执行失败: {stderr}")

            # 检查输出文件是否存在
            if not os.path.exists(output_path):
                logger.error(f"OCR输出文件不存在: {output_path}")
                logger.error(f"OCR stderr: {stderr}")
                logger.error(f"OCR stdout: {stdout}")
                raise RuntimeError("OCR输出文件未生成")

            # 读取结果
            try:
                with open(output_path, 'r', encoding='utf-8') as f:
                    ocr_result = json.load(f)
            except json.JSONDecodeError as e:
                logger.error(f"OCR输出JSON解析失败: {e}")
                logger.error(f"输出文件内容: {open(output_path, 'r', encoding='utf-8').read()}")
                logger.error(f"OCR stderr: {stderr}")
                logger.error(f"OCR stdout: {stdout}")
                raise

            # 检查OCR是否成功
            if not ocr_result.get('success', False):
                error = ocr_result.get('error', '未知错误')
                raise RuntimeError(f"OCR识别失败: {error}")

            # 构建返回结果
            metadata = self.extract_metadata(file_path)
            metadata['page_count'] = ocr_result.get('page_count', 0)
            metadata['parser'] = ocr_result.get('parser', 'paddleocr_subprocess')

            return {
                'content': ocr_result['content'],
                'metadata': metadata,
                'pages': ocr_result.get('pages', []),
            }

        except Exception as e:
            # 确保停止监控线程
            stop_event.set()
            if monitor_thread:
                monitor_thread.join(timeout=2)

            # 如果进程还在运行，终止它
            if process and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except:
                    process.kill()

            raise RuntimeError(f"OCR处理异常: {e}")

        finally:
            # 清理临时文件
            for path in [output_path, progress_path]:
                if os.path.exists(path):
                    os.remove(path)
