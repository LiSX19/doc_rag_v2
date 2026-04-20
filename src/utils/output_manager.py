"""
输出管理模块

统一管理各模块的输出，支持测试/生产模式切换
"""

import json
import pickle
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np

from .file_utils import FileUtils
from .logger import get_logger

logger = get_logger(__name__)


class OutputManager:
    """输出管理器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化输出管理器
        
        Args:
            config: 配置字典，包含 output.* 配置
        """
        self.config = config or {}
        
        # 读取输出配置
        output_config = self.config.get('output', {})
        self.mode = output_config.get('mode', 'test')
        
        # 根据模式获取输出配置
        mode_config = output_config.get(self.mode, output_config.get('test', {}))
        
        self._save_loaded = mode_config.get('save_loaded', True)
        self._save_cleaned = mode_config.get('save_cleaned', True)
        self._save_chunks = mode_config.get('save_chunks', True)
        self._save_dedup_report = mode_config.get('save_dedup_report', True)
        self._save_embeddings = mode_config.get('save_embeddings', True)
        self._save_retrieval = mode_config.get('save_retrieval', True)
        self._save_evaluation = mode_config.get('save_evaluation', True)
        
        # 输出目录
        paths_config = self.config.get('paths', {})
        self.output_dir = Path(paths_config.get('output_dir', './outputs'))
        self.loaded_dir = Path(paths_config.get('loaded_dir', './outputs/loaded'))
        self.cleaned_dir = Path(paths_config.get('cleaned_dir', './outputs/cleaned'))
        self.chunks_dir = Path(paths_config.get('chunks_dir', './outputs/chunks'))
        self.embeddings_dir = Path(paths_config.get('embeddings_dir', './outputs/embeddings'))
        self.retrieval_dir = Path(paths_config.get('retrieval_dir', './outputs/retrieval'))
        self.evaluation_dir = Path(paths_config.get('evaluation_dir', './outputs/evaluation'))
        
        # 创建输出目录
        self._ensure_directories()
        
        logger.info(f"输出管理器初始化完成，模式: {self.mode}")
        logger.info(f"输出目录: {self.output_dir}")
    
    def _ensure_directories(self):
        """确保输出目录存在"""
        dirs = [
            self.output_dir,
            self.loaded_dir,
            self.cleaned_dir,
            self.chunks_dir,
            self.embeddings_dir,
            self.retrieval_dir,
            self.evaluation_dir,
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)
    
    def _get_timestamp(self) -> str:
        """获取时间戳"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def _should_save(self, save_flag: bool) -> bool:
        """检查是否应该保存"""
        return save_flag
    
    # ==================== Loader 输出 ====================
    
    def save_loaded_document(
        self,
        filename: str,
        content: str,
        metadata: Dict[str, Any]
    ) -> Optional[Path]:
        """
        保存加载的文档
        
        Args:
            filename: 文件名
            content: 文档内容
            metadata: 元数据
            
        Returns:
            保存的文件路径，如果不保存则返回 None
        """
        if not self._should_save(self._save_loaded):
            return None
        
        # 保存文本内容
        output_path = self.loaded_dir / f"{filename}.txt"
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"文件: {metadata.get('source', filename)}\n")
                f.write(f"解析器: {metadata.get('parser', 'unknown')}\n")
                f.write(f"大小: {metadata.get('size_bytes', 0)} 字节\n")
                f.write("=" * 80 + "\n\n")
                f.write(content)
            
            logger.debug(f"已保存加载的文档: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"保存加载文档失败: {e}")
            return None
    
    def save_loaded_documents_batch(
        self,
        documents: List[Dict[str, Any]]
    ) -> List[Optional[Path]]:
        """批量保存加载的文档"""
        paths = []
        for doc in documents:
            filename = Path(doc['metadata']['source']).stem
            path = self.save_loaded_document(
                filename,
                doc['content'],
                doc['metadata']
            )
            paths.append(path)
        return paths
    
    # ==================== Cleaner 输出 ====================
    
    def save_cleaned_text(
        self,
        filename: str,
        original_content: str,
        cleaned_content: str,
        metadata: Optional[Dict] = None
    ) -> Optional[Path]:
        """保存清洗后的文本"""
        if not self._should_save(self._save_cleaned):
            return None
        
        output_path = self.cleaned_dir / f"{filename}.cleaned.txt"
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"原始文件: {filename}\n")
                f.write(f"原始长度: {len(original_content)} 字符\n")
                f.write(f"清洗后长度: {len(cleaned_content)} 字符\n")
                if metadata:
                    f.write(f"清洗步骤: {metadata.get('pipeline', [])}\n")
                f.write("=" * 80 + "\n\n")
                f.write(cleaned_content)
            
            logger.debug(f"已保存清洗后的文本: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"保存清洗文本失败: {e}")
            return None
    
    # ==================== Chunker 输出 ====================
    
    def save_chunks(
        self,
        filename: str,
        chunks: List[Dict[str, Any]]
    ) -> Optional[Path]:
        """保存分块结果"""
        if not self._should_save(self._save_chunks):
            return None
        
        output_path = self.chunks_dir / f"{filename}.chunks.json"
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'filename': filename,
                    'chunk_count': len(chunks),
                    'timestamp': self._get_timestamp(),
                    'chunks': chunks,
                }, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"已保存分块结果: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"保存分块结果失败: {e}")
            return None
    
    # ==================== Deduper 输出 ====================
    
    def save_dedup_report(
        self,
        report: Dict[str, Any],
        filename: Optional[str] = None
    ) -> Optional[Path]:
        """保存去重报告"""
        if not self._should_save(self._save_dedup_report):
            return None
        
        if filename is None:
            filename = f"dedup_report_{self._get_timestamp()}"
        
        output_path = self.output_dir / f"{filename}.json"
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'timestamp': self._get_timestamp(),
                    **report,
                }, f, ensure_ascii=False, indent=2)
            
            logger.info(f"已保存去重报告: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"保存去重报告失败: {e}")
            return None
    
    # ==================== Embedder 输出 ====================
    
    def save_embeddings(
        self,
        filename: str,
        embeddings: np.ndarray,
        metadata: Optional[Dict] = None
    ) -> Optional[Path]:
        """保存Embedding向量"""
        if not self._should_save(self._save_embeddings):
            return None
        
        # 保存numpy数组
        np_path = self.embeddings_dir / f"{filename}.embeddings.npy"
        
        try:
            np.save(np_path, embeddings)
            
            # 保存元数据
            if metadata:
                meta_path = self.embeddings_dir / f"{filename}.embeddings_meta.json"
                with open(meta_path, 'w', encoding='utf-8') as f:
                    json.dump({
                        'filename': filename,
                        'shape': embeddings.shape,
                        'timestamp': self._get_timestamp(),
                        **metadata,
                    }, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"已保存Embedding: {np_path}")
            return np_path
        except Exception as e:
            logger.error(f"保存Embedding失败: {e}")
            return None
    
    # ==================== Retriever 输出 ====================
    
    def save_retrieval_results(
        self,
        query: str,
        results: List[Dict[str, Any]],
        filename: Optional[str] = None
    ) -> Optional[Path]:
        """保存检索结果"""
        if not self._should_save(self._save_retrieval):
            return None
        
        if filename is None:
            # 使用查询的哈希作为文件名
            import hashlib
            query_hash = hashlib.md5(query.encode()).hexdigest()[:8]
            filename = f"retrieval_{query_hash}_{self._get_timestamp()}"
        
        output_path = self.retrieval_dir / f"{filename}.json"
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'query': query,
                    'result_count': len(results),
                    'timestamp': self._get_timestamp(),
                    'results': results,
                }, f, ensure_ascii=False, indent=2)
            
            logger.info(f"已保存检索结果: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"保存检索结果失败: {e}")
            return None
    
    # ==================== Evaluator 输出 ====================
    
    def save_evaluation_report(
        self,
        report: Dict[str, Any],
        filename: Optional[str] = None
    ) -> Optional[Path]:
        """保存评估报告"""
        if not self._should_save(self._save_evaluation):
            return None
        
        if filename is None:
            filename = f"eval_report_{self._get_timestamp()}"
        
        output_path = self.evaluation_dir / f"{filename}.json"
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'timestamp': self._get_timestamp(),
                    **report,
                }, f, ensure_ascii=False, indent=2)
            
            logger.info(f"已保存评估报告: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"保存评估报告失败: {e}")
            return None
    
    # ==================== 通用方法 ====================
    
    def get_output_summary(self) -> Dict[str, Any]:
        """获取输出配置摘要"""
        return {
            'mode': self.mode,
            'output_dir': str(self.output_dir),
            'save_flags': {
                'loaded': self._save_loaded,
                'cleaned': self._save_cleaned,
                'chunks': self._save_chunks,
                'dedup_report': self._save_dedup_report,
                'embeddings': self._save_embeddings,
                'retrieval': self._save_retrieval,
                'evaluation': self._save_evaluation,
            }
        }
    
    def save_failed_files_report(
        self,
        failed_files: List[Dict[str, Any]],
        filtered_files: List[Dict[str, Any]],
        filename: Optional[str] = None
    ) -> Optional[Path]:
        """
        保存失败文件报告
        
        Args:
            failed_files: 加载失败的文件列表
            filtered_files: 被过滤的文件列表
            filename: 文件名（不含扩展名）
            
        Returns:
            保存的文件路径，如果不保存则返回 None
        """
        # 失败文件报告总是保存（用于问题排查）
        if not failed_files and not filtered_files:
            return None
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if filename:
            output_file = self.output_dir / f"{filename}_failed_report_{timestamp}.json"
        else:
            output_file = self.output_dir / f"failed_files_report_{timestamp}.json"
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_failed': len(failed_files),
                'total_filtered': len(filtered_files),
                'total_issues': len(failed_files) + len(filtered_files),
            },
            'failed_files': failed_files,
            'filtered_files': filtered_files,
        }
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            logger.info(f"失败文件报告已保存: {output_file}")
            return output_file
        except Exception as e:
            logger.error(f"保存失败文件报告失败: {e}")
            return None
    
    def clean_outputs(self, confirm: bool = True) -> bool:
        """
        清理所有输出文件
        
        Args:
            confirm: 是否需要确认
            
        Returns:
            是否成功清理
        """
        if confirm:
            response = input(f"确定要清理 {self.output_dir} 下的所有输出文件吗？ (y/n): ")
            if response.lower() != 'y':
                logger.info("取消清理操作")
                return False
        
        try:
            import shutil
            if self.output_dir.exists():
                shutil.rmtree(self.output_dir)
                self._ensure_directories()
                logger.info(f"已清理输出目录: {self.output_dir}")
            return True
        except Exception as e:
            logger.error(f"清理输出目录失败: {e}")
            return False
