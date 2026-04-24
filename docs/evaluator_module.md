# Evaluator 模块详细说明文档

## 目录
1. [模块概述](#模块概述)
2. [文件结构](#文件结构)
3. [核心类与接口](#核心类与接口)
4. [RAGAS评估器](#ragas评估器)
5. [评估指标](#评估指标)
6. [使用示例](#使用示例)
7. [扩展开发](#扩展开发)

---

## 模块概述

Evaluator 模块是文档 RAG 系统的评估组件，负责评估检索增强生成 (RAG) 系统的性能和质量。该模块提供标准化的评估接口，支持多种评估方法和指标，帮助用户量化系统的检索效果、生成质量和整体性能。

### 主要功能

1. **多维度评估**: 从忠实度、相关性、精确度、召回率等多个维度评估 RAG 系统
2. **标准化接口**: 统一的评估接口，便于集成和扩展
3. **详细报告**: 生成详细的评估报告，包含指标得分、错误分析和改进建议
4. **结果持久化**: 支持评估结果的保存和加载，便于历史对比
5. **可配置指标**: 用户可选择需要计算的评估指标

### 评估流程

```
RAG系统输出
    │
    ├─> 1. 数据准备
    │      ├─ 问题 (Questions)
    │      ├─ 检索到的上下文 (Contexts)
    │      ├─ 生成的答案 (Answers)
    │      └─ 标准答案 (Ground Truths，可选)
    │
    ├─> 2. 评估执行
    │      ├─ 初始化评估器（配置评估指标）
    │      ├─ 逐项计算各项指标
    │      ├─ 聚合结果
    │      └─ 生成详细评估记录
    │
    ├─> 3. 结果分析
    │      ├─ 计算平均得分
    │      ├─ 识别薄弱环节
    │      ├─ 生成性能报告
    │      └─ 提供改进建议
    │
    └─> 4. 报告生成
           ├─ JSON格式详细报告
           ├─ CSV格式汇总报告
           ├─ 可视化图表（可选）
           └─ 历史对比分析
```

---

## 文件结构

```
src/evaluators/
├── __init__.py              # 模块导出
├── base.py                  # 基类和接口定义
└── ragas_evaluator.py       # RAGAS评估器实现
```

---

## 核心类与接口

### 1. BaseEvaluator (抽象基类)

所有评估器的基类，定义统一的评估接口：

```python
class BaseEvaluator(ABC):
    """评估器基类"""
    
    @abstractmethod
    def evaluate(
        self,
        questions: List[str],
        contexts: List[List[str]],
        answers: List[str],
        ground_truths: Optional[List[str]] = None
    ) -> EvaluationResult:
        """评估RAG系统"""
        pass
    
    @abstractmethod
    def evaluate_and_save(
        self,
        questions: List[str],
        contexts: List[List[str]],
        answers: List[str],
        ground_truths: Optional[List[str]] = None,
        output_path: Optional[str] = None
    ) -> str:
        """评估并保存结果"""
        pass
```

### 2. EvaluationResult (评估结果类)

封装评估操作的结果：

```python
class EvaluationResult:
    """评估结果类"""
    
    def __init__(
        self,
        metrics: Dict[str, float],          # 指标字典 {指标名: 得分}
        details: Optional[List[Dict[str, Any]]] = None,  # 详细结果列表
        metadata: Optional[Dict[str, Any]] = None        # 元数据
    ):
        # 初始化逻辑
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（支持JSON序列化）"""
    
    def get_average_score(self) -> float:
        """获取平均分（所有指标的平均值）"""
    
    def get_metric(self, metric_name: str) -> Optional[float]:
        """获取指定指标得分"""
    
    @property
    def score_summary(self) -> Dict[str, Any]:
        """得分摘要"""
        return {
            "average_score": self.get_average_score(),
            "metric_count": len(self.metrics),
            "metrics": self.metrics
        }
```

### 3. RAGASEvaluator (RAGAS评估器)

基于 RAGAS (Retrieval-Augmented Generation Assessment) 框架的评估器实现：

```python
class RAGASEvaluator(BaseEvaluator):
    """RAGAS评估器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化RAGAS评估器
        
        Args:
            config: 配置字典，包含：
                - evaluator.ragas.metrics: 要计算的指标列表
        """
    
    def evaluate(
        self,
        questions: List[str],
        contexts: List[List[str]],
        answers: List[str],
        ground_truths: Optional[List[str]] = None
    ) -> EvaluationResult:
        """执行RAGAS评估"""
    
    def evaluate_and_save(
        self,
        questions: List[str],
        contexts: List[List[str]],
        answers: List[str],
        ground_truths: Optional[List[str]] = None,
        output_path: Optional[str] = None
    ) -> str:
        """评估并保存结果到文件"""
```

---

## RAGAS评估器

### 1. RAGAS 框架简介

RAGAS (Retrieval-Augmented Generation Assessment) 是一个专门用于评估 RAG 系统的框架，提供了一系列针对 RAG 系统特性的评估指标。

**核心特点**:
- **无需参考标准答案**: 部分指标可以在没有人工标注的情况下计算
- **专注于RAG特性**: 专门针对检索和生成流程设计
- **模块化设计**: 可以单独使用特定指标
- **标准化评分**: 所有指标得分归一化到 0-1 范围

### 2. 支持的评估指标

RAGAS评估器支持以下指标（可通过配置选择启用哪些指标）：

#### 2.1 Faithfulness (忠实度)
**定义**: 衡量生成答案是否忠实于提供的上下文，避免幻觉 (hallucination)

**计算原理**:
1. 提取答案中的事实性陈述
2. 检查这些陈述是否在上下文中得到支持
3. 计算支持的事实占比

**适用场景**:
- 检查答案的准确性
- 检测幻觉问题
- 评估信息可靠性

**评分范围**: 0.0-1.0（越高越好）

#### 2.2 Answer Relevancy (答案相关性)
**定义**: 衡量答案与问题的相关程度

**计算原理**:
1. 分析答案是否直接回答了问题
2. 检查答案是否包含无关信息
3. 评估答案的完整性和针对性

**适用场景**:
- 评估答案的质量
- 检查是否答非所问
- 改进回答策略

**评分范围**: 0.0-1.0（越高越好）

#### 2.3 Context Precision (上下文精确度)
**定义**: 衡量检索到的上下文是否包含回答问题所需的相关信息

**计算原理**:
1. 分析上下文中相关信息的位置
2. 计算相关信息的占比和排序质量
3. 评估检索系统的精确性

**适用场景**:
- 评估检索质量
- 优化检索策略
- 改进向量搜索算法

**评分范围**: 0.0-1.0（越高越好）

#### 2.4 Context Recall (上下文召回率)
**定义**: 衡量检索到的上下文是否包含所有相关信息

**计算原理**:
1. 基于标准答案或关键信息
2. 检查上下文中是否包含了所有必要信息
3. 计算信息覆盖率

**适用场景**:
- 需要标准答案的评估
- 评估检索的全面性
- 改进召回策略

**评分范围**: 0.0-1.0（越高越好）

### 3. 配置参数

#### 3.1 基础配置
```yaml
evaluator:
  # 评估器类型 (目前仅支持ragas)
  type: "ragas"
  
  # RAGAS评估器配置
  ragas:
    # 要计算的指标列表
    metrics:
      - "faithfulness"
      - "answer_relevancy"
      - "context_precision"
      - "context_recall"
    
    # 输出配置
    output:
      format: "json"          # 报告格式: json/csv/both
      save_details: true      # 是否保存详细评估记录
      generate_summary: true  # 是否生成摘要报告
```

#### 3.2 高级配置（示例）
```yaml
evaluator:
  type: "ragas"
  
  ragas:
    metrics:
      - "faithfulness"
      - "answer_relevancy"
      - "context_precision"
      - "context_recall"
    
    # 各指标的阈值配置
    thresholds:
      faithfulness: 0.8
      answer_relevancy: 0.7
      context_precision: 0.75
      context_recall: 0.8
    
    # 性能配置
    performance:
      batch_size: 10          # 批处理大小
      timeout: 30             # 单个评估超时时间（秒）
      max_retries: 3          # 失败重试次数
    
    # 模型配置（如果需要）
    models:
      faithfulness: "gpt-3.5-turbo"
      answer_relevancy: "gpt-3.5-turbo"
```

#### 3.3 输出配置
```yaml
evaluator:
  ragas:
    output:
      # 基础配置
      format: "json"          # 输出格式: json/csv/both
      encoding: "utf-8"       # 文件编码
      indent: 2               # JSON缩进（仅对json格式有效）
      
      # 路径配置
      directory: "./outputs/evaluation"  # 输出目录
      filename_pattern: "eval_{timestamp}_{metrics}"  # 文件名模式
      
      # 内容配置
      save_details: true      # 保存详细评估记录
      generate_summary: true  # 生成摘要报告
      include_timestamps: true  # 包含时间戳
      include_config: true    # 包含配置信息
      
      # 可视化配置（可选）
      visualization:
        enabled: false        # 是否生成可视化图表
        format: "png"         # 图表格式: png/svg/pdf
        dpi: 150              # 图像分辨率
```

### 4. 评估结果格式

#### 4.1 评估结果数据结构
```json
{
  "metadata": {
    "evaluator": "RAGAS",
    "version": "1.0.0",
    "timestamp": "2024-01-15T10:30:00Z",
    "config": {
      "metrics": ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
    }
  },
  
  "summary": {
    "average_score": 0.8625,
    "total_samples": 100,
    "metrics_summary": {
      "faithfulness": {
        "average": 0.85,
        "min": 0.2,
        "max": 1.0,
        "std": 0.15
      },
      "answer_relevancy": {
        "average": 0.90,
        "min": 0.3,
        "max": 1.0,
        "std": 0.12
      },
      "context_precision": {
        "average": 0.88,
        "min": 0.25,
        "max": 1.0,
        "std": 0.18
      },
      "context_recall": {
        "average": 0.82,
        "min": 0.1,
        "max": 1.0,
        "std": 0.20
      }
    }
  },
  
  "details": [
    {
      "id": 1,
      "question": "什么是机器学习？",
      "answer": "机器学习是人工智能的一个分支...",
      "contexts": ["机器学习定义文档...", "AI基础知识..."],
      "ground_truth": "机器学习是使计算机系统能够从数据中学习和改进...",
      "metrics": {
        "faithfulness": 0.9,
        "answer_relevancy": 0.95,
        "context_precision": 0.85,
        "context_recall": 0.8
      }
    },
    // ... 更多评估记录
  ],
  
  "analysis": {
    "strengths": ["答案相关性较高", "上下文精确度较好"],
    "weaknesses": ["上下文召回率偏低", "忠实度有提升空间"],
    "recommendations": [
      "优化检索算法以提高召回率",
      "加强答案生成的事实性检查"
    ]
  }
}
```

#### 4.2 CSV格式报告
```
sample_id,question,faithfulness,answer_relevancy,context_precision,context_recall,average_score
1,什么是机器学习？,0.9,0.95,0.85,0.8,0.875
2,深度学习与机器学习的区别？,0.8,0.85,0.9,0.75,0.825
3,监督学习有哪些方法？,0.85,0.9,0.8,0.9,0.8625
```

---

## 评估指标详解

### 1. Faithfulness (忠实度) 详细说明

**数学定义**:
```
faithfulness = (支持的事实数量) / (答案中的总事实数量)
```

**计算步骤**:
1. **事实提取**: 从生成答案中提取所有事实性陈述
2. **证据匹配**: 为每个事实在上下文中寻找支持证据
3. **验证判断**: 判断证据是否充分支持该事实
4. **得分计算**: 计算被支持事实的比例

**影响因素**:
- 上下文的信息完整性
- 答案生成模型的事实性倾向
- 事实提取的准确性

**改进建议**:
- 提供更全面的上下文
- 使用事实性更强的生成模型
- 添加事实验证步骤

### 2. Answer Relevancy (答案相关性) 详细说明

**数学定义**:
```
answer_relevancy = 1 - (无关信息比例) × (冗余度惩罚)
```

**计算步骤**:
1. **问题分析**: 解析问题的核心需求
2. **答案分解**: 将答案分解为信息单元
3. **相关性判断**: 判断每个信息单元与问题的相关性
4. **冗余检测**: 检测重复或冗余信息
5. **得分计算**: 综合相关性和冗余度计算得分

**影响因素**:
- 答案与问题的语义匹配度
- 答案的完整性和针对性
- 信息的组织方式

**改进建议**:
- 加强问题理解
- 优化答案生成策略
- 减少无关信息

### 3. Context Precision (上下文精确度) 详细说明

**数学定义**:
```
context_precision = Σ(位置权重 × 相关性得分) / Σ(位置权重)
```

**位置权重函数**:
```
weight(position) = 1 / log2(position + 1)
```

**计算步骤**:
1. **上下文排序**: 按照检索系统返回的顺序处理上下文
2. **相关性评估**: 评估每个上下文的相关性
3. **位置加权**: 为每个相关上下文应用位置权重
4. **得分计算**: 计算加权平均相关度

**影响因素**:
- 检索系统的排序质量
- 上下文的相关性判断准确性
- 位置权重函数的合理性

**改进建议**:
- 优化检索排序算法
- 改进相关性判断标准
- 调整位置权重策略

### 4. Context Recall (上下文召回率) 详细说明

**数学定义**:
```
context_recall = (检索到的相关信息) / (所有相关信息)
```

**计算步骤**:
1. **相关信息识别**: 识别所有相关信息（基于标准答案或关键信息）
2. **检索匹配**: 检查检索到的上下文是否包含这些信息
3. **覆盖率计算**: 计算信息覆盖率
4. **得分计算**: 计算召回率得分

**影响因素**:
- 检索系统的全面性
- 相关信息识别的准确性
- 上下文的信息密度

**改进建议**:
- 扩大检索范围
- 优化检索策略
- 改进信息识别方法

---

## 使用示例

### 1. 基本使用
```python
from src.evaluators import RAGASEvaluator

# 初始化评估器（使用默认配置）
evaluator = RAGASEvaluator()

# 准备评估数据
questions = [
    "什么是机器学习？",
    "深度学习与机器学习的区别是什么？",
    "监督学习有哪些常见方法？"
]

contexts = [
    ["机器学习是人工智能的一个分支...", "机器学习算法可以从数据中学习..."],
    ["深度学习是机器学习的一个子领域...", "两者在模型复杂度和数据需求上有区别..."],
    ["监督学习包括分类和回归...", "常见算法有决策树、SVM、神经网络等..."]
]

answers = [
    "机器学习是人工智能的一个分支，使计算机能够从数据中学习和改进。",
    "深度学习是机器学习的子集，使用深层神经网络，需要更多数据和计算资源。",
    "监督学习的常见方法包括线性回归、逻辑回归、决策树、支持向量机等。"
]

# 执行评估
result = evaluator.evaluate(questions, contexts, answers)

# 查看评估结果
print(f"平均得分: {result.get_average_score():.3f}")
print(f"忠实度: {result.metrics.get('faithfulness', 0):.3f}")
print(f"答案相关性: {result.metrics.get('answer_relevancy', 0):.3f}")
print(f"上下文精确度: {result.metrics.get('context_precision', 0):.3f}")
print(f"上下文召回率: {result.metrics.get('context_recall', 0):.3f}")
```

### 2. 带标准答案的评估
```python
from src.evaluators import RAGASEvaluator

# 初始化评估器
evaluator = RAGASEvaluator()

# 准备带标准答案的数据
questions = ["什么是机器学习？"]
contexts = [["机器学习定义文档..."]]
answers = ["机器学习是人工智能的一个分支..."]
ground_truths = ["机器学习是使计算机系统能够从数据中学习和改进，无需明确编程。"]

# 执行评估
result = evaluator.evaluate(questions, contexts, answers, ground_truths)

# 查看详细结果
for i, detail in enumerate(result.details):
    print(f"样本 {i+1}:")
    print(f"  问题: {detail['question']}")
    print(f"  答案: {detail['answer'][:50]}...")
    print(f"  标准答案: {detail.get('ground_truth', 'N/A')}")
    print(f"  得分: {detail['metrics']}")
```

### 3. 评估并保存结果
```python
from src.evaluators import RAGASEvaluator

# 初始化评估器（带自定义配置）
config = {
    "evaluator": {
        "ragas": {
            "metrics": ["faithfulness", "answer_relevancy", "context_precision"],
            "output": {
                "format": "json",
                "save_details": True
            }
        }
    }
}

evaluator = RAGASEvaluator(config)

# 准备数据
questions = [...]  # 问题列表
contexts = [...]   # 上下文列表  
answers = [...]    # 答案列表

# 评估并保存结果
output_path = evaluator.evaluate_and_save(
    questions=questions,
    contexts=contexts,
    answers=answers,
    output_path="./evaluation_results.json"
)

print(f"评估结果已保存到: {output_path}")
```

### 4. 批量评估和对比
```python
from src.evaluators import RAGASEvaluator
import json

# 初始化评估器
evaluator = RAGASEvaluator()

# 多个批次的评估数据
batches = [
    {
        "name": "第一批",
        "questions": [...],
        "contexts": [...],
        "answers": [...]
    },
    {
        "name": "第二批", 
        "questions": [...],
        "contexts": [...],
        "answers": [...],
        "ground_truths": [...]
    }
]

# 批量评估
batch_results = []
for batch in batches:
    result = evaluator.evaluate(
        batch["questions"],
        batch["contexts"],
        batch["answers"],
        batch.get("ground_truths")
    )
    
    batch_results.append({
        "name": batch["name"],
        "result": result.to_dict()
    })

# 生成对比报告
comparison_report = {
    "timestamp": "2024-01-15T10:30:00Z",
    "batches": batch_results,
    "summary": {
        "best_batch": max(batch_results, key=lambda x: x["result"]["metrics"]["average_score"])["name"],
        "worst_batch": min(batch_results, key=lambda x: x["result"]["metrics"]["average_score"])["name"],
        "average_scores": {
            batch["name"]: batch["result"]["metrics"]["average_score"] 
            for batch in batch_results
        }
    }
}

# 保存对比报告
with open("batch_comparison.json", "w", encoding="utf-8") as f:
    json.dump(comparison_report, f, ensure_ascii=False, indent=2)

print("批量对比报告已生成")
```

### 5. 自定义评估器
```python
from src.evaluators.base import BaseEvaluator, EvaluationResult
from typing import List, Dict, Any, Optional

class CustomEvaluator(BaseEvaluator):
    """自定义评估器示例"""
    
    def __init__(self, config=None):
        super().__init__(config)
        self.config = config or {}
        self.custom_metric_weight = self.config.get("custom_metric_weight", 0.5)
    
    def evaluate(
        self,
        questions: List[str],
        contexts: List[List[str]],
        answers: List[str],
        ground_truths: Optional[List[str]] = None
    ) -> EvaluationResult:
        """自定义评估逻辑"""
        
        metrics = {}
        details = []
        
        # 自定义评估逻辑
        for i, (question, context_list, answer) in enumerate(zip(questions, contexts, answers)):
            # 计算自定义指标
            custom_score = self._calculate_custom_score(question, context_list, answer)
            
            # 准备详细记录
            detail = {
                "question": question,
                "answer": answer,
                "contexts": context_list,
                "custom_score": custom_score
            }
            
            if ground_truths and i < len(ground_truths):
                detail["ground_truth"] = ground_truths[i]
                # 可以计算与标准答案的相似度
                similarity = self._calculate_similarity(answer, ground_truths[i])
                detail["similarity"] = similarity
                custom_score = custom_score * 0.7 + similarity * 0.3
            
            details.append(detail)
            metrics[f"sample_{i}"] = custom_score
        
        # 计算聚合指标
        if details:
            avg_score = sum(metrics.values()) / len(metrics)
            metrics["average_custom_score"] = avg_score
        
        return EvaluationResult(
            metrics=metrics,
            details=details,
            metadata={
                "evaluator": "custom",
                "custom_metric_weight": self.custom_metric_weight
            }
        )
    
    def _calculate_custom_score(self, question: str, contexts: List[str], answer: str) -> float:
        """自定义评分算法"""
        # 实现自定义评分逻辑
        # 例如：基于答案长度、关键词匹配、语义相似度等
        base_score = 0.5
        
        # 检查答案是否包含问题中的关键词
        question_words = set(question.lower().split())
        answer_words = set(answer.lower().split())
        keyword_match = len(question_words & answer_words) / len(question_words) if question_words else 0
        
        # 检查答案长度是否合适
        answer_length = len(answer.split())
        length_score = 0.7 if 10 <= answer_length <= 100 else 0.3
        
        # 综合评分
        final_score = (base_score * 0.3 + keyword_match * 0.4 + length_score * 0.3)
        
        return min(1.0, max(0.0, final_score))
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度（简化示例）"""
        if not text1 or not text2:
            return 0.0
        
        # 使用Jaccard相似度
        set1 = set(text1.lower().split())
        set2 = set(text2.lower().split())
        
        if not set1 and not set2:
            return 1.0
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
    
    def evaluate_and_save(
        self,
        questions: List[str],
        contexts: List[List[str]],
        answers: List[str],
        ground_truths: Optional[List[str]] = None,
        output_path: Optional[str] = None
    ) -> str:
        """评估并保存结果"""
        result = self.evaluate(questions, contexts, answers, ground_truths)
        
        # 确定输出路径
        if not output_path:
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"./evaluation_custom_{timestamp}.json"
        
        # 保存结果
        import json
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
        
        return output_path
```

---

## 扩展开发

### 1. 添加新的评估指标

**步骤 1**: 创建支持新指标的评估器
```python
from src.evaluators import RAGASEvaluator

class EnhancedRAGASEvaluator(RAGASEvaluator):
    """增强版RAGAS评估器，添加新指标"""
    
    def __init__(self, config=None):
        super().__init__(config)
        
        # 读取新指标配置
        evaluator_config = self.config.get('evaluator', self.config)
        ragas_config = evaluator_config.get('ragas', {})
        
        # 添加新指标到指标列表
        additional_metrics = ragas_config.get('additional_metrics', [])
        self.metrics.extend(additional_metrics)
    
    def evaluate(self, questions, contexts, answers, ground_truths=None):
        """重写评估方法，添加新指标计算"""
        
        # 先执行基类评估
        result = super().evaluate(questions, contexts, answers, ground_truths)
        
        # 添加新指标计算
        if 'answer_coherence' in self.metrics:
            coherence_scores = self._calculate_coherence(answers)
            result.metrics['answer_coherence'] = sum(coherence_scores) / len(coherence_scores)
        
        if 'context_diversity' in self.metrics:
            diversity_scores = self._calculate_diversity(contexts)
            result.metrics['context_diversity'] = sum(diversity_scores) / len(diversity_scores)
        
        return result
    
    def _calculate_coherence(self, answers: List[str]) -> List[float]:
        """计算答案连贯性"""
        scores = []
        for answer in answers:
            # 连贯性评分逻辑
            # 例如：检查句子之间的逻辑连接、话题一致性等
            score = 0.8  # 简化示例
            scores.append(score)
        return scores
    
    def _calculate_diversity(self, contexts: List[List[str]]) -> List[float]:
        """计算上下文多样性"""
        scores = []
        for context_list in contexts:
            # 多样性评分逻辑
            # 例如：计算不同来源的上下文比例、信息重叠度等
            if len(context_list) <= 1:
                score = 0.0
            else:
                # 简化示例：基于不同上下文的数量
                score = min(1.0, len(set(context_list)) / len(context_list))
            scores.append(score)
        return scores
```

**步骤 2**: 更新配置支持
```yaml
evaluator:
  type: "enhanced_ragas"
  
  ragas:
    metrics:
      - "faithfulness"
      - "answer_relevancy"
      - "context_precision"
      - "context_recall"
    
    additional_metrics:
      - "answer_coherence"
      - "context_diversity"
```

### 2. 集成外部评估库

**集成 BLEU/ROUGE 评估**:
```python
from rouge_score import rouge_scorer
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction

class NLTKEvaluator(BaseEvaluator):
    """NLTK评估器（BLEU/ROUGE）"""
    
    def __init__(self, config=None):
        super().__init__(config)
        self.config = config or {}
        
        # 读取配置
        evaluator_config = self.config.get('evaluator', self.config)
        nltk_config = evaluator_config.get('nltk', {})
        
        self.use_bleu = nltk_config.get('use_bleu', True)
        self.use_rouge = nltk_config.get('use_rouge', True)
        self.rouge_types = nltk_config.get('rouge_types', ['rouge1', 'rouge2', 'rougeL'])
        
        # 初始化ROUGE计算器
        if self.use_rouge:
            self.rouge_scorer = rouge_scorer.RougeScorer(self.rouge_types, use_stemmer=True)
    
    def evaluate(self, questions, contexts, answers, ground_truths=None):
        """执行NLTK评估"""
        
        if not ground_truths:
            raise ValueError("NLTK评估需要标准答案")
        
        metrics = {}
        details = []
        
        bleu_scores = []
        rouge_scores = {rouge_type: [] for rouge_type in self.rouge_types}
        
        for i, (answer, ground_truth) in enumerate(zip(answers, ground_truths)):
            detail = {
                "question": questions[i] if i < len(questions) else f"question_{i}",
                "answer": answer,
                "ground_truth": ground_truth
            }
            
            # 计算BLEU分数
            if self.use_bleu:
                # 准备参考文本（分词）
                reference = [ground_truth.split()]
                candidate = answer.split()
                
                # 计算BLEU（使用平滑函数处理零匹配情况）
                smoothing = SmoothingFunction().method1
                bleu_score = sentence_bleu(reference, candidate, smoothing_function=smoothing)
                
                detail["bleu_score"] = bleu_score
                bleu_scores.append(bleu_score)
            
            # 计算ROUGE分数
            if self.use_rouge:
                rouge_result = self.rouge_scorer.score(ground_truth, answer)
                
                detail["rouge_scores"] = {}
                for rouge_type in self.rouge_types:
                    score = rouge_result[rouge_type].fmeasure
                    detail["rouge_scores"][rouge_type] = score
                    rouge_scores[rouge_type].append(score)
            
            details.append(detail)
        
        # 计算平均分数
        if self.use_bleu and bleu_scores:
            metrics["bleu_average"] = sum(bleu_scores) / len(bleu_scores)
        
        if self.use_rouge and rouge_scores:
            for rouge_type in self.rouge_types:
                if rouge_scores[rouge_type]:
                    metrics[f"{rouge_type}_average"] = sum(rouge_scores[rouge_type]) / len(rouge_scores[rouge_type])
        
        return EvaluationResult(
            metrics=metrics,
            details=details,
            metadata={
                "evaluator": "nltk",
                "config": {
                    "use_bleu": self.use_bleu,
                    "use_rouge": self.use_rouge,
                    "rouge_types": self.rouge_types
                }
            }
        )
```

### 3. 性能优化

**并行评估优化**:
```python
from concurrent.futures import ThreadPoolExecutor, as_completed

class ParallelEvaluator(BaseEvaluator):
    """并行评估器"""
    
    def __init__(self, config=None):
        super().__init__(config)
        self.config = config or {}
        
        # 读取并行配置
        evaluator_config = self.config.get('evaluator', self.config)
        parallel_config = evaluator_config.get('parallel', {})
        
        self.max_workers = parallel_config.get('max_workers', 4)
        self.batch_size = parallel_config.get('batch_size', 10)
    
    def evaluate(self, questions, contexts, answers, ground_truths=None):
        """并行评估"""
        
        # 将数据分批次
        num_samples = len(questions)
        batches = []
        
        for i in range(0, num_samples, self.batch_size):
            batch_end = min(i + self.batch_size, num_samples)
            
            batch = {
                "questions": questions[i:batch_end],
                "contexts": contexts[i:batch_end],
                "answers": answers[i:batch_end],
            }
            
            if ground_truths:
                batch["ground_truths"] = ground_truths[i:batch_end]
            
            batches.append(batch)
        
        # 并行执行评估
        all_details = []
        all_metrics = {}
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交批处理任务
            future_to_batch = {
                executor.submit(self._evaluate_batch, batch): batch 
                for batch in batches
            }
            
            # 收集结果
            for future in as_completed(future_to_batch):
                batch_result = future.result()
                all_details.extend(batch_result["details"])
                
                # 合并指标
                for metric_name, metric_value in batch_result["metrics"].items():
                    if metric_name not in all_metrics:
                        all_metrics[metric_name] = []
                    all_metrics[metric_name].append(metric_value)
        
        # 计算聚合指标
        final_metrics = {}
        for metric_name, values in all_metrics.items():
            final_metrics[metric_name] = sum(values) / len(values)
        
        return EvaluationResult(
            metrics=final_metrics,
            details=all_details,
            metadata={
                "evaluator": "parallel",
                "parallel_config": {
                    "max_workers": self.max_workers,
                    "batch_size": self.batch_size,
                    "num_batches": len(batches)
                }
            }
        )
    
    def _evaluate_batch(self, batch):
        """评估单个批次"""
        # 这里可以使用任何评估器来评估批次
        # 例如：调用RAGASEvaluator或自定义评估器
        from src.evaluators import RAGASEvaluator
        
        evaluator = RAGASEvaluator(self.config)
        result = evaluator.evaluate(
            batch["questions"],
            batch["contexts"],
            batch["answers"],
            batch.get("ground_truths")
        )
        
        return {
            "details": result.details,
            "metrics": result.metrics
        }
```

---

## 常见问题

### Q1: 评估需要标准答案吗？

**答案**: 取决于评估指标：
- **需要标准答案的指标**: Context Recall、BLEU、ROUGE等
- **不需要标准答案的指标**: Faithfulness、Answer Relevancy、Context Precision等（RAGAS指标）

**建议**: 
1. 如果有标准答案，使用所有相关指标进行全面评估
2. 如果没有标准答案，使用无需标准答案的指标进行初步评估
3. 可以考虑使用人工标注或高质量参考生成标准答案

### Q2: 如何解释评估得分？

**得分解释指南**:
- **0.9+**: 优秀性能，接近人类水平
- **0.8-0.9**: 良好性能，满足大多数应用需求
- **0.7-0.8**: 一般性能，可能需要改进
- **0.6-0.7**: 较差性能，需要显著改进
- **0.6以下**: 很差性能，可能需要重新设计系统

**注意事项**:
1. 不同指标的基准可能不同
2. 得分应结合具体应用场景解释
3. 建议建立自己的基准线进行对比

### Q3: 评估结果不一致怎么办？

**可能原因和解决方案**:
1. **数据质量问题**: 检查问题、上下文、答案的质量和一致性
2. **评估指标敏感度**: 不同指标可能关注不同方面，结果自然不同
3. **随机性因素**: 某些评估可能包含随机性，多次评估取平均
4. **配置问题**: 检查评估器配置是否正确

**建议做法**:
1. 多次评估取平均值
2. 使用多个评估指标综合判断
3. 人工抽查验证评估结果
4. 建立稳定的评估流程

### Q4: 如何提高评估效率？

**效率优化建议**:
1. **批处理**: 合理设置批处理大小，平衡内存使用和速度
2. **并行处理**: 启用并行评估（如果CPU资源充足）
3. **缓存结果**: 对相同的评估请求缓存结果
4. **简化指标**: 根据需求选择必要的评估指标
5. **增量评估**: 只评估发生变化的部分

### Q5: 评估结果如何用于系统改进？

**改进流程**:
1. **识别薄弱环节**: 通过评估结果找出得分较低的指标
2. **分析原因**: 深入研究低分样本，找出问题根源
3. **制定改进策略**: 根据问题原因制定针对性改进措施
4. **实施改进**: 修改系统配置、算法或流程
5. **重新评估**: 使用相同数据集重新评估，验证改进效果
6. **持续迭代**: 重复上述流程，持续优化系统

---

## 版本历史

### v1.0.0 (初始版本)
- 实现基础评估框架和接口
- 集成RAGAS评估器（简化版）
- 支持忠实度、相关性、精确度、召回率等指标
- 提供评估结果持久化和报告生成

### v1.1.0 (计划功能)
- 完整集成RAGAS库
- 添加更多评估指标（答案连贯性、上下文多样性等）
- 支持并行评估
- 添加可视化报告
- 支持评估结果对比和趋势分析

---

## 相关链接

- [RAGAS官方文档](https://