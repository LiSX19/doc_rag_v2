#!/usr/bin/env python3
"""
OCR处理器 - 独立子进程脚本

此脚本在OCR环境中运行，通过子进程被主环境调用。
用于处理需要OCR识别的PDF文件。
支持进度汇报和无超时限制。

使用方法:
    python ocr_processor.py <pdf_path> <output_json_path> [progress_fifo_path] [max_workers]
"""

import sys
import json
import os
import tempfile
import time
from pathlib import Path


def report_progress(progress_fifo_path: str, current: int, total: int, message: str = ""):
    """
    向主进程汇报进度

    Args:
        progress_fifo_path: 进度管道文件路径
        current: 当前进度
        total: 总进度
        message: 进度消息
    """
    if not progress_fifo_path or not os.path.exists(progress_fifo_path):
        return

    try:
        progress_data = {
            'current': current,
            'total': total,
            'percentage': round(current / total * 100, 1) if total > 0 else 0,
            'message': message,
            'timestamp': time.time(),
        }
        with open(progress_fifo_path, 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, ensure_ascii=False)
    except:
        pass  # 忽略进度汇报错误


def process_pdf_with_ocr(pdf_path: str, output_path: str, progress_fifo_path: str = None, max_workers: int = 2):
    """
    使用PaddleOCR处理PDF文件

    Args:
        pdf_path: PDF文件路径
        output_path: 输出JSON文件路径
        progress_fifo_path: 进度管道文件路径（可选）
        max_workers: 最大CPU核心使用数
    """
    try:
        # 限制CPU使用
        if max_workers > 0:
            try:
                import multiprocessing
                # 设置进程使用的CPU核心数
                os.environ['OMP_NUM_THREADS'] = str(max_workers)
                os.environ['MKL_NUM_THREADS'] = str(max_workers)
                # 对于PaddlePaddle
                os.environ['CPU_NUM'] = str(max_workers)
            except:
                pass

        from paddleocr import PaddleOCR
        import fitz  # PyMuPDF

        # 打开PDF
        doc = fitz.open(pdf_path)
        total_pages = len(doc)

        # 汇报开始
        report_progress(progress_fifo_path, 0, total_pages, "初始化OCR引擎...")

        # 初始化OCR - 使用更轻量的配置
        ocr = PaddleOCR(
            use_angle_cls=True,
            lang='ch',
            show_log=False,
            use_gpu=False,  # 确保使用CPU
            cpu_threads=max_workers,  # 限制CPU线程数
            enable_mkldnn=False,  # 禁用MKL-DNN以减少内存占用
        )

        texts = []
        pages = []

        # 创建临时目录
        temp_dir = tempfile.gettempdir()

        for page_num in range(total_pages):
            # 汇报进度
            report_progress(
                progress_fifo_path,
                page_num,
                total_pages,
                f"{page_num + 1}/{total_pages}"
            )

            page = doc[page_num]

            # 将页面转换为图片 (2x分辨率)
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))

            # 保存临时图片 (使用系统临时目录)
            temp_img = os.path.join(temp_dir, f"ocr_page_{page_num}_{os.getpid()}.png")
            pix.save(temp_img)

            try:
                # OCR识别
                result = ocr.ocr(temp_img, cls=True)

                # 提取文本
                page_texts = []
                if result and result[0]:
                    for line in result[0]:
                        if line:
                            text = line[1][0]
                            page_texts.append(text)

                page_content = '\n'.join(page_texts)
                texts.append(page_content)
                pages.append({
                    'page_num': page_num + 1,
                    'content': page_content
                })
            finally:
                # 清理临时文件
                if os.path.exists(temp_img):
                    os.remove(temp_img)

        doc.close()

        # 汇报完成
        report_progress(progress_fifo_path, total_pages, total_pages, "完成")

        # 构建结果
        result_data = {
            'success': True,
            'content': '\n\n'.join(texts),
            'pages': pages,
            'page_count': len(pages),
            'parser': 'paddleocr_subprocess',
            'error': None,
        }

    except Exception as e:
        # 汇报错误
        report_progress(progress_fifo_path, 0, 0, f"错误: {str(e)}")

        result_data = {
            'success': False,
            'content': '',
            'pages': [],
            'page_count': 0,
            'parser': 'paddleocr_subprocess',
            'error': str(e),
        }

    # 写入输出文件
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)

    return result_data['success']


def main():
    """主函数"""
    if len(sys.argv) < 3:
        print("Usage: python ocr_processor.py <pdf_path> <output_json_path> [progress_fifo_path] [max_workers]", file=sys.stderr)
        sys.exit(1)

    pdf_path = sys.argv[1]
    output_path = sys.argv[2]
    progress_fifo_path = sys.argv[3] if len(sys.argv) > 3 else None
    max_workers = int(sys.argv[4]) if len(sys.argv) > 4 else 2

    # 检查输入文件
    if not os.path.exists(pdf_path):
        result = {
            'success': False,
            'error': f'PDF文件不存在: {pdf_path}',
        }
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        sys.exit(1)

    # 处理PDF
    success = process_pdf_with_ocr(pdf_path, output_path, progress_fifo_path, max_workers)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
