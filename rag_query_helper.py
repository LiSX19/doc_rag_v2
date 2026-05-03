"""
RAG检索辅助脚本
用法: python rag_query_helper.py "你的问题"
"""
import sys
import os
import json
from pathlib import Path

# 确保能找到模块
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def query_rag(query: str, top_k: int = 5) -> list:
    """调用RAG系统检索相关文档"""
    from src.configs import ConfigManager
    from src.pipeline_manager import PipelineManager
    
    config_path = project_root / "config.yaml"
    config = ConfigManager(config_path=str(config_path))
    
    pipeline = PipelineManager(config)
    results = pipeline.retrieve(query=query, top_k=top_k)
    return results

if __name__ == "__main__":
    query = sys.argv[1] if len(sys.argv) > 1 else "测试查询"
    top_k = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    
    results = query_rag(query, top_k)
    
    # 输出JSON结果供调用方解析
    print(json.dumps(results, ensure_ascii=False, indent=2))
