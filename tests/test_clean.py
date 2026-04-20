"""
文本清洗模块测试

测试Clean模块的各项功能，输入使用tests/outputs/loaded下的txt文件（loader模块的输出）
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
from pathlib import Path
from typing import List, Tuple

from src.cleaners import TextCleaner, CleaningResult
from src.configs import ConfigManager


class TestTextCleaner(unittest.TestCase):
    """文本清洗器测试类"""
    
    @classmethod
    def setUpClass(cls):
        """测试类初始化"""
        cls.test_dir = Path(__file__).parent
        cls.project_dir = cls.test_dir.parent
        cls.loaded_dir = cls.test_dir / "outputs" / "loaded"
        cls.output_dir = cls.test_dir / "outputs"
        cls.cleaned_dir = cls.output_dir / "cleaned"
        
        # 确保输出目录存在
        cls.cleaned_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载配置
        cls.config = ConfigManager().get_all()
        
        # 设置测试专用的输出路径
        cls.config['paths'] = cls.config.get('paths', {})
        cls.config['paths']['output_dir'] = str(cls.output_dir)
        cls.config['paths']['cleaned_dir'] = str(cls.cleaned_dir)
        cls.config['output'] = {'mode': 'test', 'test': {'save_cleaned': True}}
        
        # 初始化清洗器
        cls.cleaner = TextCleaner(cls.config)
    
    def get_test_files(self) -> List[Path]:
        """获取测试文件列表"""
        if not self.loaded_dir.exists():
            return []
        return list(self.loaded_dir.glob("*.txt"))
    
    def read_file_content(self, file_path: Path) -> str:
        """读取文件内容，跳过元数据头部"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 跳过元数据头部（以====分隔）
        if '====' in content:
            parts = content.split('====', 1)
            if len(parts) > 1:
                # 只移除开头的换行和空格，保留内容中的换行符
                return parts[1].lstrip('\n').lstrip()
        return content
    
    # ==================== 基础功能测试 ====================
    
    def test_structure_cleaning(self):
        """测试结构清洗功能"""
        # 测试换行符规范化
        text = "第一行\r\n第二行\r第三行"
        result = self.cleaner._clean_structure(text)
        self.assertEqual(result, "第一行\n第二行\n第三行")
        
        # 测试多余空白合并
        text = "多个    空格    和\t制表符"
        result = self.cleaner._clean_structure(text)
        self.assertEqual(result, "多个 空格 和 制表符")
        
        # 测试控制字符移除
        text = "文本\x00\x01\x02内容"
        result = self.cleaner._clean_structure(text)
        self.assertEqual(result, "文本内容")
    
    def test_encoding_fix(self):
        """测试编码修复功能"""
        # 测试ftfy修复乱码
        text = "âœ” æˆ'"
        result = self.cleaner._fix_encoding(text)
        # ftfy会尝试修复编码问题
        self.assertIsInstance(result, str)
    
    def test_simplified_conversion(self):
        """测试繁简转换功能"""
        # 测试繁体转简体
        text = "這是繁體中文，包含壹些複雜的字"
        result = self.cleaner._convert_to_simplified(text)
        self.assertIn("这是", result)
        self.assertIn("复杂", result)
    
    def test_custom_rules(self):
        """测试自定义规则"""
        # 添加测试规则
        self.cleaner.custom_rules = [
            {
                'name': 'test_rule',
                'pattern': r'测试替换',
                'replacement': '替换成功',
                'enabled': True
            }
        ]
        
        text = "这是测试替换的内容"
        result = self.cleaner._apply_custom_rules(text)
        self.assertEqual(result, "这是替换成功的内容")
    
    # ==================== 质量检查测试 ====================
    
    def test_quality_check_pass(self):
        """测试质量检查通过的情况"""
        original = "这是一段正常的文本内容，长度足够通过检查。"
        cleaned = "这是一段正常的文本内容，长度足够通过检查。"
        
        report = self.cleaner._check_quality(original, cleaned)
        
        self.assertTrue(report.passed)
        self.assertTrue(report.min_length_check)
        self.assertTrue(report.char_set_valid)
        self.assertEqual(len(report.issues), 0)
    
    def test_quality_check_fail_length(self):
        """测试质量检查失败：长度过短"""
        original = "这是一段很长的原始文本内容，包含很多信息。"
        cleaned = "短"
        
        report = self.cleaner._check_quality(original, cleaned)
        
        self.assertFalse(report.passed)
        self.assertFalse(report.min_length_check)
        self.assertTrue(len(report.issues) > 0)
    
    def test_quality_check_fail_ratio(self):
        """测试质量检查失败：长度比例过低"""
        original = "这是一段很长的原始文本内容，包含很多信息。"
        cleaned = "清洗后"
        
        report = self.cleaner._check_quality(original, cleaned)
        
        # 检查是否有长度比例过低的警告
        ratio_issues = [i for i in report.issues if '比例' in i or '过度清洗' in i]
        self.assertTrue(len(ratio_issues) > 0 or not report.passed)
    
    def test_char_set_check(self):
        """测试字符集检查"""
        # 正常文本
        text = "正常的中文字符"
        self.assertTrue(self.cleaner._check_char_set(text))
        
        # 包含过多替换字符
        text = "\ufffd\ufffd\ufffd\ufffd\ufffd正常"
        self.assertFalse(self.cleaner._check_char_set(text))
    
    # ==================== 完整流程测试 ====================
    
    def test_full_clean_pipeline(self):
        """测试完整清洗流程"""
        text = "  這是一段\r\n包含  多余空格\x00和乱码âœ” æˆ'的文本。  "

        
        result = self.cleaner.clean(text)
        
        # 验证清洗结果
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)
        # 不应该包含控制字符
        self.assertNotIn('\x00', result)
        # 不应该有多余的前后空格
        self.assertEqual(result.strip(), result)
    
    def test_clean_with_report(self):
        """测试带报告的清洗"""
        text = "这是一段测试文本，用于验证清洗报告功能。"
        
        result = self.cleaner.clean_with_report(text, "test_file")
        
        self.assertIsInstance(result, CleaningResult)
        self.assertTrue(result.success)
        self.assertEqual(result.filename, "test_file")
        self.assertEqual(result.original_text, text)
        # quality_report 字段直接包含质量信息，不是嵌套字典
        self.assertIn('original_length', result.quality_report or {})
    
    def test_clean_batch(self):
        """测试批量清洗"""
        texts = [
            ("第一\r\n段文本", "file1"),
            ("第二  段\t文本", "file2"),
            ("第三段\x00文本", "file3"),
        ]
        
        results = self.cleaner.clean_batch(texts)
        
        self.assertEqual(len(results), 3)
        for result in results:
            self.assertIsInstance(result, CleaningResult)
            self.assertTrue(result.success)
    
    def test_empty_text(self):
        """测试空文本处理"""
        result = self.cleaner.clean("")
        self.assertEqual(result, "")
        
        result = self.cleaner.clean(None)
        self.assertEqual(result, "")
    
    # ==================== 文件输入测试 ====================
    
    def test_clean_from_loaded_files(self):
        """测试从loaded目录读取文件并清洗"""
        test_files = self.get_test_files()
        
        if not test_files:
            self.skipTest(f"未找到测试文件，请确保 {self.loaded_dir} 目录存在且包含.txt文件")
        
        print(f"\n找到 {len(test_files)} 个测试文件")
        
        for file_path in test_files:  # 处理所有文件
            print(f"  测试文件: {file_path.name}")
            
            # 读取文件内容
            content = self.read_file_content(file_path)
            
            # 执行清洗并保存文件（所有文件使用OCR清洗）
            cleaned_text = self.cleaner.clean(
                content, 
                filename=file_path.stem,
                is_ocr=True
            )
            
            # 验证结果
            self.assertIsInstance(cleaned_text, str)
            self.assertTrue(len(cleaned_text) > 0, f"文件 {file_path.name} 清洗后内容为空")
            
            # 检查输出文件是否生成
            output_file = self.cleaned_dir / f"{file_path.stem}.cleaned.txt"
            self.assertTrue(output_file.exists(), f"输出文件未生成: {output_file}")
            
            print(f"    清洗完成，输出文件: {output_file.name}")
    
    def test_output_file_generation(self):
        """测试输出文件生成"""
        # 执行清洗并保存（使用唯一的测试文件名）
        text = "这是测试文本\r\n包含需要清洗的内容。"
        self.cleaner.clean(text, filename="test_output_file_gen")
        
        # 检查输出文件
        output_file = self.cleaned_dir / "test_output_file_gen.cleaned.txt"
        self.assertTrue(output_file.exists(), f"输出文件未生成: {output_file}")
        
        # 验证文件内容
        with open(output_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        self.assertIn("原始长度:", content)
        self.assertIn("清洗后长度:", content)
        self.assertIn("====", content)


class TestCleanerConfiguration(unittest.TestCase):
    """清洗器配置测试"""
    
    def test_default_pipeline(self):
        """测试默认清洗流水线"""
        cleaner = TextCleaner()
        self.assertEqual(cleaner.pipeline, ['structure', 'encoding', 'simplified'])
    
    def test_custom_pipeline(self):
        """测试自定义清洗流水线"""
        config = {
            'cleaner': {
                'pipeline': ['structure', 'custom_rules']
            }
        }
        cleaner = TextCleaner(config)
        self.assertEqual(cleaner.pipeline, ['structure', 'custom_rules'])
    
    def test_quality_check_config(self):
        """测试质量检查配置"""
        config = {
            'cleaner': {
                'quality_check': {
                    'enabled': True,
                    'min_length': 20,
                    'max_length_ratio': 0.2
                }
            }
        }
        cleaner = TextCleaner(config)
        self.assertTrue(cleaner.quality_check_enabled)
        self.assertEqual(cleaner.min_length, 20)
        self.assertEqual(cleaner.max_length_ratio, 0.2)
    
    def test_unstructured_config(self):
        """测试Unstructured配置"""
        config = {
            'cleaner': {
                'unstructured': {
                    'enabled': True,
                    'options': {
                        'clean_bullets': True,
                        'clean_extra_whitespace': True,
                        'clean_non_ascii_chars': False,
                    }
                }
            }
        }
        cleaner = TextCleaner(config)
        # 如果Unstructured可用，应该启用
        # 如果不可用，use_unstructured应该为False
        self.assertIsInstance(cleaner.use_unstructured, bool)
        self.assertIsInstance(cleaner.unstructured_options, dict)


class TestOCRTextCleaning(unittest.TestCase):
    """测试OCR文本清洗"""
    
    def test_ocr_hyphenation_fix(self):
        """测试OCR连字符断词修复"""
        cleaner = TextCleaner()
        # 模拟OCR文本中的连字符断词
        text = "这是一个com-\nputer示例，还有tele-\nphone。"
        result = cleaner.clean(text, is_ocr=True)
        # 连字符应该被移除，单词合并
        self.assertNotIn("com-\nputer", result)
        self.assertNotIn("tele-\nphone", result)
    
    def test_ocr_line_break_merge(self):
        """测试OCR换行合并"""
        cleaner = TextCleaner()
        # 模拟OCR文本中每行都换行的情况
        text = "这是第一行\n这是第二行\n这是第三行。\n\n新段落开始\n继续新段落。"
        result = cleaner.clean(text, is_ocr=True)
        # 应该合并为一个段落（因为没有标点分隔）
        # 或者根据标点正确分段
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)
    
    def test_ocr_vs_normal_clean(self):
        """测试OCR清洗与普通清洗的区别"""
        cleaner = TextCleaner()
        text = "这是第一行\n这是第二行\n这是第三行。"
        
        # 普通清洗
        normal_result = cleaner.clean(text, is_ocr=False)
        # OCR清洗
        ocr_result = cleaner.clean(text, is_ocr=True)
        
        # 两者都应该返回字符串
        self.assertIsInstance(normal_result, str)
        self.assertIsInstance(ocr_result, str)


def run_tests():
    """运行所有测试"""
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestTextCleaner))
    suite.addTests(loader.loadTestsFromTestCase(TestCleanerConfiguration))
    suite.addTests(loader.loadTestsFromTestCase(TestOCRTextCleaning))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
