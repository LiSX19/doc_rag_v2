"""
Pipeline 工具模块

注意：进度追踪器 ProgressTracker 已迁移到 src/utils/progress_tracker.py
"""


def print_stats(stats: dict):
    """打印处理统计信息"""
    print("\n" + "=" * 60)
    print("处理完成统计")
    print("=" * 60)
    print(f"总文件数: {stats.get('total_files', 0)}")
    print(f"成功加载: {stats.get('loaded_files', 0)}")
    print(f"成功清洗: {stats.get('cleaned_files', 0)}")
    print(f"成功分块: {stats.get('chunked_files', 0)}")
    print(f"成功去重: {stats.get('deduped_files', 0)}")
    print(f"总分块数: {stats.get('total_chunks', 0)}")
    print(f"唯一分块数: {stats.get('unique_chunks', 0)}")
    print(f"去重分块数: {stats.get('removed_chunks', 0)}")
    print(f"编码分块数: {stats.get('encoded_chunks', 0)}")
    print(f"存储分块数: {stats.get('stored_chunks', 0)}")

    total_chunks = stats.get('total_chunks', 0)
    removed_chunks = stats.get('removed_chunks', 0)
    if total_chunks > 0:
        dedup_rate = removed_chunks / total_chunks * 100
        print(f"去重率: {dedup_rate:.1f}%")

    errors = stats.get('errors', [])
    print(f"错误数: {len(errors)}")

    if errors:
        print("\n错误详情:")
        for error in errors[:10]:
            print(f"  - {error}")
        if len(errors) > 10:
            print(f"  ... 还有 {len(errors) - 10} 个错误")
