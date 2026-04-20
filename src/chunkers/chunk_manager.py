"""
分块管理器

负责管理文本分块的存储、检索和增量更新。
支持将分块存储到数据库，并记录文件哈希值以实现增量更新。
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from src.utils import get_logger

logger = get_logger(__name__)


class ChunkRecord:
    """分块记录"""
    
    def __init__(
        self,
        chunk_id: str,
        content: str,
        source_file: str,
        chunk_index: int,
        start_pos: int = 0,
        end_pos: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
        created_at: Optional[str] = None
    ):
        """
        初始化分块记录
        
        Args:
            chunk_id: 分块唯一ID
            content: 分块内容
            source_file: 源文件路径
            chunk_index: 分块在文件中的索引
            start_pos: 在原文中的起始位置
            end_pos: 在原文中的结束位置
            metadata: 元数据
            created_at: 创建时间
        """
        self.chunk_id = chunk_id
        self.content = content
        self.source_file = source_file
        self.chunk_index = chunk_index
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.metadata = metadata or {}
        self.created_at = created_at or datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'chunk_id': self.chunk_id,
            'content': self.content,
            'source_file': self.source_file,
            'chunk_index': self.chunk_index,
            'start_pos': self.start_pos,
            'end_pos': self.end_pos,
            'metadata': self.metadata,
            'created_at': self.created_at,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChunkRecord':
        """从字典创建"""
        return cls(
            chunk_id=data['chunk_id'],
            content=data['content'],
            source_file=data['source_file'],
            chunk_index=data['chunk_index'],
            start_pos=data.get('start_pos', 0),
            end_pos=data.get('end_pos', 0),
            metadata=data.get('metadata', {}),
            created_at=data.get('created_at'),
        )
    
    def compute_hash(self) -> str:
        """计算内容哈希值"""
        return hashlib.md5(self.content.encode('utf-8')).hexdigest()


class FileChunkRecord:
    """文件分块记录"""
    
    def __init__(
        self,
        file_path: str,
        file_hash: str,
        chunk_ids: List[str],
        processed_at: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        初始化文件分块记录
        
        Args:
            file_path: 文件路径
            file_hash: 文件内容哈希值
            chunk_ids: 该文件对应的分块ID列表
            processed_at: 处理时间
            metadata: 元数据
        """
        self.file_path = file_path
        self.file_hash = file_hash
        self.chunk_ids = chunk_ids
        self.processed_at = processed_at or datetime.now().isoformat()
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'file_path': self.file_path,
            'file_hash': self.file_hash,
            'chunk_ids': self.chunk_ids,
            'processed_at': self.processed_at,
            'metadata': self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FileChunkRecord':
        """从字典创建"""
        return cls(
            file_path=data['file_path'],
            file_hash=data['file_hash'],
            chunk_ids=data.get('chunk_ids', []),
            processed_at=data.get('processed_at'),
            metadata=data.get('metadata', {}),
        )


class ChunkDatabase:
    """分块数据库（JSON文件存储）"""
    
    def __init__(self, db_path: Union[str, Path]):
        """
        初始化分块数据库
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 数据存储
        self.chunks: Dict[str, ChunkRecord] = {}
        self.file_records: Dict[str, FileChunkRecord] = {}
        
        # 加载已有数据
        self._load()
    
    def _load(self):
        """从文件加载数据"""
        if not self.db_path.exists():
            return
        
        try:
            with open(self.db_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 加载分块记录
            for chunk_data in data.get('chunks', []):
                chunk = ChunkRecord.from_dict(chunk_data)
                self.chunks[chunk.chunk_id] = chunk
            
            # 加载文件记录
            for file_data in data.get('files', []):
                record = FileChunkRecord.from_dict(file_data)
                self.file_records[record.file_path] = record
            
            logger.info(f"已加载 {len(self.chunks)} 个分块，{len(self.file_records)} 个文件记录")
        except Exception as e:
            logger.error(f"加载分块数据库失败: {e}")
            self.chunks = {}
            self.file_records = {}
    
    def _save(self):
        """保存数据到文件"""
        try:
            data = {
                'chunks': [chunk.to_dict() for chunk in self.chunks.values()],
                'files': [record.to_dict() for record in self.file_records.values()],
                'updated_at': datetime.now().isoformat(),
            }
            
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"已保存 {len(self.chunks)} 个分块到数据库")
        except Exception as e:
            logger.error(f"保存分块数据库失败: {e}")
    
    def add_chunks(self, chunks: List[ChunkRecord], file_record: FileChunkRecord):
        """
        添加分块记录
        
        Args:
            chunks: 分块记录列表
            file_record: 文件分块记录
        """
        # 添加分块
        for chunk in chunks:
            self.chunks[chunk.chunk_id] = chunk
        
        # 更新或添加文件记录
        self.file_records[file_record.file_path] = file_record
        
        # 保存到文件
        self._save()
        
        logger.info(f"已添加 {len(chunks)} 个分块，文件: {file_record.file_path}")
    
    def get_chunks_by_file(self, file_path: str) -> List[ChunkRecord]:
        """
        获取指定文件的所有分块
        
        Args:
            file_path: 文件路径
            
        Returns:
            分块记录列表
        """
        file_record = self.file_records.get(file_path)
        if not file_record:
            return []
        
        chunks = []
        for chunk_id in file_record.chunk_ids:
            if chunk_id in self.chunks:
                chunks.append(self.chunks[chunk_id])
        
        # 按索引排序
        chunks.sort(key=lambda x: x.chunk_index)
        return chunks
    
    def get_file_record(self, file_path: str) -> Optional[FileChunkRecord]:
        """
        获取文件分块记录
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件分块记录，如果不存在则返回None
        """
        return self.file_records.get(file_path)
    
    def delete_file_chunks(self, file_path: str) -> bool:
        """
        删除指定文件的所有分块记录
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否成功删除
        """
        file_record = self.file_records.get(file_path)
        if not file_record:
            return False
        
        # 删除分块
        for chunk_id in file_record.chunk_ids:
            if chunk_id in self.chunks:
                del self.chunks[chunk_id]
        
        # 删除文件记录
        del self.file_records[file_path]
        
        # 保存
        self._save()
        
        logger.info(f"已删除文件分块记录: {file_path}")
        return True
    
    def check_file_hash(self, file_path: str, current_hash: str) -> bool:
        """
        检查文件哈希是否变化
        
        Args:
            file_path: 文件路径
            current_hash: 当前文件哈希值
            
        Returns:
            如果文件未变化返回True，否则返回False
        """
        file_record = self.file_records.get(file_path)
        if not file_record:
            return False
        
        return file_record.file_hash == current_hash
    
    def get_all_file_paths(self) -> Set[str]:
        """获取所有已记录的文件路径"""
        return set(self.file_records.keys())
    
    def get_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        return {
            'total_chunks': len(self.chunks),
            'total_files': len(self.file_records),
            'db_path': str(self.db_path),
        }


class ChunkManager:
    """分块管理器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化分块管理器
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        
        # 数据库路径
        chunker_config = self.config.get('chunker', {})
        db_path = chunker_config.get('db_path', './cache/chunks_db.json')
        self.db = ChunkDatabase(db_path)
        
        logger.info(f"分块管理器初始化完成，数据库: {db_path}")
    
    def compute_file_hash(self, file_path: Union[str, Path], algorithm: str = 'md5') -> str:
        """
        计算文件哈希值
        
        Args:
            file_path: 文件路径
            algorithm: 哈希算法 (md5/sha256)
            
        Returns:
            哈希值字符串
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        hash_obj = hashlib.md5() if algorithm == 'md5' else hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hash_obj.update(chunk)
        
        return hash_obj.hexdigest()
    
    def compute_content_hash(self, content: str, algorithm: str = 'md5') -> str:
        """
        计算内容哈希值
        
        Args:
            content: 文本内容
            algorithm: 哈希算法
            
        Returns:
            哈希值字符串
        """
        hash_obj = hashlib.md5() if algorithm == 'md5' else hashlib.sha256()
        hash_obj.update(content.encode('utf-8'))
        return hash_obj.hexdigest()
    
    def check_file_processed(self, file_path: Union[str, Path], content: Optional[str] = None) -> Tuple[bool, str]:
        """
        检查文件是否已处理且未变化
        
        Args:
            file_path: 文件路径
            content: 文件内容（如果提供则计算内容哈希，否则计算文件哈希）
            
        Returns:
            (是否已处理且未变化, 当前哈希值)
        """
        file_path = str(Path(file_path).resolve())
        
        # 计算当前哈希
        if content is not None:
            current_hash = self.compute_content_hash(content)
        else:
            current_hash = self.compute_file_hash(file_path)
        
        # 检查数据库
        is_unchanged = self.db.check_file_hash(file_path, current_hash)
        
        return is_unchanged, current_hash
    
    def store_chunks(
        self,
        file_path: Union[str, Path],
        chunks: List[Any],
        file_hash: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[ChunkRecord]:
        """
        存储分块到数据库
        
        Args:
            file_path: 源文件路径
            chunks: 分块列表（TextChunk对象）
            file_hash: 文件哈希值
            metadata: 文件元数据
            
        Returns:
            分块记录列表
        """
        file_path = str(Path(file_path).resolve())
        
        # 如果文件已存在，先删除旧记录
        if file_path in self.db.file_records:
            self.db.delete_file_chunks(file_path)
            logger.info(f"删除旧的分块记录: {file_path}")
        
        # 创建分块记录
        chunk_records = []
        chunk_ids = []
        
        for i, chunk in enumerate(chunks):
            # 生成唯一ID
            chunk_id = f"{file_path}#{i}"
            
            record = ChunkRecord(
                chunk_id=chunk_id,
                content=chunk.content,
                source_file=file_path,
                chunk_index=chunk.index,
                start_pos=chunk.start_pos,
                end_pos=chunk.end_pos,
                metadata=chunk.metadata,
            )
            
            chunk_records.append(record)
            chunk_ids.append(chunk_id)
        
        # 创建文件记录
        file_record = FileChunkRecord(
            file_path=file_path,
            file_hash=file_hash,
            chunk_ids=chunk_ids,
            metadata=metadata or {},
        )
        
        # 添加到数据库
        self.db.add_chunks(chunk_records, file_record)
        
        logger.info(f"已存储 {len(chunk_records)} 个分块，文件: {file_path}")
        return chunk_records
    
    def get_file_chunks(self, file_path: Union[str, Path]) -> List[ChunkRecord]:
        """
        获取文件的所有分块
        
        Args:
            file_path: 文件路径
            
        Returns:
            分块记录列表
        """
        file_path = str(Path(file_path).resolve())
        return self.db.get_chunks_by_file(file_path)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self.db.get_stats()
