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
import click
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.configs import ConfigManager
from src.utils import get_logger, setup_logging, OutputManager
from src.utils.file_utils import FileUtils
from src.utils.incremental_tracker import IncrementalTracker

# 初始化日志（将在cli中重新配置）
logger = get_logger(__name__)


class ProgressBar:
    """简单的进度条实现"""
    
    def __init__(self, total: int, desc: str = "处理中", bar_length: int = 40, enabled: bool = True):
        """
        初始化进度条
        
        Args:
            total: 总任务数
            desc: 描述文本
            bar_length: 进度条长度
            enabled: 是否启用
        """
        self.total = total
        self.desc = desc
        self.bar_length = bar_length
        self.enabled = enabled
        self.current = 0
        self.start_time = datetime.now()
        
    def update(self, n: int = 1, current_item: str = ""):
        """
        更新进度
        
        Args:
            n: 进度增量
            current_item: 当前处理项名称
        """
        if not self.enabled:
            return
            
        self.current += n
        progress = self.current / self.total if self.total > 0 else 1.0
        filled = int(self.bar_length * progress)
        bar = '█' * filled + '░' * (self.bar_length - filled)
        percentage = progress * 100
        
        # 计算耗时和预估剩余时间
        elapsed = (datetime.now() - self.start_time).total_seconds()
        if self.current > 0:
            avg_time = elapsed / self.current
            remaining = avg_time * (self.total - self.current)
            time_str = f"耗时: {self._format_time(elapsed)} | 剩余: {self._format_time(remaining)}"
        else:
            time_str = f"耗时: {self._format_time(elapsed)}"
        
        # 截断当前项名称
        item_str = current_item[:30] if current_item else ""
        
        # 输出进度条
        sys.stdout.write(f"\r{self.desc}: [{bar}] {percentage:5.1f}% ({self.current}/{self.total}) {time_str}")
        if item_str:
            sys.stdout.write(f" | 当前: {item_str:<30}")
        sys.stdout.flush()
    
    def close(self, message: str = ""):
        """关闭进度条"""
        if not self.enabled:
            return
            
        sys.stdout.write("\n")
        if message:
            sys.stdout.write(f"{message}\n")
        sys.stdout.flush()
    
    def _format_time(self, seconds: float) -> str:
        """格式化时间显示"""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            return f"{seconds/60:.1f}m"
        else:
            return f"{seconds/3600:.1f}h"


class DocRAGPipeline:
    """DocRAG处理流程"""

    def __init__(self, config: ConfigManager, verbose: bool = False):
        """
        初始化处理流程

        Args:
            config: 配置管理器
            verbose: 是否显示详细信息
        """
        self.config = config
        self.verbose = verbose
        self.output_manager = OutputManager(config.get_all())

        # 初始化各模块（懒加载）
        self._loader = None
        self._cleaner = None
        self._chunker = None
        self._chunk_manager = None
        self._incremental_tracker = None

    @property
    def loader(self):
        """获取文档加载器"""
        if self._loader is None:
            from src.loaders import DocumentLoader
            self._loader = DocumentLoader(self.config.get_all())
        return self._loader

    @property
    def cleaner(self):
        """获取文本清洗器"""
        if self._cleaner is None:
            from src.cleaners import TextCleaner
            self._cleaner = TextCleaner(self.config.get_all())
        return self._cleaner

    @property
    def chunker(self):
        """获取文本分块器"""
        if self._chunker is None:
            from src.chunkers import RecursiveChunker
            self._chunker = RecursiveChunker(self.config.get_all())
        return self._chunker

    @property
    def chunk_manager(self):
        """获取分块管理器"""
        if self._chunk_manager is None:
            from src.chunkers import ChunkManager
            self._chunk_manager = ChunkManager(self.config.get_all())
        return self._chunk_manager

    @property
    def incremental_tracker(self):
        """获取增量更新追踪器"""
        if self._incremental_tracker is None:
            self._incremental_tracker = IncrementalTracker(self.config.get_all())
        return self._incremental_tracker

    def scan_directory(self, input_dir: str) -> List[Path]:
        """
        扫描目录获取所有支持的文件

        Args:
            input_dir: 输入目录

        Returns:
            文件路径列表
        """
        from src.loaders import LoaderFactory

        input_path = Path(input_dir)
        if not input_path.exists():
            raise FileNotFoundError(f"输入目录不存在: {input_dir}")

        # 获取支持的扩展名
        supported_extensions = LoaderFactory.get_supported_extensions()

        # 扫描文件
        files = FileUtils.list_files(input_path, supported_extensions, recursive=True)

        return files

    def process_files(
        self,
        input_dir: Optional[str] = None,
        file_limit: Optional[int] = None,
        incremental: bool = True,
        is_ocr: bool = False
    ) -> Dict[str, Any]:
        """
        处理文件完整流程：加载→清洗→分块→存储

        Args:
            input_dir: 输入目录
            file_limit: 文件数量限制
            incremental: 是否增量更新
            is_ocr: 是否使用OCR清洗

        Returns:
            处理统计信息
        """
        stats = {
            'start_time': datetime.now().isoformat(),
            'total_files': 0,
            'loaded_files': 0,
            'cleaned_files': 0,
            'chunked_files': 0,
            'total_chunks': 0,
            'errors': [],
        }

        try:
            # ========== 步骤1: 文档加载 ==========
            input_path = input_dir or self.config.get('paths.input_dir', './data')

            # 扫描文件
            all_files = self.scan_directory(input_path)
            stats['total_files'] = len(all_files)

            # 增量更新筛选
            if incremental:
                files_to_process, filter_stats = self.incremental_tracker.filter_files(all_files)
            else:
                files_to_process = all_files

            # 应用文件数量限制
            if file_limit and len(files_to_process) > file_limit:
                files_to_process = files_to_process[:file_limit]

            if not files_to_process:
                print("没有需要处理的文件，流程结束")
                stats['end_time'] = datetime.now().isoformat()
                return stats
            
            print(f"扫描到 {len(all_files)} 个文件，需要处理 {len(files_to_process)} 个")
            print("=" * 60)

            # ========== 步骤2: 处理每个文件 ==========
            total_files = len(files_to_process)
            
            # 创建进度条（在非verbose模式下也显示）
            progress_bar = ProgressBar(
                total=total_files,
                desc="处理文件",
                enabled=True  # 始终显示进度条
            )
            
            for i, file_path in enumerate(files_to_process, 1):
                file_path = Path(file_path)
                
                # 更新进度条
                progress_bar.update(1, file_path.name)
                
                try:
                    # 2.1 加载文档
                    document = self.loader.load_document(file_path)

                    if not document or not document.get('content'):
                        stats['errors'].append(f"文件加载失败或为空: {file_path.name}")
                        continue

                    stats['loaded_files'] += 1

                    # 保存加载的原始文本
                    self.output_manager.save_loaded_document(
                        filename=file_path.stem,
                        content=document.get('content', ''),
                        metadata=document.get('metadata', {})
                    )

                    # 2.2 文本清洗
                    cleaned_text = self.cleaner.clean(
                        document.get('content', ''),
                        filename=file_path.stem,
                        is_ocr=is_ocr
                    )

                    if not cleaned_text:
                        stats['errors'].append(f"清洗后文本为空: {file_path.name}")
                        continue

                    stats['cleaned_files'] += 1

                    # 保存清洗后的文本
                    self.output_manager.save_cleaned_text(
                        filename=file_path.stem,
                        original_content=document.get('content', ''),
                        cleaned_content=cleaned_text,
                        metadata={'pipeline': ['structure', 'encoding', 'simplified']}
                    )

                    # 2.3 文本分块
                    chunks = self.chunker.split(
                        cleaned_text,
                        metadata=document.get('metadata', {})
                    )

                    if not chunks:
                        stats['errors'].append(f"未生成分块: {file_path.name}")
                        continue

                    stats['chunked_files'] += 1
                    stats['total_chunks'] += len(chunks)

                    # 保存分块结果到outputs
                    chunks_data = []
                    for chunk in chunks:
                        chunks_data.append({
                            'index': chunk.index,
                            'content': chunk.content,
                            'start_pos': chunk.start_pos,
                            'end_pos': chunk.end_pos,
                            'metadata': chunk.metadata
                        })
                    self.output_manager.save_chunks(file_path.stem, chunks_data)

                    # 2.4 保存分块到数据库
                    # 计算文件内容哈希
                    content_hash = self.chunk_manager.compute_file_hash(file_path)

                    # 存储分块
                    chunk_records = self.chunk_manager.store_chunks(
                        file_path=file_path,
                        chunks=chunks,
                        file_hash=content_hash,
                        metadata={
                            'processed_at': datetime.now().isoformat(),
                            'chunk_count': len(chunks),
                        }
                    )

                    # 更新增量更新记录
                    self.incremental_tracker.update_record(file_path)

                except Exception as e:
                    error_msg = f"处理文件失败 {file_path.name}: {str(e)}"
                    stats['errors'].append(error_msg)
                    continue

            # 关闭进度条
            progress_bar.close()
            
            # 保存增量更新记录
            self.incremental_tracker._save_records()

            # ========== 完成统计 ==========
            stats['end_time'] = datetime.now().isoformat()

            # 显示处理统计
            print("\n" + "=" * 60)
            print("处理完成统计")
            print("=" * 60)
            print(f"总文件数: {stats['total_files']}")
            print(f"成功加载: {stats['loaded_files']}")
            print(f"成功清洗: {stats['cleaned_files']}")
            print(f"成功分块: {stats['chunked_files']}")
            print(f"总分块数: {stats['total_chunks']}")
            print(f"错误数: {len(stats['errors'])}")

            if stats['errors']:
                print("\n错误详情:")
                for error in stats['errors'][:10]:  # 只显示前10个错误
                    print(f"  - {error}")
                if len(stats['errors']) > 10:
                    print(f"  ... 还有 {len(stats['errors']) - 10} 个错误")

            # 保存统计报告
            self._save_stats_report(stats)

            return stats

        except Exception as e:
            logger.error(f"处理流程出错: {e}")
            raise

    def _save_stats_report(self, stats: Dict[str, Any]):
        """保存处理统计报告"""
        report_path = self.output_manager.output_dir / f"processing_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)

        logger.info(f"统计报告已保存: {report_path}")


@click.group()
@click.option('--config', '-c', type=click.Path(exists=True), help='配置文件路径')
@click.option('--verbose', '-v', is_flag=True, help='详细输出模式')
@click.option('--log-level', type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR']), default=None, help='日志级别（默认使用配置文件中的设置）')
@click.option('--log-dir', type=click.Path(), default='./logs', help='日志目录')
@click.pass_context
def cli(ctx, config, verbose, log_level, log_dir):
    """DocRAG - 文档RAG系统"""
    # 确保上下文对象存在
    ctx.ensure_object(dict)

    # 加载配置
    config_manager = ConfigManager(config_path=config)
    ctx.obj['config'] = config_manager
    ctx.obj['verbose'] = verbose

    # 优先使用命令行参数，否则使用配置文件，最后使用默认值
    effective_log_level = log_level or config_manager.get('logging.level', 'INFO')
    ctx.obj['log_level'] = effective_log_level

    # 设置日志
    log_dir_path = Path(log_dir)
    log_dir_path.mkdir(parents=True, exist_ok=True)
    log_file = log_dir_path / f"doc_rag_{datetime.now().strftime('%Y%m%d')}.log"

    # 获取控制台日志配置
    console_output = config_manager.get('logging.console_output', True)
    console_level = config_manager.get('logging.console_level', effective_log_level)
    
    # verbose模式强制开启控制台输出
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

    # 只在verbose模式下显示日志文件路径
    if verbose:
        logger.info(f"日志文件: {log_file}")


@cli.command()
@click.option('--input-dir', '-i', type=click.Path(exists=True), help='输入文件夹路径')
@click.option('--file-limit', type=int, help='文件数量限制（默认：全部）')
@click.option('--incremental/--full', default=True, help='增量更新模式（默认）/ 全量更新模式')
@click.option('--ocr/--no-ocr', default=False, help='使用OCR清洗模式')
@click.option('--output-dir', '-o', type=click.Path(), help='输出目录路径（默认：./outputs）')
@click.option('--interactive/--no-interactive', '-I', default=False, help='使用交互式配置模式')
@click.pass_context
def build(ctx, input_dir, file_limit, incremental, ocr, output_dir, interactive):
    """构建知识库：文件→加载→清洗→分块→存储"""
    config = ctx.obj['config']
    verbose = ctx.obj.get('verbose', False)

    # 交互式配置模式
    if interactive:
        from src.utils.interactive_config import interactive_config
        user_config = interactive_config(config.get_all())
        
        # 应用交互式配置
        if user_config.get('paths.input_dir'):
            input_dir = user_config.get('paths.input_dir')
        if user_config.get('paths.output_dir'):
            output_dir = user_config.get('paths.output_dir')
        if user_config.get('build.incremental') is not None:
            incremental = user_config.get('build.incremental')
        if user_config.get('build.ocr') is not None:
            ocr = user_config.get('build.ocr')
        if user_config.get('build.file_limit') is not None:
            file_limit = user_config.get('build.file_limit') or None
        if user_config.get('logging.level'):
            # 重新设置日志级别
            from src.utils import setup_logging
            log_dir = ctx.obj.get('log_dir', './logs')
            log_file = Path(log_dir) / f"doc_rag_{datetime.now().strftime('%Y%m%d')}.log"
            setup_logging(
                level=user_config.get('logging.level'),
                format_type="simple" if verbose else "structured",
                log_file=str(log_file),
                console_output=user_config.get('logging.console_output', True)
            )
    
    # 更新配置
    if input_dir:
        config.set('paths.input_dir', input_dir)
    if output_dir:
        config.set('paths.output_dir', output_dir)

    if verbose:
        print("=" * 60)
        print("开始构建知识库")
        print("=" * 60)
        print(f"输入目录: {config.get('paths.input_dir')}")
        print(f"输出目录: {config.get('paths.output_dir')}")
        print(f"增量更新: {'是' if incremental else '否'}")
        print(f"OCR模式: {'是' if ocr else '否'}")
        print()

    try:
        # 创建处理流程
        pipeline = DocRAGPipeline(config, verbose=verbose)

        # 执行处理
        stats = pipeline.process_files(
            input_dir=input_dir,
            file_limit=file_limit,
            incremental=incremental,
            is_ocr=ocr
        )

        # 只在verbose模式或有错误时显示完成信息
        if verbose or stats['errors']:
            print("\n" + "=" * 60)
            print("知识库构建完成")
            print("=" * 60)

            # 输出摘要
            print("\n处理摘要:")
            print(f"  总文件数: {stats['total_files']}")
            print(f"  成功处理: {stats['chunked_files']}")
            print(f"  总分块数: {stats['total_chunks']}")
            print(f"  错误数: {len(stats['errors'])}")

    except Exception as e:
        print(f"构建知识库时出错: {e}")
        raise click.ClickException(str(e))


@cli.command()
@click.option('--query', '-q', required=True, help='查询问题')
@click.option('--top-k', '-k', type=int, default=5, help='返回结果数量（默认：5）')
@click.option('--output-format', type=click.Choice(['json', 'text']), default='text', help='输出格式')
@click.pass_context
def retrieve(ctx, query, top_k, output_format):
    """检索知识库，获取相关文档片段"""
    config = ctx.obj['config']

    logger.info("=" * 60)
    logger.info(f"检索查询: {query}")
    logger.info("=" * 60)

    try:
        # TODO: 实现检索流程
        logger.info(f"检索参数: top_k={top_k}")

        # 模拟检索结果
        results = [
            {"content": "示例检索结果1", "score": 0.95, "metadata": {"source": "doc1.pdf"}},
            {"content": "示例检索结果2", "score": 0.87, "metadata": {"source": "doc2.pdf"}},
        ]

        # 输出结果
        if output_format == 'json':
            import json
            output = json.dumps(results, ensure_ascii=False, indent=2)
        else:
            output = f"\n检索结果 ({len(results)} 条):\n"
            output += "-" * 60 + "\n"
            for i, result in enumerate(results, 1):
                output += f"[{i}] 相似度: {result['score']:.4f}\n"
                output += f"    内容: {result['content']}\n"
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

    logger.info("=" * 60)
    logger.info("系统状态")
    logger.info("=" * 60)

    try:
        # 获取分块管理器统计
        from src.chunkers import ChunkManager
        chunk_manager = ChunkManager(config.get_all())
        stats = chunk_manager.get_stats()

        click.echo("\n分块数据库统计:")
        click.echo(f"  总分块数: {stats['total_chunks']}")
        click.echo(f"  总文件数: {stats['total_files']}")
        click.echo(f"  数据库路径: {stats['db_path']}")

        # 增量更新追踪器统计
        tracker = IncrementalTracker(config.get_all())
        tracker_stats = tracker.get_statistics()
        click.echo("\n增量更新统计:")
        click.echo(f"  已记录文件数: {tracker_stats['total_recorded']}")
        click.echo(f"  模式: {'增量' if tracker_stats['enabled'] else '全量'}")

        # 输出目录状态
        output_dir = Path(config.get('paths.output_dir', './outputs'))
        click.echo(f"\n输出目录: {output_dir}")
        click.echo(f"  存在: {'是' if output_dir.exists() else '否'}")

        if output_dir.exists():
            for subdir in ['loaded', 'cleaned', 'chunks']:
                subdir_path = output_dir / subdir
                if subdir_path.exists():
                    file_count = len(list(subdir_path.glob('*')))
                    click.echo(f"  - {subdir}/: {file_count} 个文件")

    except Exception as e:
        logger.error(f"获取状态时出错: {e}")
        raise click.ClickException(str(e))


@cli.command()
@click.confirmation_option(prompt='确定要清理所有临时文件和缓存吗?')
@click.pass_context
def clean(ctx):
    """清理临时文件和缓存"""
    config = ctx.obj['config']

    logger.info("=" * 60)
    logger.info("清理临时文件和缓存")
    logger.info("=" * 60)

    try:
        import shutil

        # 清理输出目录
        output_dir = Path(config.get('paths.output_dir', './outputs'))
        if output_dir.exists():
            shutil.rmtree(output_dir)
            logger.info(f"已清理输出目录: {output_dir}")

        # 清理缓存目录（保留日志子目录）
        cache_dir = Path('./cache')
        if cache_dir.exists():
            shutil.rmtree(cache_dir)
            logger.info(f"已清理缓存目录: {cache_dir}")

        # 清理日志目录中的旧日志文件（保留当前正在使用的日志文件）
        log_dir = Path('./logs')
        if log_dir.exists():
            current_date = datetime.now().strftime('%Y%m%d')
            for log_file in log_dir.glob('*.log'):
                # 跳过今天的日志文件（正在被使用）
                if current_date not in log_file.name:
                    try:
                        log_file.unlink()
                        logger.info(f"已删除旧日志文件: {log_file}")
                    except PermissionError:
                        logger.warning(f"无法删除日志文件（正在使用）: {log_file}")
            logger.info(f"已清理日志目录（保留当前日志文件）")

        click.echo("清理完成")

    except Exception as e:
        logger.error(f"清理时出错: {e}")
        raise click.ClickException(str(e))


@cli.command()
@click.option('--input-dir', '-i', type=click.Path(exists=True), help='输入文件夹路径')
@click.pass_context
def init(ctx, input_dir):
    """初始化项目配置和目录结构"""
    config = ctx.obj['config']

    logger.info("=" * 60)
    logger.info("初始化项目")
    logger.info("=" * 60)

    try:
        # 创建必要的目录
        dirs_to_create = [
            './outputs',
            './outputs/loaded',
            './outputs/cleaned',
            './outputs/chunks',
            './logs',
            './cache',
            './data',
        ]

        for dir_path in dirs_to_create:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            logger.info(f"创建目录: {dir_path}")

        # 如果指定了输入目录，更新配置
        if input_dir:
            config.set('paths.input_dir', input_dir)
            logger.info(f"设置输入目录: {input_dir}")

        click.echo("\n项目初始化完成！")
        click.echo("目录结构:")
        for dir_path in dirs_to_create:
            click.echo(f"  - {dir_path}")

    except Exception as e:
        logger.error(f"初始化时出错: {e}")
        raise click.ClickException(str(e))


@cli.command(name='set')
@click.option('--category', '-c', type=click.Choice([
    'paths', 'logging', 'loader', 'cleaner', 'chunker', 'performance'
]), help='配置分类（不指定则配置所有）')
@click.pass_context
def set_config(ctx, category):
    """交互式配置系统参数（保存到用户配置文件）"""
    config = ctx.obj['config']
    
    try:
        from src.utils.interactive_config import InteractiveConfigurator
        
        # 获取当前配置
        current_config = config.get_all()
        
        # 创建配置器并运行
        configurator = InteractiveConfigurator(current_config)
        user_config = configurator.run(category=category)
        
        if user_config:
            # 更新配置
            for key, value in user_config.items():
                config.set(key, value)
            
            click.echo(f"\n✓ 配置已保存到: {config.USER_CONFIG_PATH}")
            click.echo(f"✓ 共更新 {len(user_config)} 个配置项")
        else:
            click.echo("\n配置未更改")
            
    except Exception as e:
        click.echo(f"配置时出错: {e}")
        raise click.ClickException(str(e))


@cli.command(name='showset')
@click.option('--format', '-f', type=click.Choice(['text', 'yaml']), 
              default='text', help='输出格式（默认: text）')
@click.option('--category', '-c', type=click.Choice([
    'paths', 'logging', 'loader', 'cleaner', 'chunker', 'performance'
]), help='只显示指定分类的配置')
@click.pass_context
def show_config(ctx, format, category):
    """显示当前系统配置（合并后的配置）"""
    config = ctx.obj['config']
    
    try:
        from src.utils.interactive_config import show_current_config
        
        config_dict = config.get_all()
        
        # 如果只显示特定分类
        if category:
            if category in config_dict:
                config_dict = {category: config_dict[category]}
            else:
                click.echo(f"配置分类 '{category}' 不存在")
                return
        
        # 显示配置来源信息
        click.echo(f"\n配置文件加载顺序:")
        click.echo(f"  1. {config.DEFAULT_CONFIG_PATH} (全局默认)")
        if config.USER_CONFIG_PATH.exists():
            click.echo(f"  2. {config.USER_CONFIG_PATH} (用户配置)")
        click.echo("")
        
        show_current_config(config_dict, format=format)
        
    except Exception as e:
        click.echo(f"显示配置时出错: {e}")
        raise click.ClickException(str(e))


def main():
    """主入口"""
    cli()


if __name__ == '__main__':
    main()
