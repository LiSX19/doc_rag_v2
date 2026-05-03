#!/usr/bin/env python3
"""
Unstructured库可用性测试脚本

测试unstructured对各种文档格式的解析能力。
运行方式: python tests/test_unstructured.py
"""

import sys
import os
from pathlib import Path

def test_unstructured_import():
    """测试unstructured库是否可导入"""
    print("=" * 60)
    print("测试1: 检查unstructured库是否可导入")
    print("=" * 60)

    try:
        import unstructured
        print(f"✓ unstructured版本: {unstructured.__version__}")
        return True
    except ImportError as e:
        print(f"✗ 无法导入unstructured: {e}")
        return False

def test_unstructured_modules():
    """测试unstructured各个模块是否可用"""
    print("\n" + "=" * 60)
    print("测试2: 检查unstructured各模块可用性")
    print("=" * 60)

    modules = {
        'partition.pdf': 'PDF文档',
        'partition.docx': 'Word文档(.docx)',
        'partition.doc': 'Word文档(.doc)',
        'partition.pptx': 'PowerPoint(.pptx)',
        'partition.ppt': 'PowerPoint(.ppt)',
        'partition.xlsx': 'Excel(.xlsx)',
        'partition.xls': 'Excel(.xls)',
        'partition.text': '文本文件',
        'partition.md': 'Markdown文件',
        'partition.html': 'HTML文件',
    }

    results = {}
    for module_name, description in modules.items():
        try:
            module = __import__(f'unstructured.{module_name}', fromlist=[''])
            print(f"✓ {description}: 可用")
            results[module_name] = True
        except ImportError as e:
            print(f"✗ {description}: 不可用 - {e}")
            results[module_name] = False

    return results

def test_pdf_parsing():
    """测试PDF解析功能"""
    print("\n" + "=" * 60)
    print("测试3: 测试PDF解析功能")
    print("=" * 60)

    try:
        from unstructured.partition.pdf import partition_pdf

        sample_pdf = Path(__file__).parent / "data" / "sample.pdf"
        if not sample_pdf.exists():
            sample_pdf = Path(__file__).parent.parent / "data" / "sample.pdf"

        if not sample_pdf.exists():
            print("⚠ 未找到示例PDF文件，跳过实际解析测试")
            print("  请确保data/sample.pdf存在，或手动测试:")
            print("  python -c \"from unstructured.partition.pdf import partition_pdf;")
            print("    elements = partition_pdf(filename='your_file.pdf')\"")
            return None

        print(f"正在解析: {sample_pdf}")
        elements = partition_pdf(filename=str(sample_pdf), strategy="fast")
        print(f"✓ PDF解析成功，共{len(elements)}个元素")

        for i, elem in enumerate(elements[:5]):
            print(f"  元素{i+1}: {str(elem)[:80]}...")

        return True

    except ImportError as e:
        print(f"✗ PDF模块不可用: {e}")
        return False
    except Exception as e:
        print(f"✗ PDF解析失败: {e}")
        return False

def test_docx_parsing():
    """测试Word文档解析功能"""
    print("\n" + "=" * 60)
    print("测试4: 测试Word文档(.docx)解析功能")
    print("=" * 60)

    try:
        from unstructured.partition.docx import partition_docx

        sample_docx = Path(__file__).parent / "data" / "sample.docx"
        if not sample_docx.exists():
            sample_docx = Path(__file__).parent.parent / "data" / "sample.docx"

        if not sample_docx.exists():
            print("⚠ 未找到示例docx文件，跳过实际解析测试")
            return None

        print(f"正在解析: {sample_docx}")
        elements = partition_docx(filename=str(sample_docx))
        print(f"✓ docx解析成功，共{len(elements)}个元素")

        for i, elem in enumerate(elements[:5]):
            print(f"  元素{i+1}: {str(elem)[:80]}...")

        return True

    except ImportError as e:
        print(f"✗ docx模块不可用: {e}")
        return False
    except Exception as e:
        print(f"✗ docx解析失败: {e}")
        return False

def test_pptx_parsing():
    """测试PowerPoint解析功能"""
    print("\n" + "=" * 60)
    print("测试5: 测试PowerPoint(.pptx)解析功能")
    print("=" * 60)

    try:
        from unstructured.partition.pptx import partition_pptx

        sample_pptx = Path(__file__).parent / "data" / "sample.pptx"
        if not sample_pptx.exists():
            sample_pptx = Path(__file__).parent.parent / "data" / "sample.pptx"

        if not sample_pptx.exists():
            print("⚠ 未找到示例pptx文件，跳过实际解析测试")
            return None

        print(f"正在解析: {sample_pptx}")
        elements = partition_pptx(filename=str(sample_pptx))
        print(f"✓ pptx解析成功，共{len(elements)}个元素")

        for i, elem in enumerate(elements[:5]):
            print(f"  元素{i+1}: {str(elem)[:80]}...")

        return True

    except ImportError as e:
        print(f"✗ pptx模块不可用: {e}")
        return False
    except Exception as e:
        print(f"✗ pptx解析失败: {e}")
        return False

def test_xlsx_parsing():
    """测试Excel解析功能"""
    print("\n" + "=" * 60)
    print("测试6: 测试Excel(.xlsx)解析功能")
    print("=" * 60)

    try:
        from unstructured.partition.xlsx import partition_xlsx

        sample_xlsx = Path(__file__).parent / "data" / "sample.xlsx"
        if not sample_xlsx.exists():
            sample_xlsx = Path(__file__).parent.parent / "data" / "sample.xlsx"

        if not sample_xlsx.exists():
            print("⚠ 未找到示例xlsx文件，跳过实际解析测试")
            return None

        print(f"正在解析: {sample_xlsx}")
        elements = partition_xlsx(filename=str(sample_xlsx))
        print(f"✓ xlsx解析成功，共{len(elements)}个元素")

        for i, elem in enumerate(elements[:5]):
            print(f"  元素{i+1}: {str(elem)[:80]}...")

        return True

    except ImportError as e:
        print(f"✗ xlsx模块不可用: {e}")
        return False
    except Exception as e:
        print(f"✗ xlsx解析失败: {e}")
        return False

def test_text_parsing():
    """测试文本文件解析功能"""
    print("\n" + "=" * 60)
    print("测试7: 测试文本文件解析功能")
    print("=" * 60)

    try:
        from unstructured.partition.text import partition_text

        sample_txt = Path(__file__).parent / "data" / "sample.txt"
        if not sample_txt.exists():
            sample_txt = Path(__file__).parent.parent / "data" / "sample.txt"

        if not sample_txt.exists():
            print("⚠ 未找到示例txt文件，跳过实际解析测试")
            return None

        print(f"正在解析: {sample_txt}")
        elements = partition_text(filename=str(sample_txt))
        print(f"✓ txt解析成功，共{len(elements)}个元素")

        for i, elem in enumerate(elements[:5]):
            print(f"  元素{i+1}: {str(elem)[:80]}...")

        return True

    except ImportError as e:
        print(f"✗ text模块不可用: {e}")
        return False
    except Exception as e:
        print(f"✗ txt解析失败: {e}")
        return False

def test_md_parsing():
    """测试Markdown解析功能"""
    print("\n" + "=" * 60)
    print("测试8: 测试Markdown解析功能")
    print("=" * 60)

    try:
        from unstructured.partition.md import partition_md

        sample_md = Path(__file__).parent / "data" / "sample.md"
        if not sample_md.exists():
            sample_md = Path(__file__).parent.parent / "data" / "sample.md"

        if not sample_md.exists():
            print("⚠ 未找到示例md文件，跳过实际解析测试")
            return None

        print(f"正在解析: {sample_md}")
        elements = partition_md(filename=str(sample_md))
        print(f"✓ md解析成功，共{len(elements)}个元素")

        for i, elem in enumerate(elements[:5]):
            print(f"  元素{i+1}: {str(elem)[:80]}...")

        return True

    except ImportError as e:
        print(f"✗ md模块不可用: {e}")
        return False
    except Exception as e:
        print(f"✗ md解析失败: {e}")
        return False

def test_inference_model():
    """测试unstructured-inference模型是否可用"""
    print("\n" + "=" * 60)
    print("测试9: 检查unstructured-inference模型")
    print("=" * 60)

    try:
        from unstructured_inference import __version__
        print(f"✓ unstructured-inference版本: {__version__}")
    except ImportError as e:
        print(f"⚠ unstructured-inference未安装: {e}")
        print("  这可能影响hi_res策略的PDF解析")

    try:
        import huggingface_hub
        print(f"✓ huggingface_hub可用")
    except ImportError:
        print(f"⚠ huggingface_hub未安装，可能无法自动下载模型")

def print_summary():
    """打印测试总结"""
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print("""
如果某些模块不可用，请尝试以下操作:

1. 升级unstructured:
   pip install -U unstructured[all-docs]

2. 安装特定模块:
   pip install unstructured[inference]  # PDF/图像支持

3. 如果是Windows系统且office文档解析失败:
   pip install python-docx openpyxl python-pptx

4. 检查依赖:
   pip install pillow	pytesseract

5. 查看完整依赖列表:
   pip install unstructured[all-docs]
""")

def main():
    """主函数"""
    print("Unstructured库可用性测试")
    print("=" * 60)

    test_unstructured_import()
    module_results = test_unstructured_modules()
    test_inference_model()

    print("\n" + "-" * 60)
    print("实际解析测试 (需要示例文件)")
    print("-" * 60)

    test_pdf_parsing()
    test_docx_parsing()
    test_pptx_parsing()
    test_xlsx_parsing()
    test_text_parsing()
    test_md_parsing()

    print_summary()

if __name__ == '__main__':
    main()
