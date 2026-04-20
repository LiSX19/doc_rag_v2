"""
评估器基类
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class EvaluationResult:
    """评估结果类"""
    
    def __init__(
        self,
        metrics: Dict[str, float],
        details: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        初始化评估结果
        
        Args:
            metrics: 指标字典
            details: 详细结果列表
            metadata: 元数据
        """
        self.metrics = metrics
        self.details = details or []
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'metrics': self.metrics,
            'details': self.details,
            'metadata': self.metadata,
        }
    
    def get_average_score(self) -> float:
        """获取平均分"""
        if not self.metrics:
            return 0.0
        return sum(self.metrics.values()) / len(self.metrics)


class BaseEvaluator(ABC):
    """评估器基类"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化评估器
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
    
    @abstractmethod
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
            contexts: 上下文列表（每个问题对应一个上下文列表）
            answers: 答案列表
            ground_truths: 标准答案列表（可选）
            
        Returns:
            评估结果
        """
        pass
    
    @abstractmethod
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
            relevant_contexts: 相关上下文列表（标准答案）
            
        Returns:
            评估结果
        """
        pass
