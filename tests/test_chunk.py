"""
文本分块模块测试

测试Chunk模块的各项功能，包括分块、存储、哈希记录等
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
import tempfile
from pathlib import Path

from src.chunkers import (
    RecursiveChunker,
    ChunkManager,
    ChunkRecord,
    ChunkDatabase,
    TextChunk,
)


class TestRecursiveChunker(unittest.TestCase):
    """测试递归分块器"""
    
    def setUp(self):
        """测试前准备"""
        self.config = {
            'chunker': {
                'chunk_size': 100,
                'chunk_overlap': 20,
            }
        }
        self.chunker = RecursiveChunker(self.config)
    
    def test_basic_split(self):
        """测试基本分块功能"""
        text = "这是一段测试文本。" * 20  # 生成足够长的文本
        chunks = self.chunker.split(text)
        
        self.assertIsInstance(chunks, list)
        self.assertTrue(len(chunks) > 0)
        
        # 检查每个分块
        for i, chunk in enumerate(chunks):
            self.assertIsInstance(chunk, TextChunk)
            self.assertEqual(chunk.index, i)
            self.assertTrue(len(chunk.content) > 0)
    
    def test_empty_text(self):
        """测试空文本处理"""
        chunks = self.chunker.split("")
        self.assertEqual(len(chunks), 0)
    
    def test_metadata(self):
        """测试元数据传递"""
        text = "这是一段测试文本。" * 10
        metadata = {'source': 'test', 'author': 'tester'}
        
        chunks = self.chunker.split(text, metadata=metadata)
        
        for chunk in chunks:
            self.assertEqual(chunk.metadata.get('source'), 'test')
            self.assertEqual(chunk.metadata.get('author'), 'tester')
    
    def test_chinese_separators(self):
        """测试中文分隔符"""
        text = "第一句。第二句；第三句，第四句 第五句"
        chunks = self.chunker.split(text)
        
        # 应该根据中文标点进行分割
        self.assertIsInstance(chunks, list)


class TestChunkManager(unittest.TestCase):
    """测试分块管理器"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.config = {
            'chunker': {
                'db_path': os.path.join(self.temp_dir, 'test_chunks_db.json'),
                'chunk_size': 100,
                'chunk_overlap': 20,
            }
        }
        self.manager = ChunkManager(self.config)
        self.chunker = RecursiveChunker(self.config)
    
    def tearDown(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_compute_file_hash(self):
        """测试文件哈希计算"""
        # 创建临时文件
        temp_file = os.path.join(self.temp_dir, 'test_file.txt')
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write("测试内容")
        
        # 计算哈希
        hash1 = self.manager.compute_file_hash(temp_file)
        hash2 = self.manager.compute_file_hash(temp_file)
        
        # 相同内容应该产生相同哈希
        self.assertEqual(hash1, hash2)
        self.assertEqual(len(hash1), 32)  # MD5哈希长度为32
    
    def test_compute_content_hash(self):
        """测试内容哈希计算"""
        content = "测试内容"
        hash1 = self.manager.compute_content_hash(content)
        hash2 = self.manager.compute_content_hash(content)
        
        self.assertEqual(hash1, hash2)
        self.assertEqual(len(hash1), 32)
    
    def test_store_and_retrieve_chunks(self):
        """测试存储和检索分块"""
        # 创建测试文件
        temp_file = os.path.join(self.temp_dir, 'test_doc.txt')
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write("这是一段测试文本。" * 20)
        
        # 读取并分块
        with open(temp_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        chunks = self.chunker.split(content)
        file_hash = self.manager.compute_file_hash(temp_file)
        
        # 存储分块
        records = self.manager.store_chunks(temp_file, chunks, file_hash)
        
        self.assertEqual(len(records), len(chunks))
        
        # 检索分块
        retrieved = self.manager.get_file_chunks(temp_file)
        
        self.assertEqual(len(retrieved), len(chunks))
        
        # 检查内容是否一致
        for i, (original, retrieved_chunk) in enumerate(zip(chunks, retrieved)):
            self.assertEqual(original.content, retrieved_chunk.content)
            self.assertEqual(retrieved_chunk.chunk_index, i)
    
    def test_incremental_update(self):
        """测试增量更新"""
        # 创建测试文件
        temp_file = os.path.join(self.temp_dir, 'test_incremental.txt')
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write("原始内容")
        
        # 第一次处理
        with open(temp_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        chunks = self.chunker.split(content)
        file_hash = self.manager.compute_file_hash(temp_file)
        self.manager.store_chunks(temp_file, chunks, file_hash)
        
        # 检查文件是否已处理
        is_processed, current_hash = self.manager.check_file_processed(temp_file)
        self.assertTrue(is_processed)
        self.assertEqual(current_hash, file_hash)
        
        # 修改文件
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write("修改后的内容")
        
        # 再次检查
        is_processed, new_hash = self.manager.check_file_processed(temp_file)
        self.assertFalse(is_processed)
        self.assertNotEqual(new_hash, file_hash)
    
    def test_get_stats(self):
        """测试统计信息"""
        stats = self.manager.get_stats()
        
        self.assertIn('total_chunks', stats)
        self.assertIn('total_files', stats)
        self.assertIn('db_path', stats)


class TestChunkDatabase(unittest.TestCase):
    """测试分块数据库"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test_db.json')
        self.db = ChunkDatabase(self.db_path)
    
    def tearDown(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_add_and_get_chunks(self):
        """测试添加和获取分块"""
        # 创建分块记录
        chunks = [
            ChunkRecord(
                chunk_id='chunk_1',
                content='内容1',
                source_file='/test/file.txt',
                chunk_index=0,
            ),
            ChunkRecord(
                chunk_id='chunk_2',
                content='内容2',
                source_file='/test/file.txt',
                chunk_index=1,
            ),
        ]
        
        file_record = FileChunkRecord(
            file_path='/test/file.txt',
            file_hash='abc123',
            chunk_ids=['chunk_1', 'chunk_2'],
        )
        
        # 添加
        self.db.add_chunks(chunks, file_record)
        
        # 获取
        retrieved = self.db.get_chunks_by_file('/test/file.txt')
        
        self.assertEqual(len(retrieved), 2)
        self.assertEqual(retrieved[0].content, '内容1')
        self.assertEqual(retrieved[1].content, '内容2')
    
    def test_delete_file_chunks(self):
        """测试删除文件分块"""
        # 添加分块
        chunks = [
            ChunkRecord(
                chunk_id='chunk_1',
                content='内容1',
                source_file='/test/delete.txt',
                chunk_index=0,
            ),
        ]
        
        file_record = FileChunkRecord(
            file_path='/test/delete.txt',
            file_hash='abc123',
            chunk_ids=['chunk_1'],
        )
        
        self.db.add_chunks(chunks, file_record)
        
        # 删除
        result = self.db.delete_file_chunks('/test/delete.txt')
        self.assertTrue(result)
        
        # 验证已删除
        retrieved = self.db.get_chunks_by_file('/test/delete.txt')
        self.assertEqual(len(retrieved), 0)
    
    def test_check_file_hash(self):
        """测试文件哈希检查"""
        file_record = FileChunkRecord(
            file_path='/test/hash_check.txt',
            file_hash='abc123',
            chunk_ids=[],
        )
        
        self.db.file_records['/test/hash_check.txt'] = file_record
        
        # 相同哈希
        self.assertTrue(self.db.check_file_hash('/test/hash_check.txt', 'abc123'))
        
        # 不同哈希
        self.assertFalse(self.db.check_file_hash('/test/hash_check.txt', 'xyz789'))


# 修复导入问题
from src.chunkers.chunk_manager import FileChunkRecord


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestRecursiveChunker))
    suite.addTests(loader.loadTestsFromTestCase(TestChunkManager))
    suite.addTests(loader.loadTestsFromTestCase(TestChunkDatabase))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
