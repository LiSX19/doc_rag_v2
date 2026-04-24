"""
编码模块测试

测试编码器的各项功能
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import numpy as np

from src.encoders import DenseEncoder, SparseEncoder, HybridEncoder, EncoderManager
from src.encoders.base import EncodedVector


def test_dense_encoder():
    """测试稠密向量编码器"""
    print("\n" + "=" * 60)
    print("测试稠密向量编码器")
    print("=" * 60)
    
    config = {
        'encoder': {
            'dense': {
                'model_name': 'BAAI/bge-small-zh-v1.5',
                'device': 'cpu',
                'normalize': True,
                'batch_size': 4,
            }
        }
    }
    
    encoder = DenseEncoder(config)
    
    # 测试单条编码
    text = "这是一个测试文本，用于验证编码器功能。"
    result = encoder.encode(text, chunk_id="test_001")
    
    print(f"输入文本: {text}")
    print(f"Chunk ID: {result.chunk_id}")
    print(f"向量维度: {len(result.dense_vector)}")
    print(f"向量类型: {result.vector_type}")
    print(f"是否有稠密向量: {result.has_dense}")
    print(f"向量前5个值: {result.dense_vector[:5]}")
    
    # 测试批量编码
    texts = [
        "第一测试文本",
        "第二测试文本",
        "第三测试文本"
    ]
    chunk_ids = ["batch_001", "batch_002", "batch_003"]
    
    results = encoder.encode_batch(texts, chunk_ids)
    print(f"\n批量编码完成，编码了 {len(results)} 条文本")
    
    # 验证维度
    assert encoder.dimension > 0, "维度应该大于0"
    assert len(results) == 3, "应该返回3个结果"
    assert all(r.has_dense for r in results), "所有结果都应该有稠密向量"
    
    print("✓ 稠密向量编码器测试通过")
    return True


def test_sparse_encoder():
    """测试稀疏向量编码器"""
    print("\n" + "=" * 60)
    print("测试稀疏向量编码器")
    print("=" * 60)
    
    config = {
        'encoder': {
            'sparse': {
                'bm25': {
                    'k1': 1.5,
                    'b': 0.75,
                    'max_features': 1000,
                }
            }
        }
    }
    
    encoder = SparseEncoder(config)
    
    # 先拟合编码器
    fit_texts = [
        "这是一个用于拟合的文档",
        "这是第二个文档，包含不同的内容",
        "第三个文档用于构建词汇表"
    ]
    encoder.fit(fit_texts)
    
    # 测试单条编码
    text = "测试文档用于编码"
    result = encoder.encode(text, chunk_id="sparse_001")
    
    print(f"输入文本: {text}")
    print(f"Chunk ID: {result.chunk_id}")
    print(f"词汇表大小: {encoder.dimension}")
    print(f"向量类型: {result.vector_type}")
    print(f"是否有稀疏向量: {result.has_sparse}")
    print(f"稀疏向量非零项数: {len(result.sparse_vector) if result.sparse_vector else 0}")
    
    # 测试批量编码
    texts = ["文本一", "文本二", "文本三"]
    chunk_ids = ["s_001", "s_002", "s_003"]
    
    results = encoder.encode_batch(texts, chunk_ids)
    print(f"\n批量编码完成，编码了 {len(results)} 条文本")
    
    assert encoder.dimension > 0, "词汇表大小应该大于0"
    assert len(results) == 3, "应该返回3个结果"
    assert all(r.has_sparse for r in results), "所有结果都应该有稀疏向量"
    
    print("✓ 稀疏向量编码器测试通过")
    return True


def test_hybrid_encoder():
    """测试混合编码器"""
    print("\n" + "=" * 60)
    print("测试混合编码器")
    print("=" * 60)
    
    config = {
        'encoder': {
            'hybrid': {
                'dense_weight': 0.7,
                'sparse_weight': 0.3,
                'sparse_type': 'bm25',
                'dense_config': {
                    'model_name': 'BAAI/bge-small-zh-v1.5',
                    'device': 'cpu',
                },
                'sparse_config': {
                    'bm25': {
                        'max_features': 1000,
                    }
                }
            }
        }
    }
    
    encoder = HybridEncoder(config)
    
    # 先拟合
    fit_texts = ["文档一", "文档二", "文档三"]
    encoder.fit(fit_texts)
    
    # 测试单条编码
    text = "这是一个混合编码测试"
    result = encoder.encode(text, chunk_id="hybrid_001")
    
    print(f"输入文本: {text}")
    print(f"Chunk ID: {result.chunk_id}")
    print(f"稠密向量维度: {encoder.dimension}")
    print(f"稀疏向量维度: {encoder.sparse_dimension}")
    print(f"向量类型: {result.vector_type}")
    print(f"是否是混合向量: {result.is_hybrid}")
    print(f"有稠密向量: {result.has_dense}")
    print(f"有稀疏向量: {result.has_sparse}")
    
    # 测试批量编码
    texts = ["混合文本一", "混合文本二"]
    chunk_ids = ["h_001", "h_002"]
    
    results = encoder.encode_batch(texts, chunk_ids)
    print(f"\n批量编码完成，编码了 {len(results)} 条文本")
    
    assert result.is_hybrid, "结果应该是混合向量"
    assert len(results) == 2, "应该返回2个结果"
    
    print("✓ 混合编码器测试通过")
    return True


def test_encoder_manager():
    """测试编码管理器"""
    print("\n" + "=" * 60)
    print("测试编码管理器")
    print("=" * 60)
    
    config = {
        'encoder': {
            'type': 'dense',
            'cache_dir': './cache/test_encodings',
            'incremental': True,
            'dense': {
                'model_name': 'BAAI/bge-small-zh-v1.5',
                'device': 'cpu',
                'batch_size': 4,
            }
        }
    }
    
    manager = EncoderManager(config)
    
    # 模拟分块数据
    class MockChunk:
        def __init__(self, chunk_id, content):
            self.chunk_id = chunk_id
            self.content = content
    
    chunks = [
        MockChunk("chunk_001", "这是第一个测试分块"),
        MockChunk("chunk_002", "这是第二个测试分块"),
        MockChunk("chunk_003", "这是第三个测试分块"),
    ]
    
    print(f"准备编码 {len(chunks)} 个分块")
    
    # 编码分块
    results = manager.encode_chunks(chunks, use_cache=True)
    
    print(f"编码完成，共 {len(results)} 个结果")
    print(f"编码器类型: {manager.encoder_type}")
    
    # 测试缓存功能 - 再次编码应该使用缓存
    print("\n再次编码（应该使用缓存）...")
    results2 = manager.encode_chunks(chunks, use_cache=True)
    print(f"缓存编码完成，共 {len(results2)} 个结果")
    
    # 保存到文件
    output_path = manager.save_embeddings_to_npy(results)
    print(f"向量已保存到: {output_path}")
    
    # 验证保存的文件
    loaded = np.load(output_path)
    print(f"加载的向量形状: {loaded.shape}")
    
    assert len(results) == 3, "应该返回3个结果"
    assert loaded.shape[0] == 3, "保存的向量应该有3行"
    
    print("✓ 编码管理器测试通过")
    return True


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("编码模块测试开始")
    print("=" * 60)
    
    try:
        # 运行测试
        test_dense_encoder()
        test_sparse_encoder()
        test_hybrid_encoder()
        test_encoder_manager()
        
        print("\n" + "=" * 60)
        print("所有测试通过！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
