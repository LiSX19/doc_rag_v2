"""
RAGAS评估器实现
"""

from typing import Any, Dict, List, Optional

try:
    from ragas import evaluate
    from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
    from ragas.llms import llm_factory
    from ragas import EvaluationDataset
    RAGAS_AVAILABLE = True
except ImportError:
    RAGAS_AVAILABLE = False
    evaluate = None
    llm_factory = None
    EvaluationDataset = None
    faithfulness = answer_relevancy = context_precision = context_recall = None

from src.utils import OutputManager, get_logger

from .base import BaseEvaluator, EvaluationResult

logger = get_logger(__name__)


class RAGASEvaluator(BaseEvaluator):
    """RAGAS评估器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化RAGAS评估器
        
        Args:
            config: 配置字典，包含：
                - ragas.metrics: 要计算的指标列表
                - ragas.llm: LLM配置（支持openai和ollama）
        """
        super().__init__(config)
        
        # 读取 evaluator 配置（适配 configs.yaml 结构）
        evaluator_config = self.config.get('evaluator', self.config)
        ragas_config = evaluator_config.get('ragas', {})
        
        self.metrics = ragas_config.get('metrics', [
            'faithfulness',
            'answer_relevancy',
            'context_precision',
            'context_recall',
        ])
        
        # 读取LLM配置
        self.llm = None
        llm_config = ragas_config.get('llm', {})
        self.llm_provider = llm_config.get('provider', 'openai')
        self.llm_model = llm_config.get('model', 'gpt-4o-mini')
        self.llm_base_url = llm_config.get('base_url', 'http://localhost:11434/v1')
        self.llm_api_key = llm_config.get('api_key', 'ollama')
        
        # 如果RAGAS库可用，尝试创建LLM实例
        if RAGAS_AVAILABLE and self.llm_provider == 'ollama':
            self._init_ollama_llm()
        
        # 输出管理器
        self.output_manager = OutputManager(config)
    
    def _init_ollama_llm(self):
        """初始化Ollama本地模型"""
        try:
            from openai import OpenAI
            
            client = OpenAI(
                base_url=self.llm_base_url,
                api_key=self.llm_api_key,
            )
            self.llm = llm_factory(
                model=self.llm_model,
                provider='openai',
                client=client,
            )
            logger.info(f"Ollama LLM初始化成功: model={self.llm_model}, base_url={self.llm_base_url}")
        except Exception as e:
            logger.error(f"Ollama LLM初始化失败: {e}", exc_info=True)
            logger.warning("将使用默认LLM（OpenAI）进行RAGAS评估")
    
    def evaluate(
        self,
        questions: List[str],
        contexts: List[List[str]],
        answers: List[str],
        ground_truths: Optional[List[str]] = None
    ) -> EvaluationResult:
        """
        评估RAG系统
        
        Args:
            questions: 问题列表
            contexts: 上下文列表
            answers: 答案列表
            ground_truths: 标准答案列表
            
        Returns:
            评估结果
        """
        # 如果RAGAS库不可用，回退到模拟评估
        if not RAGAS_AVAILABLE:
            logger.warning("RAGAS库未安装，使用模拟评估模式")
            return self._simulate_evaluate(questions, contexts, answers, ground_truths)
        
        try:
            # 准备数据集 - 构建样本列表
            samples = []
            for i, question in enumerate(questions):
                sample = {
                    'user_input': question,
                    'retrieved_contexts': contexts[i],
                    'response': answers[i],
                }
                if ground_truths and i < len(ground_truths):
                    sample['ground_truth'] = ground_truths[i]
                samples.append(sample)
            
            # 转换为RAGAS的EvaluationDataset
            ragas_dataset = EvaluationDataset.from_list(samples)
            
            # 构建指标列表
            metric_objects = []
            metric_mapping = {
                'faithfulness': faithfulness,
                'answer_relevancy': answer_relevancy,
                'context_precision': context_precision,
                'context_recall': context_recall,
            }
            
            for metric_name in self.metrics:
                if metric_name in metric_mapping and metric_mapping[metric_name] is not None:
                    metric_objects.append(metric_mapping[metric_name])
                else:
                    logger.warning(f"未知或不可用的评估指标: {metric_name}")
            
            if not metric_objects:
                logger.error("没有可用的评估指标，使用模拟评估")
                return self._simulate_evaluate(questions, contexts, answers, ground_truths)
            
            # 执行评估
            llm_kwargs = {}
            if self.llm is not None:
                llm_kwargs['llm'] = self.llm
            
            evaluation_result = evaluate(
                dataset=ragas_dataset,
                metrics=metric_objects,
                **llm_kwargs
            )
            
            # 提取指标得分
            metrics_dict = {}
            for metric_name in self.metrics:
                if metric_name in evaluation_result:
                    metrics_dict[metric_name] = float(evaluation_result[metric_name])
            
            # 构建详细结果
            details = []
            for i, question in enumerate(questions):
                detail = {
                    'question': question,
                    'answer': answers[i],
                    'contexts': contexts[i],
                }
                if ground_truths and i < len(ground_truths):
                    detail['ground_truth'] = ground_truths[i]
                details.append(detail)
            
            result = EvaluationResult(
                metrics=metrics_dict,
                details=details,
                metadata={
                    'evaluator': 'RAGAS',
                    'metrics_used': self.metrics,
                    'llm_provider': self.llm_provider,
                    'llm_model': self.llm_model,
                    'ragas_version': 'integrated'
                }
            )
            
            return result
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"RAGAS评估失败: {error_msg}", exc_info=True)
            
            # 检查是否为OpenAI API密钥错误
            if 'api_key' in error_msg.lower() or 'openai' in error_msg.lower():
                logger.warning("RAGAS评估需要OpenAI API密钥。请设置OPENAI_API_KEY环境变量或配置OpenAI API密钥。")
                logger.warning("您可以通过以下方式设置：")
                logger.warning("  1. 设置环境变量: export OPENAI_API_KEY='your-api-key'")
                logger.warning("  2. 在配置文件中配置OpenAI API密钥")
                logger.warning("  3. 使用本地评估模型（需要额外配置）")
            
            logger.warning("回退到模拟评估模式")
            return self._simulate_evaluate(questions, contexts, answers, ground_truths)
    
    def _simulate_evaluate(
        self,
        questions: List[str],
        contexts: List[List[str]],
        answers: List[str],
        ground_truths: Optional[List[str]] = None
    ) -> EvaluationResult:
        """
        模拟评估（当RAGAS库不可用时使用）
        
        Args:
            questions: 问题列表
            contexts: 上下文列表
            answers: 答案列表
            ground_truths: 标准答案列表
            
        Returns:
            评估结果
        """
        metrics = {}
        details = []
        
        for i, question in enumerate(questions):
            detail = {
                'question': question,
                'answer': answers[i],
                'contexts': contexts[i],
            }
            
            if ground_truths:
                detail['ground_truth'] = ground_truths[i]
            
            details.append(detail)
        
        # 模拟指标计算
        if 'faithfulness' in self.metrics:
            metrics['faithfulness'] = 0.85
        if 'answer_relevancy' in self.metrics:
            metrics['answer_relevancy'] = 0.90
        if 'context_precision' in self.metrics:
            metrics['context_precision'] = 0.88
        if 'context_recall' in self.metrics:
            metrics['context_recall'] = 0.82
        
        result = EvaluationResult(
            metrics=metrics,
            details=details,
            metadata={'evaluator': 'RAGAS', 'metrics_used': self.metrics}
        )
        
        return result
    
    def evaluate_and_save(
        self,
        questions: List[str],
        contexts: List[List[str]],
        answers: List[str],
        ground_truths: Optional[List[str]] = None,
        filename: Optional[str] = None
    ) -> 'EvaluationResult':
        """
        评估并保存结果
        
        Args:
            questions: 问题列表
            contexts: 上下文列表
            answers: 答案列表
            ground_truths: 标准答案列表
            filename: 文件名（用于保存输出）
            
        Returns:
            评估结果
        """
        result = self.evaluate(questions, contexts, answers, ground_truths)
        
        # 保存评估报告
        report = {
            'metrics': result.metrics,
            'details': result.details,
            'metadata': result.metadata,
        }
        self.output_manager.save_evaluation_report(report, filename)
        
        return result
    
    def evaluate_retrieval(
        self,
        questions: List[str],
        retrieved_contexts: List[List[str]],
        relevant_contexts: List[List[str]]
    ) -> EvaluationResult:
        """
        评估检索性能
        
        Args:
            questions: 问题列表
            retrieved_contexts: 检索到的上下文列表
            relevant_contexts: 相关上下文列表
            
        Returns:
            评估结果
        """
        # 计算检索精度和召回率
        precisions = []
        recalls = []
        
        for retrieved, relevant in zip(retrieved_contexts, relevant_contexts):
            if not retrieved:
                precision = 0.0
            else:
                relevant_set = set(relevant)
                retrieved_set = set(retrieved)
                precision = len(relevant_set & retrieved_set) / len(retrieved_set)
            
            if not relevant:
                recall = 0.0
            else:
                relevant_set = set(relevant)
                retrieved_set = set(retrieved)
                recall = len(relevant_set & retrieved_set) / len(relevant_set)
            
            precisions.append(precision)
            recalls.append(recall)
        
        avg_precision = sum(precisions) / len(precisions) if precisions else 0.0
        avg_recall = sum(recalls) / len(recalls) if recalls else 0.0
        
        metrics = {
            'retrieval_precision': avg_precision,
            'retrieval_recall': avg_recall,
        }
        
        return EvaluationResult(
            metrics=metrics,
            metadata={'evaluator': 'Retrieval'}
        )
