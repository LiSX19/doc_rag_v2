"""
递归文本分块器

基于LangChain的RecursiveCharacterTextSplitter实现，
针对中文进行了优化。
"""

from typing import Any, Dict, List, Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter
from src.utils import OutputManager, get_logger

from .base import BaseChunker, TextChunk

logger = get_logger(__name__)


class RecursiveChunker(BaseChunker):
    """递归文本分块器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化递归分块器
        
        Args:
            config: 配置字典，包含：
                - chunk_size: 块大小（默认500）
                - chunk_overlap: 重叠长度（默认50）
                - separators: 分隔符列表
        """
        super().__init__(config)
        
        # 读取 chunker 配置（适配 configs.yaml 结构）
        chunker_config = self.config.get('chunker', self.config)
        
        self.chunk_size = chunker_config.get('chunk_size', 500)
        self.chunk_overlap = chunker_config.get('chunk_overlap', 50)
        
        # 中文优化的分隔符
        self.separators = chunker_config.get('separators', [
            "\n\n",  # 段落
            "\n",    # 换行
            "。",     # 句号
            "；",    # 分号
            "，",    # 逗号
            " ",     # 空格
            "",      # 字符
        ])
        
        # 初始化LangChain分割器
        self.splitter = RecursiveCharacterTextSplitter(
            separators=self.separators,
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            is_separator_regex=False,
        )
        
        # 输出管理器
        self.output_manager = OutputManager(config)
    
    def split(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[TextChunk]:
        """
        分割文本
        
        Args:
            text: 原始文本
            metadata: 文档元数据
            
        Returns:
            文本块列表
        """
        if not text:
            return []
        
        # 使用LangChain分割器
        docs = self.splitter.create_documents([text])
        
        chunks = []
        current_pos = 0
        
        for i, doc in enumerate(docs):
            content = doc.page_content
            
            # 查找内容在原文中的位置
            start_pos = text.find(content, current_pos)
            if start_pos == -1:
                start_pos = current_pos
            end_pos = start_pos + len(content)
            current_pos = end_pos - self.chunk_overlap
            
            # 合并元数据
            chunk_metadata = metadata.copy() if metadata else {}
            chunk_metadata.update(doc.metadata)
            
            chunk = TextChunk(
                content=content,
                index=i,
                metadata=chunk_metadata,
                start_pos=start_pos,
                end_pos=end_pos,
            )
            chunks.append(chunk)
        
        # 后处理：过滤短块、合并相邻短块
        chunks = self._post_process(chunks)
        
        return chunks
    
    def split_and_save(
        self,
        text: str,
        filename: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[TextChunk]:
        """
        分割文本并保存结果
        
        Args:
            text: 原始文本
            filename: 文件名（用于保存输出）
            metadata: 文档元数据
            
        Returns:
            文本块列表
        """
        chunks = self.split(text, metadata)
        
        # 保存分块结果
        if chunks:
            chunk_data = [
                {
                    'index': c.index,
                    'content': c.content,
                    'start_pos': c.start_pos,
                    'end_pos': c.end_pos,
                    'metadata': c.metadata,
                }
                for c in chunks
            ]
            self.output_manager.save_chunks(filename, chunk_data)
        
        return chunks
    
    def _post_process(self, chunks: List[TextChunk]) -> List[TextChunk]:
        """
        后处理：过滤短块、合并相邻短块
        
        Args:
            chunks: 原始文本块列表
            
        Returns:
            处理后的文本块列表
        """
        if not chunks:
            return chunks
        
        # 读取 chunker 配置（适配 configs.yaml 结构）
        chunker_config = self.config.get('chunker', self.config)
        post_process_config = chunker_config.get('post_process', {})
        
        min_length = post_process_config.get('min_chunk_length', 20)
        merge_short = post_process_config.get('merge_adjacent_short', True)
        
        # 过滤过短的块
        if post_process_config.get('filter_short_chunks', True):
            chunks = [c for c in chunks if len(c.content) >= min_length]
        
        # 合并相邻的短块
        if merge_short and len(chunks) > 1:
            merged = []
            current = chunks[0]
            
            for next_chunk in chunks[1:]:
                if len(current.content) < min_length:
                    # 合并到当前块
                    current.content += "\n" + next_chunk.content
                    current.end_pos = next_chunk.end_pos
                else:
                    merged.append(current)
                    current = next_chunk
            
            merged.append(current)
            chunks = merged
        
        # 重新编号
        for i, chunk in enumerate(chunks):
            chunk.index = i
        
        return chunks
