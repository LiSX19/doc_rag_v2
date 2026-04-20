"""
RAGAS评估器实现
"""

from typing import Any, Dict, List, Optional

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
        
        # 输出管理器
        self.output_manager = OutputManager(config)
    
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
        # TODO: 集成RAGAS库进行实际评估
        # 这里提供简化实现
        
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
