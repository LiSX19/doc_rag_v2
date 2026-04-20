#!/usr/bin/env python3
"""
测试读取data目录下所有文件
验证文档加载器的完整功能
"""

import sys
import os
import shutil
import argparse
from pathlib import Path
import json
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def get_all_files(data_dir: Path):
    """获取所有支持的文件"""
    supported_extensions = {
        '.pdf': 'PDF',
        '.docx': 'Word',
        '.doc': 'Word (旧版)',
        '.wps': 'WPS',
        '.xlsx': 'Excel',
        '.xls': 'Excel (旧版)',
        '.pptx': 'PowerPoint',
        '.ppt': 'PowerPoint (旧版)',
        '.ppsx': 'PowerPoint (旧版)',
        '.txt': 'Text',
        '.md': 'Markdown',
        '.html': 'HTML',
        '.htm': 'HTML',
        '.csv': 'CSV',
        '.caj': 'CAJ',

       
    }
    
    files = []
    for ext, type_name in supported_extensions.items():
        for file_path in data_dir.rglob(f'*{ext}'):
            files.append({
                'path': file_path,
                'type': type_name,
                'ext': ext,
                'size': file_path.stat().st_size,
            })
    
    return files


def clear_output_dir(output_dir: Path):
    """清除输出目录"""
    if output_dir.exists():
        print(f"清除旧输出目录: {output_dir}")
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"创建新输出目录: {output_dir}")


def test_file_loader(file_info: dict, output_dir: Path):
    """测试单个文件加载"""
    from src.loaders.document_loader import DocumentLoader
    
    file_path = file_info['path']
    file_type = file_info['type']
    
    print(f"\n{'='*60}")
    print(f"测试文件: {file_path.name}")
    print(f"类型: {file_type}")
    print(f"大小: {file_info['size'] / 1024:.1f} KB")
    print(f"{'='*60}")
    
    try:
        # 创建文档加载器
        config = {
            'ocr': {
                'enabled': True,
                'conda_env': 'OCR',
                'timeout': 300,
            }
        }
        loader = DocumentLoader(config)
        
        # 加载文档
        result = loader.load_document(file_path)
        
        # 显示结果
        print(f"\n[OK] 加载成功")
        print(f"解析器: {result['metadata'].get('parser', 'unknown')}")
        print(f"内容长度: {len(result['content'])} 字符")
        
        # 显示前200字符预览
        preview = result['content'][:200].replace('\n', ' ')
        print(f"\n内容预览:\n{preview}...")
        
        # 保存结果
        output_file = output_dir / f"{file_path.stem}.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"文件: {file_path}\n")
            f.write(f"类型: {file_type}\n")
            f.write(f"解析器: {result['metadata'].get('parser', 'unknown')}\n")
            f.write(f"{'='*60}\n\n")
            f.write(result['content'])
        
        print(f"\n结果已保存: {output_file}")
        
        return {
            'success': True,
            'file': str(file_path),
            'type': file_type,
            'parser': result['metadata'].get('parser', 'unknown'),
            'content_length': len(result['content']),
            'output': str(output_file),
        }
        
    except Exception as e:
        print(f"\n[X] 加载失败: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            'success': False,
            'file': str(file_path),
            'type': file_type,
            'error': str(e),
        }


def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='测试文档加载器 - 读取指定目录下所有文件')
    parser.add_argument(
        '--input-dir', '-i',
        type=str,
        default='data',
        help='输入目录路径 (默认: data)'
    )
    parser.add_argument(
        '--output-dir', '-o',
        type=str,
        default='tests/outputs/loaded',
        help='输出目录路径 (默认: tests/outputs/loaded)'
    )
    parser.add_argument(
        '--keep-output', '-k',
        action='store_true',
        help='保留之前的输出，不清除'
    )
    
    args = parser.parse_args()
    
    print("\n" + "#"*60)
    print("# 文档加载器全量测试")
    print("#"*60)
    
    # 设置路径
    data_dir = project_root / args.input_dir
    output_dir = project_root / args.output_dir
    
    print(f"\n数据目录: {data_dir}")
    print(f"输出目录: {output_dir}")
    
    # 检查数据目录是否存在
    if not data_dir.exists():
        print(f"\n[X] 数据目录不存在: {data_dir}")
        return
    
    # 清除或创建输出目录
    if not args.keep_output:
        clear_output_dir(output_dir)
    else:
        output_dir.mkdir(parents=True, exist_ok=True)
    
    # 获取所有文件
    files = get_all_files(data_dir)
    
    if not files:
        print("\n[X] 未找到任何支持的文件")
        return
    
    print(f"\n找到 {len(files)} 个文件:")
    for i, file_info in enumerate(files, 1):
        print(f"  {i}. {file_info['path'].name} ({file_info['type']}, {file_info['size']/1024:.1f} KB)")
    
    # 测试每个文件
    results = []
    success_count = 0
    fail_count = 0
    
    print("\n" + "#"*60)
    print("# 开始测试")
    print("#"*60)
    
    for file_info in files:
        result = test_file_loader(file_info, output_dir)
        results.append(result)
        
        if result['success']:
            success_count += 1
        else:
            fail_count += 1
    
    # 生成报告
    report = {
        'test_time': datetime.now().isoformat(),
        'input_dir': str(data_dir),
        'output_dir': str(output_dir),
        'total_files': len(files),
        'success_count': success_count,
        'fail_count': fail_count,
        'results': results,
    }
    
    # 保存报告
    report_file = output_dir / "_report.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    # 打印总结
    print("\n" + "#"*60)
    print("# 测试总结")
    print("#"*60)
    print(f"总文件数: {len(files)}")
    print(f"成功: {success_count}")
    print(f"失败: {fail_count}")
    print(f"\n报告已保存: {report_file}")
    
    # 打印失败详情
    if fail_count > 0:
        print("\n失败的文件:")
        for result in results:
            if not result['success']:
                print(f"  - {result['file']}: {result.get('error', 'Unknown error')}")


if __name__ == "__main__":
    main()
