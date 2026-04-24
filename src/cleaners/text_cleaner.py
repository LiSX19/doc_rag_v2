"""
文本清洗器实现
"""

import re
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import ftfy
import opencc
import yaml

from src.utils import OutputManager, get_logger

from .base import BaseCleaner

logger = get_logger(__name__)

# 尝试导入Unstructured的清洗功能
def _check_unstructured_available():
    """检查Unstructured库是否可用"""
    # 检测核心功能
    try:
        from unstructured.cleaners.core import (
            clean_bullets,
            clean_extra_whitespace,
            clean_non_ascii_chars,
            clean_ordered_bullets,
            clean_postfix,
            clean_prefix,
            group_broken_paragraphs,
            remove_punctuation,
        )
        from unstructured.cleaners.translate import translate_text
        core_available = True
    except ImportError:
        core_available = False
    
    # 检测OCR功能
    ocr_available = False
    if core_available:
        try:
            # OCR专用清洗功能
            from unstructured.cleaners.ocr import (
                clean_ordered_bullets as ocr_clean_ordered_bullets,
                clean_ligatures,
                clean_non_ascii_chars as ocr_clean_non_ascii_chars,
                replace_unicode_quotes,
            )
            ocr_available = True
        except ImportError:
            ocr_available = False
    
    return core_available, ocr_available

# 全局变量，延迟检测
_UNSTRUCTURED_CHECKED = False
UNSTRUCTURED_AVAILABLE = False
UNSTRUCTURED_OCR_AVAILABLE = False

def _ensure_unstructured_checked(force=False):
    """确保已检测Unstructured可用性
    
    Args:
        force: 是否强制重新检测
    """
    global _UNSTRUCTURED_CHECKED, UNSTRUCTURED_AVAILABLE, UNSTRUCTURED_OCR_AVAILABLE
    if not _UNSTRUCTURED_CHECKED or force:
        UNSTRUCTURED_AVAILABLE, UNSTRUCTURED_OCR_AVAILABLE = _check_unstructured_available()
        _UNSTRUCTURED_CHECKED = True
        if not UNSTRUCTURED_AVAILABLE:
            logger.warning("Unstructured库未安装，将使用基础清洗功能")
        else:
            if UNSTRUCTURED_OCR_AVAILABLE:
                logger.info("Unstructured库已检测到，将使用高级清洗功能（包括OCR清洗）")
            else:
                logger.info("Unstructured核心库已检测到，将使用高级清洗功能（OCR清洗功能不可用）")


@dataclass
class CleaningResult:
    """清洗结果"""
    filename: str
    original_text: str
    cleaned_text: str
    quality_report: Dict[str, Any]
    success: bool
    error: Optional[str] = None


@dataclass
class QualityReport:
    """质量检查报告"""
    original_length: int
    cleaned_length: int
    length_ratio: float
    char_set_valid: bool
    min_length_check: bool
    passed: bool
    issues: List[str]


class TextCleaner(BaseCleaner):
    """文本清洗器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化文本清洗器
        
        Args:
            config: 配置字典，包含：
                - pipeline: 清洗步骤列表
                - custom_rules: 自定义规则列表
                - quality_check: 质量检查配置
                - parallel: 并行处理配置
        """
        super().__init__(config)
        
        # 延迟检测Unstructured可用性
        _ensure_unstructured_checked()
        
        # 读取 cleaner 配置（适配 configs.yaml 结构）
        cleaner_config = self.config.get('cleaner', self.config)
        
        self.pipeline = cleaner_config.get('pipeline', ['structure', 'encoding', 'simplified'])
        self.custom_rules = cleaner_config.get('custom_rules', [])
        
        # 质量检查配置
        quality_config = cleaner_config.get('quality_check', {})
        self.quality_check_enabled = quality_config.get('enabled', True)
        self.min_length = quality_config.get('min_length', 10)
        self.max_length_ratio = quality_config.get('max_length_ratio', 0.1)
        
        # 并行处理配置
        parallel_config = cleaner_config.get('parallel', {})
        self.parallel_enabled = parallel_config.get('enabled', False)
        self.max_workers = parallel_config.get('max_workers', 4)
        
        # 加载自定义规则文件
        rules_file = cleaner_config.get('custom_rules_file')
        if rules_file and Path(rules_file).exists():
            self._load_custom_rules_from_file(rules_file)
        
        # 初始化繁简转换器
        if 'simplified' in self.pipeline:
            self.converter = opencc.OpenCC('t2s')  # 繁体转简体
        
        # Unstructured清洗配置
        unstructured_config = cleaner_config.get('unstructured', {})
        self.use_unstructured = unstructured_config.get('enabled', False) and UNSTRUCTURED_AVAILABLE
        self.unstructured_options = unstructured_config.get('options', {
            'clean_bullets': True,
            'clean_extra_whitespace': True,
            'clean_non_ascii_chars': False,
            'group_broken_paragraphs': True,
            'remove_punctuation': False,
        })
        
        if self.use_unstructured:
            logger.info("已启用Unstructured结构清洗功能")
        
        # 输出管理器
        self.output_manager = OutputManager(config)
    
    def _load_custom_rules_from_file(self, file_path: str):
        """从YAML文件加载自定义规则"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                rules_config = yaml.safe_load(f)
            
            if rules_config and 'rules' in rules_config:
                for rule in rules_config['rules']:
                    if rule.get('enabled', False):
                        self.custom_rules.append({
                            'name': rule.get('name', 'unnamed'),
                            'pattern': rule.get('pattern', ''),
                            'replacement': rule.get('replacement', ''),
                            'priority': rule.get('priority', 100)
                        })
                # 按优先级排序
                self.custom_rules.sort(key=lambda x: x.get('priority', 100))
                logger.info(f"已从 {file_path} 加载 {len(self.custom_rules)} 条自定义规则")
        except Exception as e:
            logger.warning(f"加载自定义规则文件失败: {e}")
    
    def clean(self, text: str, filename: Optional[str] = None, is_ocr: bool = False) -> str:
        """
        清洗文本
        
        Args:
            text: 原始文本
            filename: 文件名（用于保存输出）
            is_ocr: 是否为OCR文本（OCR文本需要特殊处理换行和断词）
            
        Returns:
            清洗后的文本
        """
        if not text:
            return ""
        
        original_text = text
        
        # 如果是OCR文本，先进行OCR专用清洗
        if is_ocr:
            text = self._clean_ocr_text(text)
        
        for step in self.pipeline:
            if step == 'structure':
                text = self._clean_structure(text)
            elif step == 'encoding':
                text = self._fix_encoding(text)
            elif step == 'simplified':
                text = self._convert_to_simplified(text)
            elif step == 'custom_rules':
                text = self._apply_custom_rules(text)
        
        cleaned_text = text.strip()
        
        # 质量检查
        quality_report = None
        if self.quality_check_enabled:
            quality_report = self._check_quality(original_text, cleaned_text)
            if not quality_report.passed:
                logger.warning(f"质量检查未通过: {quality_report.issues}")
        
        # 保存清洗结果（如果提供了文件名）
        if filename:
            metadata = {'pipeline': self.pipeline}
            if quality_report:
                metadata['quality_report'] = {
                    'original_length': quality_report.original_length,
                    'cleaned_length': quality_report.cleaned_length,
                    'length_ratio': quality_report.length_ratio,
                    'passed': quality_report.passed
                }
            self.output_manager.save_cleaned_text(
                filename=filename,
                original_content=original_text,
                cleaned_content=cleaned_text,
                metadata=metadata
            )
        
        return cleaned_text
    
    def clean_with_report(self, text: str, filename: Optional[str] = None, is_ocr: bool = False) -> CleaningResult:
        """
        清洗文本并返回详细报告
        
        Args:
            text: 原始文本
            filename: 文件名
            is_ocr: 是否为OCR文本
            
        Returns:
            清洗结果对象
        """
        try:
            original_text = text or ""
            cleaned_text = self.clean(text, filename, is_ocr=is_ocr)
            
            quality_report = {}
            if self.quality_check_enabled:
                report = self._check_quality(original_text, cleaned_text)
                quality_report = {
                    'original_length': report.original_length,
                    'cleaned_length': report.cleaned_length,
                    'length_ratio': report.length_ratio,
                    'passed': report.passed,
                    'issues': report.issues
                }
            
            return CleaningResult(
                filename=filename or "",
                original_text=original_text,
                cleaned_text=cleaned_text,
                quality_report=quality_report,
                success=True
            )
        except Exception as e:
            logger.error(f"清洗失败: {e}")
            return CleaningResult(
                filename=filename or "",
                original_text=text or "",
                cleaned_text="",
                quality_report={},
                success=False,
                error=str(e)
            )
    
    def clean_batch(self, texts: List[Union[str, Tuple[str, str]]]) -> List[CleaningResult]:
        """
        批量清洗文本
        
        Args:
            texts: 文本列表，可以是字符串或(文本, 文件名)元组
            
        Returns:
            清洗结果列表
        """
        results = []
        
        for item in texts:
            if isinstance(item, tuple):
                text, filename = item
            else:
                text, filename = item, None
            
            result = self.clean_with_report(text, filename)
            results.append(result)
        
        return results
    
    def clean_batch_parallel(self, texts: List[Union[str, Tuple[str, str]]]) -> List[CleaningResult]:
        """
        并行批量清洗文本
        
        Args:
            texts: 文本列表
            
        Returns:
            清洗结果列表
        """
        if not self.parallel_enabled or len(texts) < 2:
            return self.clean_batch(texts)
        
        results = [None] * len(texts)
        
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_index = {}
            for i, item in enumerate(texts):
                if isinstance(item, tuple):
                    text, filename = item
                else:
                    text, filename = item, None
                
                future = executor.submit(_clean_worker, text, filename, self.config)
                future_to_index[future] = i
            
            # 收集结果
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    result = future.result()
                    results[index] = result
                except Exception as e:
                    logger.error(f"并行清洗任务失败: {e}")
                    item = texts[index]
                    filename = item[1] if isinstance(item, tuple) else None
                    results[index] = CleaningResult(
                        filename=filename or "",
                        original_text=item[0] if isinstance(item, tuple) else item,
                        cleaned_text="",
                        quality_report={},
                        success=False,
                        error=str(e)
                    )
        
        return results
    
    def _check_quality(self, original_text: str, cleaned_text: str) -> QualityReport:
        """
        质量检查
        
        Args:
            original_text: 原始文本
            cleaned_text: 清洗后文本
            
        Returns:
            质量检查报告
        """
        issues = []
        
        original_length = len(original_text)
        cleaned_length = len(cleaned_text)
        
        # 长度检查
        min_length_check = cleaned_length >= self.min_length
        if not min_length_check:
            issues.append(f"清洗后文本长度({cleaned_length})小于最小长度({self.min_length})")
        
        # 长度比例检查（防止过度清洗）
        if original_length > 0:
            length_ratio = cleaned_length / original_length
        else:
            length_ratio = 1.0
        
        if length_ratio < self.max_length_ratio:
            issues.append(f"长度比例({length_ratio:.2%})过低，可能过度清洗")
        
        # 字符集检查
        char_set_valid = self._check_char_set(cleaned_text)
        if not char_set_valid:
            issues.append("文本包含无效字符")
        
        passed = min_length_check and length_ratio >= self.max_length_ratio and char_set_valid
        
        return QualityReport(
            original_length=original_length,
            cleaned_length=cleaned_length,
            length_ratio=length_ratio,
            char_set_valid=char_set_valid,
            min_length_check=min_length_check,
            passed=passed,
            issues=issues
        )
    
    def _check_char_set(self, text: str) -> bool:
        """检查字符集是否有效"""
        # 检查是否包含过多的替换字符（通常表示编码问题）
        replacement_char_count = text.count('\ufffd')
        if len(text) > 0 and replacement_char_count / len(text) > 0.1:
            return False
        return True
    
    def _clean_structure(self, text: str) -> str:
        """结构清洗：移除多余空白、规范化换行等"""
        # 如果启用Unstructured，使用Unstructured进行结构清洗
        if self.use_unstructured and UNSTRUCTURED_AVAILABLE:
            return self._clean_structure_unstructured(text)
        
        # 基础结构清洗
        return self._clean_structure_basic(text)
    
    def _clean_structure_unstructured(self, text: str) -> str:
        """使用Unstructured进行结构清洗"""
        try:
            # 导入Unstructured清洗函数
            from unstructured.cleaners.core import (
                clean_bullets,
                clean_extra_whitespace,
                clean_non_ascii_chars,
                clean_ordered_bullets,
                group_broken_paragraphs,
                remove_punctuation,
            )
            
            opts = self.unstructured_options
            
            # 清理项目符号
            if opts.get('clean_bullets', True):
                text = clean_bullets(text)
                text = clean_ordered_bullets(text)
            
            # 清理多余空白
            if opts.get('clean_extra_whitespace', True):
                text = clean_extra_whitespace(text)
            
            # 清理非ASCII字符
            if opts.get('clean_non_ascii_chars', False):
                text = clean_non_ascii_chars(text)
            
            # 组合断裂的段落
            if opts.get('group_broken_paragraphs', True):
                text = group_broken_paragraphs(text)
            
            # 移除标点（可选）
            if opts.get('remove_punctuation', False):
                text = remove_punctuation(text)
            
            # 应用额外的基础清洗以确保换行符保留
            text = self._clean_structure_basic(text)
            
            logger.debug("Unstructured结构清洗完成")
            return text
        except Exception as e:
            logger.warning(f"Unstructured结构清洗失败，回退到基础清洗: {e}")
            return self._clean_structure_basic(text)
    
    def _clean_structure_basic(self, text: str) -> str:
        """基础结构清洗：移除多余空白、规范化换行等"""
        # 规范化换行符
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # 移除控制字符（保留换行符\n）
        text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', text)
        
        # 合并行内多个空白字符（但保留换行符）
        text = re.sub(r'[ \t]+', ' ', text)
        
        # 合并多个换行（保留段落分隔）
        text = re.sub(r'\n[ \t]*\n+', '\n\n', text)
        
        # 移除每行首尾的空格和制表符（但保留换行符结构）
        lines = text.split('\n')
        lines = [line.strip(' \t') for line in lines]
        text = '\n'.join(lines)
        
        return text
    
    def _fix_encoding(self, text: str) -> str:
        """修复编码问题"""
        return ftfy.fix_text(text)
    
    def _convert_to_simplified(self, text: str) -> str:
        """繁体转简体"""
        if hasattr(self, 'converter'):
            return self.converter.convert(text)
        return text
    
    def _apply_custom_rules(self, text: str) -> str:
        """应用自定义规则"""
        for rule in self.custom_rules:
            if rule.get('enabled', True):
                pattern = rule.get('pattern', '')
                replacement = rule.get('replacement', '')
                if pattern:
                    text = re.sub(pattern, replacement, text)
        return text
    
    def _clean_ocr_text(self, text: str) -> str:
        """
        OCR文本专用清洗：处理换行频繁、连字符断词等问题
        
        Args:
            text: OCR识别后的文本
            
        Returns:
            清洗后的文本
        """
        if not text:
            return text
        
        # 首先应用Unstructured的OCR清洗（如果可用）
        if UNSTRUCTURED_OCR_AVAILABLE:
            try:
                # 导入OCR清洗函数
                from unstructured.cleaners.ocr import (
                    clean_ligatures,
                    replace_unicode_quotes,
                    clean_ordered_bullets as ocr_clean_ordered_bullets,
                )
                # 清理连字（ligatures）
                text = clean_ligatures(text)
                # 替换Unicode引号
                text = replace_unicode_quotes(text)
                # 清理OCR中的有序列表符号
                text = ocr_clean_ordered_bullets(text)
            except Exception as e:
                logger.debug(f"Unstructured OCR清洗失败: {e}")
        
        # 修复连字符断词（如 "com-\nputer" -> "computer"）
        text = self._fix_ocr_hyphenation(text)
        
        # 智能合并断行
        text = self._merge_ocr_line_breaks(text)
        
        return text
    
    def _fix_ocr_hyphenation(self, text: str) -> str:
        """
        修复OCR中的连字符断词
        例如："com-\nputer" -> "computer"
        """
        # 匹配连字符+换行+小写字母的模式
        text = re.sub(r'(\w)-\n(\w)', r'\1\2', text)
        # 匹配连字符+空白+换行+小写字母的模式
        text = re.sub(r'(\w)-\s*\n\s*(\w)', r'\1\2', text)
        return text
    
    def _merge_ocr_line_breaks(self, text: str) -> str:
        """
        智能合并OCR中的断行
        OCR文本通常每行都换行，需要根据语义合并
        """
        # 规范化换行符
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # 分割成行
        lines = text.split('\n')
        
        merged_lines = []
        current_para = ""
        
        for line in lines:
            line = line.strip()
            if not line:
                # 空行表示段落结束
                if current_para:
                    merged_lines.append(current_para)
                    current_para = ""
                continue
            
            if not current_para:
                current_para = line
            else:
                # 检查是否需要合并
                # 当前行不以标点结尾，且下一行（或当前累积）以小写开头
                last_char = current_para[-1] if current_para else ""
                first_char = line[0] if line else ""
                
                # 如果以标点结尾，或下一行以大写/数字开头，则分段
                if last_char in '.。!！?？;；:：' or first_char.isupper() or first_char.isdigit():
                    merged_lines.append(current_para)
                    current_para = line
                else:
                    # 合并行，添加空格
                    current_para = current_para + " " + line
        
        # 添加最后一段
        if current_para:
            merged_lines.append(current_para)
        
        # 合并段落，使用双换行分隔
        text = '\n\n'.join([line for line in merged_lines if line.strip()])
        
        # 清理多余空白（但保留段落结构）
        text = re.sub(r'[ \t]+', ' ', text)
        
        # 合并过多的换行（超过2个的换行合并为2个）
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()


# ==================== 并行处理辅助函数 ====================

def _clean_worker(text: str, filename: Optional[str], config: Dict[str, Any]) -> CleaningResult:
    """
    并行清洗工作函数（必须在模块级别定义以便pickle序列化）
    
    Args:
        text: 原始文本
        filename: 文件名
        config: 配置字典
        
    Returns:
        清洗结果
    """
    try:
        cleaner = TextCleaner(config)
        return cleaner.clean_with_report(text, filename)
    except Exception as e:
        return CleaningResult(
            filename=filename or "",
            original_text=text or "",
            cleaned_text="",
            quality_report={},
            success=False,
            error=str(e)
        )
