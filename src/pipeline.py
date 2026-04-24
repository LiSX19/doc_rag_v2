"""
DocRAG Pipeline 执行模块

负责实际执行文档处理的各个阶段。
"""

from typing import Any, Dict, List, Optional
from pathlib import Path
from datetime import datetime

from src.utils import get_logger
from src.utils.task_file_manager import FileStatus
from src.utils.progress_tracker import ProgressTracker
from src.utils.log_manager import ErrorLogger, FilterLogger
from src.pipeline_stage_tracker import (
    PipelineStageTracker,
    STAGE_IDLE,
    STAGE_FILE_PROCESSING,
    STAGE_DEDUP,
    STAGE_ENCODE_STORE,
    STAGE_COMPLETE,
)

logger = get_logger(__name__)

# 模块级日志管理器实例（用于实时写入）
error_logger = ErrorLogger()
filter_logger = FilterLogger()


def build_pipeline(
    files_to_process: List[Path],
    config: Dict[str, Any],
    task_file_manager,
    loader,
    cleaner,
    chunker,
    chunk_manager,
    deduper,
    encoder_manager,
    vector_store,
    output_manager,
    is_ocr: bool = False,
    pipeline_tracker: Optional[PipelineStageTracker] = None,
) -> Dict[str, Any]:
    """
    执行构建知识库的完整流程

    Args:
        files_to_process: 待处理文件列表
        config: 配置字典
        task_file_manager: 任务文件管理器
        loader: 文档加载器
        cleaner: 文本清洗器
        chunker: 文本分块器
        chunk_manager: 分块管理器
        deduper: 去重器
        encoder_manager: 编码管理器
        vector_store: 向量数据库
        output_manager: 输出管理器
        is_ocr: 是否使用OCR清洗
        pipeline_tracker: Pipeline 阶段追踪器

    Returns:
        处理统计信息
    """
    stats = {
        'start_time': datetime.now().isoformat(),
        'total_files': len(files_to_process),
        'loaded_files': 0,
        'cleaned_files': 0,
        'chunked_files': 0,
        'deduped_files': 0,
        'total_chunks': 0,
        'unique_chunks': 0,
        'removed_chunks': 0,
        'encoded_chunks': 0,
        'stored_chunks': 0,
        'errors': [],
    }

    # 创建进度追踪器
    progress = ProgressTracker(total=len(files_to_process), desc="处理文件")

    # 阶段1: 处理每个文件（加载→清洗→分块→存储）
    print(f"\n🚀 开始处理文件...")
    print(f"   总计 {len(files_to_process)} 个文件待处理\n")

    for i, file_path in enumerate(files_to_process, 1):
        file_path = Path(file_path)
        progress.update(1, file_path.name)

        # 更新文件状态
        task_file_manager.update_file_status(file_path, FileStatus.PROCESSING)

        try:
            # 1.1 加载文档
            document = _load_document(loader, file_path, config, progress)
            if not document:
                error_msg = f"文件加载失败或为空: {file_path.name}"
                print(f"      ❌ {error_msg}")
                error_entry = {
                    'timestamp': datetime.now().isoformat(),
                    'file_path': str(file_path),
                    'module': 'loader',
                    'reason': error_msg
                }
                stats['errors'].append(error_entry)
                error_logger.append(error_entry)
                task_file_manager.update_file_status(file_path, FileStatus.ERROR, error_msg)
                continue

            stats['loaded_files'] += 1
            _save_loaded_document(output_manager, file_path, document)

            # 1.2 文本清洗
            cleaned_text = _clean_text(cleaner, document, file_path, is_ocr)
            if not cleaned_text:
                error_msg = f"清洗后文本为空: {file_path.name}"
                print(f"      ❌ {error_msg}")
                error_entry = {
                    'timestamp': datetime.now().isoformat(),
                    'file_path': str(file_path),
                    'module': 'cleaner',
                    'reason': error_msg
                }
                stats['errors'].append(error_entry)
                error_logger.append(error_entry)
                task_file_manager.update_file_status(file_path, FileStatus.ERROR, error_msg)
                continue

            stats['cleaned_files'] += 1
            _save_cleaned_document(output_manager, file_path, document, cleaned_text)

            # 1.3 文本分块
            chunks = _chunk_text(chunker, cleaned_text, document, file_path)
            if not chunks:
                error_msg = f"未生成分块: {file_path.name}"
                print(f"      ❌ {error_msg}")
                error_entry = {
                    'timestamp': datetime.now().isoformat(),
                    'file_path': str(file_path),
                    'module': 'chunker',
                    'reason': error_msg
                }
                stats['errors'].append(error_entry)
                error_logger.append(error_entry)
                task_file_manager.update_file_status(file_path, FileStatus.ERROR, error_msg)
                continue

            stats['chunked_files'] += 1
            stats['total_chunks'] += len(chunks)
            _save_chunks(output_manager, file_path, chunks)

            # 1.4 保存分块到数据库
            _store_chunks(chunk_manager, file_path, chunks)

            # 更新文件状态为完成
            task_file_manager.update_file_status(file_path, FileStatus.COMPLETED)

        except Exception as e:
            error_msg = f"处理文件失败 {file_path.name}: {str(e)}"
            print(f"      ❌ {error_msg}")
            logger.error(error_msg)
            error_entry = {
                'timestamp': datetime.now().isoformat(),
                'file_path': str(file_path),
                'module': 'pipeline',
                'reason': str(e)
            }
            stats['errors'].append(error_entry)
            error_logger.append(error_entry)
            task_file_manager.update_file_status(file_path, FileStatus.ERROR, error_msg)
            continue

    progress.close(clear_line=True)
    print(f"\n✅ 文件处理阶段完成")

    # 保存文件处理阶段状态（用于中断恢复）
    if pipeline_tracker:
        pipeline_tracker.set_stage(STAGE_FILE_PROCESSING, stats)

    # 阶段2+3: 去重 → 编码存储
    stats = _run_dedup_and_encode(
        chunk_manager=chunk_manager,
        deduper=deduper,
        encoder_manager=encoder_manager,
        vector_store=vector_store,
        stats=stats,
        pipeline_tracker=pipeline_tracker,
    )

    stats['end_time'] = datetime.now().isoformat()
    return stats


def _run_dedup_and_encode(
    chunk_manager,
    deduper,
    encoder_manager,
    vector_store,
    stats: Dict[str, Any],
    pipeline_tracker: Optional[PipelineStageTracker] = None,
) -> Dict[str, Any]:
    """执行去重和编码存储阶段（可独立调用，用于中断恢复）"""
    # 判断是否是恢复运行（去重已完成）
    current_stage = pipeline_tracker.get_stage() if pipeline_tracker else STAGE_IDLE
    dedup_already_done = current_stage in (STAGE_DEDUP, STAGE_ENCODE_STORE)

    if stats.get('chunked_files', 0) > 0:
        # 阶段2: 全局去重（仅当尚未完成时执行）
        if not dedup_already_done:
            print(f"\n🔄 正在进行全局去重...")
            dedup_result = _deduplicate_chunks(chunk_manager, deduper, stats)
            if dedup_result:
                stats.update(dedup_result)
                if pipeline_tracker:
                    pipeline_tracker.set_stage(STAGE_DEDUP, stats)
            else:
                print(f"   ⚠️  去重阶段无结果")
        else:
            all_records = chunk_manager.db.get_all_chunks()
            unique_count = len(all_records) if all_records else 0
            stats.update({
                'unique_chunks': unique_count,
                'removed_chunks': 0,
            })
            print(f"\n⏭️  去重已完成（跳过），数据库现有 {unique_count} 个唯一分块")

        # 阶段3: 编码并存储唯一分块到向量数据库
        if stats.get('unique_chunks', 0) > 0:
            print(f"\n🧠 正在编码并存储唯一分块到向量数据库...")
            encode_result = _encode_and_store(chunk_manager, encoder_manager, vector_store, stats, pipeline_tracker=pipeline_tracker)
            if encode_result:
                stats.update(encode_result)
                if pipeline_tracker:
                    pipeline_tracker.set_stage(STAGE_ENCODE_STORE, stats)
                print(f"   ✅ 向量数据库存储完成: 存储了 {encode_result.get('stored_chunks', 0)} 个唯一分块")
            else:
                print(f"   ⚠️  编码存储阶段未存储任何分块")
        else:
            print(f"   ⚠️  没有唯一分块需要存储")
    else:
        print(f"   ⚠️  没有分块需要去重，跳过全局去重和编码存储")

    if pipeline_tracker:
        pipeline_tracker.set_stage(STAGE_COMPLETE, stats)

    return stats


def _remove_duplicates_from_vector_store(vector_store, removed_chunks: List):
    """从向量数据库中删除重复的分块"""
    if not removed_chunks:
        return

    try:
        ids_to_remove = []
        for chunk in removed_chunks:
            if hasattr(chunk, 'source_file') and hasattr(chunk, 'chunk_index'):
                chunk_id = f"{chunk.source_file}_{chunk.chunk_index}"
                ids_to_remove.append(chunk_id)

        if ids_to_remove:
            vector_store.delete(ids=ids_to_remove)
            logger.info(f"从向量数据库删除 {len(ids_to_remove)} 个重复分块")
    except Exception as e:
        logger.warning(f"从向量数据库删除重复分块失败: {e}")


def _load_document(loader, file_path: Path, config: Dict, progress) -> Optional[Dict]:
    """加载单个文档"""
    if file_path.suffix.lower() == '.pdf':
        from src.loaders import DocumentLoader
        config_dict = config.copy()
        config_dict['ocr'] = config_dict.get('ocr', {})

        def ocr_progress_callback(current, total, message):
            progress.set_sub_progress(desc="OCR识别", current=current, total=total, message=message)

        config_dict['ocr']['progress_callback'] = ocr_progress_callback
        temp_loader = DocumentLoader(config_dict)
        document = temp_loader.load_document(file_path)
        progress.clear_sub_progress()
    else:
        document = loader.load_document(file_path)

    return document if document and document.get('content') else None


def _save_loaded_document(output_manager, file_path: Path, document: Dict):
    """保存加载的文档"""
    try:
        output_manager.save_loaded_document(
            filename=file_path.stem,
            content=document.get('content', ''),
            metadata=document.get('metadata', {})
        )
    except Exception as e:
        logger.warning(f"保存加载文档失败: {file_path.name}, 错误: {e}")


def _clean_text(cleaner, document: Dict, file_path: Path, is_ocr: bool) -> Optional[str]:
    """清洗文本"""
    cleaned_text = cleaner.clean(
        document.get('content', ''),
        filename=file_path.stem,
        is_ocr=is_ocr
    )
    return cleaned_text if cleaned_text else None


def _save_cleaned_document(output_manager, file_path: Path, document: Dict, cleaned_text: str):
    """保存清洗后的文档"""
    try:
        output_manager.save_cleaned_text(
            filename=file_path.stem,
            original_content=document.get('content', ''),
            cleaned_content=cleaned_text,
            metadata={'pipeline': ['structure', 'encoding', 'simplified']}
        )
    except Exception as e:
        logger.warning(f"保存清洗文档失败: {file_path.name}, 错误: {e}")


def _chunk_text(chunker, cleaned_text: str, document: Dict, file_path: Path) -> Optional[List]:
    """分块文本"""
    chunks = chunker.split(cleaned_text, metadata=document.get('metadata', {}))
    return chunks if chunks else None


def _save_chunks(output_manager, file_path: Path, chunks: List):
    """保存分块结果"""
    try:
        chunks_data = [
            {
                'index': chunk.index,
                'content': chunk.content,
                'start_pos': chunk.start_pos,
                'end_pos': chunk.end_pos,
                'metadata': chunk.metadata
            }
            for chunk in chunks
        ]
        output_manager.save_chunks(file_path.stem, chunks_data)
    except Exception as e:
        logger.warning(f"保存分块结果失败: {file_path.name}, 错误: {e}")


def _store_chunks(chunk_manager, file_path: Path, chunks: List):
    """存储分块到数据库"""
    from src.utils.file_utils import FileUtils

    try:
        content_hash = FileUtils.calculate_file_hash(file_path, 'md5')
        chunk_manager.store_chunks(
            file_path=file_path,
            chunks=chunks,
            file_hash=content_hash,
            metadata={'processed_at': datetime.now().isoformat(), 'chunk_count': len(chunks)}
        )
    except Exception as e:
        logger.error(f"存储分块到数据库失败: {file_path.name}, 错误: {e}")
        raise


def _deduplicate_chunks(chunk_manager, deduper, stats: Dict) -> Optional[Dict]:
    """执行全局去重（带进度条）"""
    print(f"   📂 正在加载全部分块记录...", end=' ', flush=True)
    all_chunk_records = chunk_manager.db.get_all_chunks()
    if not all_chunk_records:
        print(f"❌ 无分块记录")
        return None
    print(f"✅ ({len(all_chunk_records)} 个分块)")

    from src.chunkers.base import TextChunk
    all_chunks = []
    hash_compute_count = 0

    # 去重进度条
    dedup_progress = ProgressTracker(total=len(all_chunk_records), desc="  去重进度")
    for i, record in enumerate(all_chunk_records):
        chunk = TextChunk(
            index=record.chunk_index,
            content=record.content,
            start_pos=record.start_pos,
            end_pos=record.end_pos,
            metadata=record.metadata
        )
        chunk.chunk_id = record.chunk_id
        chunk.source_file = record.source_file
        chunk.content_hash = getattr(record, 'content_hash', None)
        if chunk.content_hash is None:
            import hashlib
            chunk.content_hash = hashlib.md5(chunk.content.encode('utf-8')).hexdigest()
            hash_compute_count += 1
        all_chunks.append(chunk)

        dedup_progress.update(1)

    dedup_progress.close(clear_line=True)

    if hash_compute_count > 0:
        print(f"   🔑 计算了 {hash_compute_count} 个缺失的哈希值")

    # 保存持久化哈希表（用于增量更新时判断新文件与旧文件是否重复）
    saved_hashes = deduper.seen_hashes.copy()
    # 清空：在当前批内进行去重，只比较所有分块间的重复
    deduper.seen_hashes.clear()
    dedup_result = deduper.deduplicate(all_chunks, filename="global")
    # 恢复并更新持久化哈希表：保留旧哈希 + 新增唯一分块的哈希
    deduper.seen_hashes = saved_hashes | {chunk.content_hash for chunk in dedup_result.chunks if hasattr(chunk, 'content_hash') and chunk.content_hash}
    deduper._save_hash_table()

    removed_chunk_ids = [chunk.chunk_id for chunk in dedup_result.removed_chunks if hasattr(chunk, 'chunk_id')]
    if removed_chunk_ids:
        chunk_manager.db.delete_chunks_by_ids(removed_chunk_ids)
        print(f"   🗑️  已删除 {len(removed_chunk_ids)} 个重复分块")

    total_before = len(all_chunk_records)
    total_after = total_before - len(removed_chunk_ids)
    print(f"   ✅ 去重完成: {total_before} → {total_after} 个唯一分块 (移除 {len(removed_chunk_ids)} 个)")

    return {
        'deduped_files': stats['chunked_files'],
        'unique_chunks': total_after,
        'removed_chunks': len(dedup_result.removed_chunks)
    }


def _encode_and_store(
    chunk_manager,
    encoder_manager,
    vector_store,
    stats: Dict,
    pipeline_tracker: Optional[PipelineStageTracker] = None,
) -> Optional[Dict]:
    """编码分块并分批存储到向量数据库（支持断点续传，带进度条）"""
    all_chunk_records = chunk_manager.db.get_all_chunks()
    if not all_chunk_records:
        return None

    existing_ids = set()
    try:
        existing_ids = set(vector_store.get_existing_ids())
        if existing_ids:
            print(f"   📋 检测到 {len(existing_ids)} 个已存储的分块，跳过...")
    except Exception:
        pass

    records_to_encode = []
    for record in all_chunk_records:
        chunk_id = f"{record.source_file}_{record.chunk_index}"
        if chunk_id not in existing_ids:
            records_to_encode.append(record)

    if not records_to_encode:
        print(f"   ✅ 所有分块已存储，无需编码")
        return {
            'encoded_chunks': len(all_chunk_records),
            'stored_chunks': len(all_chunk_records),
        }

    total = len(records_to_encode)
    batch_size = 32
    total_batches = (total + batch_size - 1) // batch_size
    all_encoded = []
    stored_count = 0

    # 编码存储进度条
    encode_progress = ProgressTracker(total=total, desc="  编码存储")

    for batch_idx in range(0, total, batch_size):
        batch_records = records_to_encode[batch_idx:batch_idx + batch_size]
        batch_num = batch_idx // batch_size + 1

        encoded = encoder_manager.encode_chunks(batch_records, use_cache=True)
        if not encoded:
            print(f"      ⚠️  批次 {batch_num}/{total_batches} 编码失败，跳过")
            encode_progress.update(len(batch_records))
            continue
        all_encoded.extend(encoded)

        texts = []
        embeddings = []
        metadatas = []
        ids = []

        for record, encoded_vec in zip(batch_records, encoded):
            chunk_id = f"{record.source_file}_{record.chunk_index}"
            texts.append(record.content)

            if hasattr(encoded_vec, 'dense_vector') and encoded_vec.dense_vector is not None:
                embeddings.append(encoded_vec.dense_vector)
            else:
                embeddings.append(encoded_vec)

            metadata = {
                'source': str(record.source_file),
                'chunk_index': int(record.chunk_index),
                'start_pos': int(record.start_pos),
                'end_pos': int(record.end_pos),
            }
            if record.metadata:
                for key, value in record.metadata.items():
                    if isinstance(value, (str, int, float, bool)):
                        metadata[key] = value
                    elif isinstance(value, (list, tuple)) and len(value) > 0 and isinstance(value[0], (str, int, float, bool)):
                        metadata[key] = list(value)[:10]
            metadatas.append(metadata)
            ids.append(chunk_id)

        try:
            vector_store.add(contents=texts, embeddings=embeddings, metadatas=metadatas, ids=ids)
            stored_count += len(texts)
        except Exception as e:
            logger.error(f"批次 {batch_num}/{total_batches} 存储失败: {e}")
            encode_progress.update(len(batch_records))
            continue

        if pipeline_tracker:
            progress_stats = dict(stats)
            progress_stats['encoded_chunks'] = stored_count
            progress_stats['stored_chunks'] = stored_count
            pipeline_tracker.set_stage(STAGE_ENCODE_STORE, progress_stats)

        encode_progress.update(len(batch_records))

    encode_progress.close(clear_line=True)

    if all_encoded:
        try:
            encoder_manager.save_embeddings_to_npy(all_encoded)
        except Exception as e:
            logger.warning(f"保存编码结果到文件失败: {e}")

    return {
        'encoded_chunks': len(all_encoded),
        'stored_chunks': stored_count,
    }
