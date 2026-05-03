#!/usr/bin/env python3
"""
使用LibreOffice转换.doc文件测试

测试LibreOffice是否能正确转换有问题的.doc文件
"""

import os
import subprocess
import tempfile
from pathlib import Path

def find_libreoffice():
    """自动查找 LibreOffice 路径"""
    import os
    
    # 常见的 LibreOffice 安装路径
    possible_paths = [
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        r"C:\LibreOffice\program\soffice.exe",
        r"D:\Program Files\LibreOffice\program\soffice.exe",
        r"D:\Program Files (x86)\LibreOffice\program\soffice.exe",
    ]
    
    # 首先尝试 PATH 中的 soffice
    try:
        import subprocess
        result = subprocess.run(
            ["soffice", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print("  ✓ 找到 PATH 中的 soffice")
            return "soffice"
    except:
        pass
    
    # 尝试常见路径
    for path in possible_paths:
        if os.path.exists(path):
            print(f"  ✓ 找到 LibreOffice: {path}")
            return path
    
    print("  ✗ 未找到 LibreOffice")
    return None

def test_libreoffice_conversion():
    """测试LibreOffice转换功能"""
    print("=" * 60)
    print("测试 LibreOffice 转换功能")
    print("=" * 60)

    # 查找 LibreOffice
    libreoffice_path = find_libreoffice()
    if not libreoffice_path:
        print("错误: 未找到 LibreOffice")
        return False

    # 测试文件
    input_file = Path(r'D:\Code\HSKRAG\doc_rag_v2\data\第八课 生活中不缺少美.doc')
    if not input_file.exists():
        print(f"错误: 文件不存在: {input_file}")
        return False

    # 创建临时输出目录
    output_dir = Path(tempfile.mkdtemp())
    print(f"输出目录: {output_dir}")

    try:
        # 测试soffice命令是否可用
        print("\n[1/3] 测试 LibreOffice 命令...")
        result = subprocess.run(
            [libreoffice_path, "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print(f"  ✓ LibreOffice 版本: {result.stdout.strip()}")
        else:
            print(f"  ✗ 命令失败: {result.stderr}")
            return False

        # 转换为txt
        print("\n[2/3] 转换为 .txt...")
        result = subprocess.run(
            [
                libreoffice_path, "--headless",
                "--convert-to", "txt",
                str(input_file),
                "--outdir", str(output_dir)
            ],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            print("  ✓ 转换成功")
        else:
            print(f"  ✗ 转换失败: {result.stderr}")

        # 转换为docx
        print("\n[3/3] 转换为 .docx...")
        result = subprocess.run(
            [
                libreoffice_path, "--headless",
                "--convert-to", "docx",
                str(input_file),
                "--outdir", str(output_dir)
            ],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            print("  ✓ 转换成功")
        else:
            print(f"  ✗ 转换失败: {result.stderr}")

        # 检查输出文件
        print("\n[4/4] 检查输出文件...")
        output_files = list(output_dir.glob("*"))
        if output_files:
            print(f"  ✓ 生成了 {len(output_files)} 个文件:")
            for file in output_files:
                print(f"    - {file.name} ({file.stat().st_size} bytes)")
                
                # 显示txt文件内容预览
                if file.suffix == '.txt':
                    print("    内容预览:")
                    try:
                        with open(file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            preview = content[:200] + "..." if len(content) > 200 else content
                            print(f"    {preview}")
                    except Exception as e:
                        print(f"    读取失败: {e}")
        else:
            print("  ✗ 未生成输出文件")

        return True

    finally:
        # 清理临时目录
        import shutil
        try:
            shutil.rmtree(output_dir)
            print(f"\n已清理临时目录: {output_dir}")
        except Exception as e:
            print(f"清理临时目录失败: {e}")


def main():
    """主函数"""
    success = test_libreoffice_conversion()
    if success:
        print("\n✅ LibreOffice 转换功能测试成功！")
        print("\n现在可以使用以下命令处理文件:")
        print("  soffice --headless --convert-to txt input.doc --outdir output")
        print("  soffice --headless --convert-to docx input.doc --outdir output")
    else:
        print("\n❌ LibreOffice 转换功能测试失败")


if __name__ == '__main__':
    main()
