"""
DocRAG - 文档RAG系统主程序入口

使用方法:
    python -m src.main [命令] [参数]
    python src/main.py [命令] [参数]

命令:
    build       构建知识库（文件→加载→清洗→分块→存储）
    retrieve    检索知识库
    evaluate    评估RAG系统
    init        初始化项目配置
    status      显示系统状态
    clean       清理临时文件和缓存
    export      导出向量数据库
"""

import json
import os
import sys

# Windows ANSI支持
if sys.platform == 'win32':
    os.system('color')

import click
from pathlib import Path
from typing import Optional
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.configs import ConfigManager
from src.utils import get_logger, setup_logging
from src.pipeline_manager import PipelineManager
from src.pipeline_utils import print_stats

logger = get_logger(__name__)


@click.group()
@click.option('--config', '-c', type=click.Path(exists=True), help='配置文件路径')
@click.option('--verbose', '-v', is_flag=True, help='详细输出模式')
@click.option('--log-level', type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR']), default=None)
@click.option('--log-dir', type=click.Path(), help='日志目录')
@click.pass_context
def cli(ctx, config, verbose, log_level, log_dir):
    """DocRAG - 文档RAG系统"""
    ctx.ensure_object(dict)

    # 加载配置
    config_manager = ConfigManager(config_path=config)
    ctx.obj['config'] = config_manager
    ctx.obj['verbose'] = verbose

    # 设置日志
    effective_log_level = log_level or config_manager.get('logging.level', 'INFO')
    ctx.obj['log_level'] = effective_log_level

    effective_log_dir = log_dir or config_manager.get('paths.logs_dir', './logs')
    log_dir_path = Path(effective_log_dir)
    log_dir_path.mkdir(parents=True, exist_ok=True)
    log_file = log_dir_path / f"doc_rag_{datetime.now().strftime('%Y%m%d')}.log"
    ctx.obj['log_dir'] = str(log_dir_path)

    console_output = config_manager.get('logging.console_output', True)
    console_level = config_manager.get('logging.console_level', effective_log_level)

    if verbose:
        console_output = True
        console_level = "DEBUG"

    setup_logging(
        level=effective_log_level,
        format_type="simple" if verbose else "structured",
        log_file=str(log_file),
        console_output=console_output,
        console_level=console_level
    )

    if verbose:
        logger.info("启用详细输出模式")
        logger.info(f"日志文件: {log_file}")


@cli.command()
@click.option('--input-dir', '-i', type=click.Path(exists=True), help='输入文件夹路径')
@click.option('--file-limit', type=int, help='文件数量限制')
@click.option('--incremental/--full', default=True, help='增量更新模式/全量更新模式')
@click.option('--ocr/--no-ocr', default=False, help='使用OCR清洗模式')
@click.option('--output-dir', '-o', type=click.Path(), help='输出目录路径')
@click.option('--interactive/--no-interactive', '-I', default=False, help='使用交互式配置模式')
@click.option('--output-mode', '-m', type=click.Choice(['test', 'production', 'minimal', 'custom']))
@click.option('--output-loaded/--no-output-loaded', default=None)
@click.option('--output-cleaned/--no-output-cleaned', default=None)
@click.option('--output-chunks/--no-output-chunks', default=None)
@click.option('--output-dedup/--no-output-dedup', default=None)
@click.option('--rebuild', is_flag=True, help='强制重建向量数据库')
@click.pass_context
def build(ctx, input_dir, file_limit, incremental, ocr, output_dir, interactive,
          output_mode, output_loaded, output_cleaned, output_chunks, output_dedup,
          rebuild):
    """构建知识库：文件→加载→清洗→分块→去重→编码→存储"""
    config = ctx.obj['config']
    verbose = ctx.obj.get('verbose', False)

    # 交互式配置
    if interactive:
        from src.utils.interactive_config import interactive_config
        user_config = interactive_config(config.get_all())
        if user_config.get('paths.input_dir'):
            input_dir = user_config.get('paths.input_dir')
        if user_config.get('paths.output_dir'):
            output_dir = user_config.get('paths.output_dir')

    # 更新配置
    if input_dir:
        config.set('paths.input_dir', input_dir)
    if output_dir:
        config.set('paths.output_dir', output_dir)

    # 处理输出模式
    if output_mode:
        config.set('output.mode', output_mode)

    if output_mode == 'custom' or any(x is not None for x in [output_loaded, output_cleaned, output_chunks, output_dedup]):
        config.set('output.mode', 'custom')
        if output_loaded is not None:
            config.set('output.stages.loaded', output_loaded)
        if output_cleaned is not None:
            config.set('output.stages.cleaned', output_cleaned)
        if output_chunks is not None:
            config.set('output.stages.chunks', output_chunks)
        if output_dedup is not None:
            config.set('output.stages.dedup_report', output_dedup)



    if verbose:
        print("=" * 60)
        print("开始构建知识库")
        print("=" * 60)
        print(f"输入目录: {config.get('paths.input_dir')}")
        print(f"输出目录: {config.get('paths.output_dir')}")
        print(f"增量更新: {'是' if incremental else '否'}")
        print(f"OCR模式: {'是' if ocr else '否'}")
        print(f"强制重建: {'是' if rebuild else '否'}")
        print()

    try:
        # 创建Pipeline管理器并执行构建
        pipeline = PipelineManager(config)

        # 如果需要强制重建，清空向量数据库
        if rebuild:
            import shutil
            chroma_db_path = Path('./chroma_db')
            if chroma_db_path.exists():
                shutil.rmtree(chroma_db_path)
                print("已清空向量数据库")

        stats = pipeline.build_knowledge_base(
            input_dir=input_dir,
            file_limit=file_limit,
            incremental=incremental,
            is_ocr=ocr,
            force_rebuild=rebuild
        )

        # 打印统计信息
        if stats.get('status') == 'error':
            print(f"\n错误: {stats.get('message')}")
            return

        if stats.get('status') == 'success' and stats.get('message') == '没有需要处理的文件':
            print(f"\n{stats.get('message')}")
            if stats.get('vector_store_has_data'):
                print("向量数据库已有数据，可直接使用 retrieve 命令进行检索")
            return

        # 打印详细统计
        print_stats(stats)

        if verbose or stats.get('errors'):
            print("\n" + "=" * 60)
            print("知识库构建完成")
            print("=" * 60)

    except Exception as e:
        logger.error(f"构建知识库时出错: {e}")
        raise click.ClickException(str(e))


@cli.command()
@click.option('--query', '-q', required=True, help='查询问题')
@click.option('--top-k', '-k', type=int, default=5, help='返回结果数量')
@click.option('--threshold', '-t', type=float, default=None, help='相似度阈值')
@click.option('--output-format', type=click.Choice(['json', 'text']), default='text')
@click.option('--save/--no-save', default=True, help='是否保存检索结果')
@click.pass_context
def retrieve(ctx, query, top_k, threshold, output_format, save):
    """检索知识库，获取相关文档片段"""
    config = ctx.obj['config']
    verbose = ctx.obj.get('verbose', False)

    print("=" * 60)
    print(f"检索查询: {query}")
    print("=" * 60)

    try:
        pipeline = PipelineManager(config)

        # 检查向量数据库
        collection_count = pipeline.vector_store.collection.count()
        print(f"向量数据库中共有 {collection_count} 个文档片段")

        if collection_count == 0:
            print("\n警告: 向量数据库为空，请先运行 'build' 命令构建知识库")
            return

        print(f"检索参数: top_k={top_k}")
        if threshold:
            print(f"相似度阈值: {threshold}")
        print("-" * 60)

        # 执行检索
        result = pipeline.retrieve(query, top_k=top_k, threshold=threshold)

        if result.get('status') == 'error':
            print(f"\n错误: {result.get('message')}")
            return

        results = result.get('results', [])

        # 保存结果
        if save and results:
            pipeline.output_manager.save_retrieval_results(
                query=query,
                results=results
            )

        # 输出结果
        if not results:
            print("\n未找到相关文档片段")
            return

        if output_format == 'json':
            output = json.dumps(results, ensure_ascii=False, indent=2)
        else:
            output = f"\n检索结果 ({len(results)} 条):\n"
            output += "-" * 60 + "\n"
            for i, r in enumerate(results, 1):
                source = r.get('metadata', {}).get('source', '未知来源')
                score = r.get('score', 0)
                content = r.get('content', '')
                output += f"[{i}] 相似度: {score:.4f} | 来源: {source}\n"
                content_preview = content[:300] if len(content) > 300 else content
                output += f"    内容: {content_preview}\n"
                if len(content) > 300:
                    output += f"    ... (共 {len(content)} 字符)\n"
                output += "-" * 60 + "\n"

        click.echo(output)

    except Exception as e:
        logger.error(f"检索时出错: {e}")
        raise click.ClickException(str(e))


@cli.command()
@click.pass_context
def status(ctx):
    """显示系统状态"""
    config = ctx.obj['config']

    print("=" * 60)
    print("系统状态")
    print("=" * 60)

    try:
        pipeline = PipelineManager(config)

        # 分块数据库统计
        chunk_stats = pipeline.chunk_manager.get_stats()
        print("\n分块数据库:")
        print(f"  总分块数: {chunk_stats.get('total_chunks', 0)}")

        # 向量数据库统计
        try:
            vector_count = pipeline.vector_store.collection.count()
            print(f"\n向量数据库:")
            print(f"  文档片段数: {vector_count}")
        except Exception:
            print(f"\n向量数据库: 未初始化")

        # 任务文件表统计
        task_stats = pipeline.task_file_manager.get_statistics()
        print(f"\n任务文件表:")
        print(f"  总文件数: {task_stats.get('total', 0)}")
        print(f"  已完成: {task_stats.get('completed', 0)}")
        print(f"  处理中: {task_stats.get('processing', 0)}")
        print(f"  待处理: {task_stats.get('pending', 0)}")
        print(f"  出错: {task_stats.get('error', 0)}")

    except Exception as e:
        logger.error(f"获取系统状态时出错: {e}")
        raise click.ClickException(str(e))


@cli.command()
@click.option('--yes', '-y', is_flag=True, help='确认操作，不提示')
@click.option('--cache', is_flag=True, help='清理缓存目录')
@click.option('--output', is_flag=True, help='清理输出目录')
@click.option('--vector-db', is_flag=True, help='清理向量数据库')
@click.option('--all', 'clean_all', is_flag=True, help='清理所有（默认行为）')
@click.option('--reset-progress', is_flag=True, help='重置进度记录')
@click.option('--clear-errors', is_flag=True, help='清除错误记录')
@click.pass_context
def clean(ctx, yes, cache, output, vector_db, clean_all, reset_progress, clear_errors):
    """清理临时文件和缓存

    示例:
        python -m src.main clean              # 清理所有，交互式确认
        python -m src.main clean --yes        # 清理所有，直接确认
        python -m src.main clean --cache      # 仅清理缓存
        python -m src.main clean --vector-db  # 仅清理向量数据库
        python -m src.main clean --reset-progress  # 仅重置进度
    """
    # 如果没有指定具体清理项，默认清理所有
    if not any([cache, output, vector_db, reset_progress, clear_errors]):
        clean_all = True

    # 确认操作
    if not yes:
        if clean_all:
            click.confirm('确定要清理所有缓存和临时文件吗？', abort=True)
        else:
            click.confirm('确定要执行指定的清理操作吗？', abort=True)

    try:
        import shutil

        cleaned_items = []

        # 清理缓存目录
        if clean_all or cache:
            cache_dir = Path('./cache')
            if cache_dir.exists():
                shutil.rmtree(cache_dir)
                cleaned_items.append("缓存目录")

        # 清理输出目录
        if clean_all or output:
            output_dir = Path('./outputs')
            if output_dir.exists():
                shutil.rmtree(output_dir)
                cleaned_items.append("输出目录")

        # 清理向量数据库
        if clean_all or vector_db:
            chroma_db = Path('./chroma_db')
            if chroma_db.exists():
                shutil.rmtree(chroma_db)
                cleaned_items.append("向量数据库")

        # 重置进度记录
        if clean_all or reset_progress:
            from src.utils.incremental_tracker import IncrementalTracker
            tracker = IncrementalTracker(ctx.obj['config'].get_all())
            tracker.clear_progress()
            cleaned_items.append("进度记录")

        # 清除错误记录
        if clean_all or clear_errors:
            from src.utils.incremental_tracker import IncrementalTracker
            tracker = IncrementalTracker(ctx.obj['config'].get_all())
            tracker.clear_error_records()
            cleaned_items.append("错误记录")

        # 打印结果
        if cleaned_items:
            print("\n已清理以下项目:")
            for item in cleaned_items:
                print(f"  ✓ {item}")
            print("\n清理完成")
        else:
            print("\n没有需要清理的项目")

    except Exception as e:
        logger.error(f"清理时出错: {e}")
        raise click.ClickException(str(e))


if __name__ == '__main__':
    cli()
