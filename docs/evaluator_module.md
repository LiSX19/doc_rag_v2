# Evaluator 模块详细说明文档

## 目录
1. [模块概述](#模块概述)
2. [文件结构](#文件结构)
3. [核心类与接口](#核心类与接口)
4. [RAGAS评估器](#ragas评估器)
5. [评估指标](#评估指标)
6. [配置参数](#配置参数)
7. [使用示例](#使用示例)
8. [扩展开发](#扩展开发)
9. [常见问题](#常见问题)

---

## 模块概述

Evaluator 模块是文档 RAG 系统的评估组件，负责评估检索增强生成 (RAG) 系统的性能和质量。该模块提供标准化的评估接口，支持多种评估方法和指标，帮助用户量化系统的检索效果、生成质量和整体性能。

### 主要功能

1. **多维度评估**: 从忠实度、相关性、精确度、召回率等多个维度评估 RAG 系统
2. **标准化接口**: 统一的评估接口，便于集成和扩展
3. **检索性能评估**: 支持直接评估检索系统的精确率和召回率
4. **LLM 灵活配置**: 支持 OpenAI 和 Ollama 本地模型作为评估 LLM
5. **优雅降级**: 当 RAGAS 库不可用时自动回退到模拟评估模式
6. **结果持久化**: 通过 OutputManager 自动保存评估结果到文件

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
    ├─> 2. LLM初始化
    │      ├─ OpenAI: 使用 OPENAI_API_KEY 环境变量
    │      └─ Ollama: 连接本地服务（默认 http://localhost:11434/v1）
    │
    ├─> 3. 评估执行
    │      ├─ 选择评估模式（RAGAS / 模拟）
    │      ├─ 转换数据为 EvaluationDataset
    │      ├─ 逐项计算各项指标
    │      └─ 生成详细评估记录
    │
    ├─> 4. 结果分析
    │      ├─ 计算平均得分
    │      ├─ 识别薄弱环节
    │      └─ 生成性能报告
    │
    └─> 5. 报告保存
           └─ OutputManager.save_evaluation_report()
```

---

## 文件结构

```
src/evaluators/
├── __init__.py              # 模块导出（BaseEvaluator, RAGASEvaluator）
├── base.py                  # 基类 BaseEvaluator 和 EvaluationResult 定义
└── ragas_evaluator.py       # RAGAS评估器实现
```

---

## 核心类与接口

### 1. BaseEvaluator (抽象基类)

所有评估器的基类，定义统一的评估接口：

```python
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
        """评估RAG系统"""
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
```

### 2. EvaluationResult (评估结果类)

封装评估操作的结果：

```python
class EvaluationResult:
    """评估结果类"""

    def __init__(
        self,
        metrics: Dict[str, float],
        details: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.metrics = metrics
        self.details = details or []
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（支持JSON序列化）"""
        return {
            'metrics': self.metrics,
            'details': self.details,
            'metadata': self.metadata,
        }

    def get_average_score(self) -> float:
        """获取平均分（所有指标的平均值）"""
        if not self.metrics:
            return 0.0
        return sum(self.metrics.values()) / len(self.metrics)
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
                - evaluator.ragas.llm: LLM配置（支持openai和ollama）
        """

    def evaluate(
        self,
        questions: List[str],
        contexts: List[List[str]],
        answers: List[str],
        ground_truths: Optional[List[str]] = None
    ) -> EvaluationResult:
        """执行RAGAS评估，库不可用时自动回退到模拟评估"""

    def evaluate_and_save(
        self,
        questions: List[str],
        contexts: List[List[str]],
        answers: List[str],
        ground_truths: Optional[List[str]] = None,
        filename: Optional[str] = None
    ) -> EvaluationResult:
        """评估并保存结果到文件（通过OutputManager）"""

    def evaluate_retrieval(
        self,
        questions: List[str],
        retrieved_contexts: List[List[str]],
        relevant_contexts: List[List[str]]
    ) -> EvaluationResult:
        """评估检索性能（精确率和召回率）"""

    def _init_ollama_llm(self):
        """初始化Ollama本地模型（通过兼容OpenAI接口）"""

    def _simulate_evaluate(
        self,
        questions, contexts, answers, ground_truths=None
    ) -> EvaluationResult:
        """模拟评估（当RAGAS库不可用时使用）"""
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

### 2. LLM 配置说明

RAGAS 评估依赖 LLM 进行指标计算。当前实现支持两种 LLM 提供商：

#### OpenAI（默认）

使用 OpenAI API 进行评估，需要设置 `OPENAI_API_KEY` 环境变量：

```yaml
evaluator:
  ragas:
    llm:
      provider: "openai"
      model: "gpt-4o-mini"
      # 无需 base_url 和 api_key，默认使用 OpenAI
```

#### Ollama（本地模型）

使用本地部署的 Ollama 服务，无需外部 API 密钥：

```yaml
evaluator:
  ragas:
    llm:
      provider: "ollama"
      model: "qwen3:4b"                        # 本地模型名称
      base_url: "http://localhost:11434/v1"    # Ollama服务地址
      api_key: "ollama"                        # 可填任意值
```

当 `provider` 为 `ollama` 时，`RAGASEvaluator` 会调用 `_init_ollama_llm()` 方法，通过 OpenAI 兼容客户端连接到 Ollama 服务。

### 3. 优雅降级机制

当 RAGAS 库未安装或评估失败时，`RAGASEvaluator` 会自动回退到模拟评估模式：

**触发条件**:
- `ragas` 库未安装（`ImportError`）
- 评估过程中发生异常（如 API 密钥错误、网络超时等）

**回退行为**:
1. 记录警告日志，提示 RAGAS 库未安装或评估失败
2. 调用 `_simulate_evaluate()` 方法，返回预设的模拟得分
3. 模拟得分：faithfulness=0.85, answer_relevancy=0.90, context_precision=0.88, context_recall=0.82

**典型错误处理**:
```python
# 当 OpenAI API 密钥错误时，日志会提示：
# "RAGAS评估需要OpenAI API密钥。请设置OPENAI_API_KEY环境变量"
# 评估器会自动回退到模拟模式，不影响程序运行
```

### 4. 检索性能评估

`RAGASEvaluator` 提供了独立的检索性能评估方法 `evaluate_retrieval()`：

**计算方法**:
- **精确率 (Precision)** = `|检索到的上下文 ∩ 相关上下文| / |检索到的上下文|`
- **召回率 (Recall)** = `|检索到的上下文 ∩ 相关上下文| / |相关上下文|`

**使用场景**:
- 评估检索系统的排序质量
- 对比不同检索策略的效果
- 无需 LLM，轻量级评估

---

## 评估指标

### 1. Faithfulness (忠实度)

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

### 2. Answer Relevancy (答案相关性)

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

### 3. Context Precision (上下文精确度)

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

### 4. Context Recall (上下文召回率)

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

### 5. 检索精确率 / 召回率

**定义**: 通过集合运算直接评估检索系统的精确率和召回率

**计算方法**:
- **Precision** = 检索到的相关文档数 / 检索到的总文档数
- **Recall** = 检索到的相关文档数 / 所有相关文档数

**适用场景**:
- 快速评估检索性能
- 无需 LLM 依赖
- 轻量级基准测试

---

## 配置参数

### 1. 完整配置

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

    # LLM配置（支持OpenAI和Ollama）
    llm:
      provider: "ollama"                    # openai / ollama
      model: "qwen3:4b"                     # ollama: qwen3:4b, openai: gpt-4o-mini
      base_url: "http://localhost:11434/v1" # Ollama服务地址
      api_key: "ollama"                     # ollama可填任意值

    # 输出配置
    output:
      format: "json"
      save_details: true
      generate_summary: true
```

### 2. 配置说明

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `evaluator.type` | string | `"ragas"` | 评估器类型 |
| `evaluator.ragas.metrics` | list | `[faithfulness, answer_relevancy, context_precision, context_recall]` | 要计算的指标列表 |
| `evaluator.ragas.llm.provider` | string | `"ollama"` | LLM提供商，可选 `openai` / `ollama` |
| `evaluator.ragas.llm.model` | string | `"qwen3:4b"` | 模型名称 |
| `evaluator.ragas.llm.base_url` | string | `"http://localhost:11434/v1"` | Ollama 服务地址 |
| `evaluator.ragas.llm.api_key` | string | `"ollama"` | API 密钥 |
| `evaluator.ragas.output.save_details` | bool | `true` | 是否保存详细评估记录 |
| `evaluator.ragas.output.generate_summary` | bool | `true` | 是否生成摘要报告 |

### 3. 输出配置

评估结果通过 `OutputManager` 保存，受 `output` 配置控制：

```yaml
output:
  mode: "test"  # test / production / minimal / custom

  # 预设模式配置
  test:
    save_evaluation: true    # 测试模式：保存评估结果
  production:
    save_evaluation: true    # 生产模式：保存评估结果
  minimal:
    save_evaluation: false   # 最小模式：不保存评估结果
```

评估报告保存路径: `{output_dir}/evaluation/{filename}.json`

### 4. 评估结果格式

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "metrics": {
    "faithfulness": 0.85,
    "answer_relevancy": 0.90,
    "context_precision": 0.88,
    "context_recall": 0.82
  },
  "details": [
    {
      "question": "什么是机器学习？",
      "answer": "机器学习是人工智能的一个分支...",
      "contexts": ["机器学习定义文档...", "AI基础知识..."],
      "ground_truth": "机器学习是使计算机系统能够从数据中学习和改进..."
    }
  ],
  "metadata": {
    "evaluator": "RAGAS",
    "metrics_used": ["faithfulness", "answer_relevancy", "context_precision", "context_recall"],
    "llm_provider": "ollama",
    "llm_model": "qwen3:4b"
  }
}
```

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
```

### 3. 评估并保存结果

```python
from src.evaluators import RAGASEvaluator

# 初始化评估器（带自定义配置）
config = {
    "evaluator": {
        "ragas": {
            "metrics": ["faithfulness", "answer_relevancy", "context_precision"],
            "llm": {
                "provider": "ollama",
                "model": "qwen3:4b",
                "base_url": "http://localhost:11434/v1",
                "api_key": "ollama"
            }
        }
    }
}

evaluator = RAGASEvaluator(config)

# 评估并保存结果
result = evaluator.evaluate_and_save(
    questions=questions,
    contexts=contexts,
    answers=answers,
    filename="my_evaluation"  # 可选，保存在 outputs/evaluation/ 目录
)

print(f"评估结果: {result.metrics}")
```

### 4. 检索性能评估

```python
from src.evaluators import RAGASEvaluator

evaluator = RAGASEvaluator()

# 准备检索数据
questions = ["什么是机器学习？"]
retrieved_contexts = [
    ["文档A：机器学习定义", "文档B：深度学习介绍", "文档C：监督学习"]
]
relevant_contexts = [
    ["文档A：机器学习定义", "文档C：监督学习"]
]

# 执行检索评估
result = evaluator.evaluate_retrieval(questions, retrieved_contexts, relevant_contexts)

print(f"检索精确率: {result.metrics.get('retrieval_precision', 0):.3f}")
print(f"检索召回率: {result.metrics.get('retrieval_recall', 0):.3f}")
```

### 5. 自定义配置与 Ollama 本地模型

```python
from src.evaluators import RAGASEvaluator

# 使用 Ollama 本地模型进行 RAGAS 评估
config = {
    "evaluator": {
        "ragas": {
            "metrics": ["faithfulness", "answer_relevancy", "context_precision", "context_recall"],
            "llm": {
                "provider": "ollama",
                "model": "qwen3:4b",
                "base_url": "http://localhost:11434/v1",
                "api_key": "ollama"
            }
        }
    }
}

evaluator = RAGASEvaluator(config)
result = evaluator.evaluate(questions, contexts, answers)
print(f"平均得分: {result.get_average_score():.3f}")
```

### 6. 自定义评估器

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

        for i, (question, context_list, answer) in enumerate(zip(questions, contexts, answers)):
            custom_score = self._calculate_custom_score(question, context_list, answer)

            detail = {
                "question": question,
                "answer": answer,
                "contexts": context_list,
                "custom_score": custom_score
            }

            if ground_truths and i < len(ground_truths):
                detail["ground_truth"] = ground_truths[i]
                similarity = self._calculate_similarity(answer, ground_truths[i])
                detail["similarity"] = similarity
                custom_score = custom_score * 0.7 + similarity * 0.3

            details.append(detail)
            metrics[f"sample_{i}"] = custom_score

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

    def evaluate_retrieval(
        self,
        questions: List[str],
        retrieved_contexts: List[List[str]],
        relevant_contexts: List[List[str]]
    ) -> EvaluationResult:
        """评估检索性能（必须实现基类的抽象方法）"""
        precisions = []
        recalls = []

        for retrieved, relevant in zip(retrieved_contexts, relevant_contexts):
            relevant_set = set(relevant)
            retrieved_set = set(retrieved)

            precision = len(relevant_set & retrieved_set) / len(retrieved_set) if retrieved_set else 0.0
            recall = len(relevant_set & retrieved_set) / len(relevant_set) if relevant_set else 0.0

            precisions.append(precision)
            recalls.append(recall)

        return EvaluationResult(
            metrics={
                "retrieval_precision": sum(precisions) / len(precisions) if precisions else 0.0,
                "retrieval_recall": sum(recalls) / len(recalls) if recalls else 0.0,
            },
            metadata={"evaluator": "custom"}
        )

    def _calculate_custom_score(self, question: str, contexts: List[str], answer: str) -> float:
        """自定义评分算法"""
        base_score = 0.5

        question_words = set(question.lower().split())
        answer_words = set(answer.lower().split())
        keyword_match = len(question_words & answer_words) / len(question_words) if question_words else 0

        answer_length = len(answer.split())
        length_score = 0.7 if 10 <= answer_length <= 100 else 0.3

        final_score = (base_score * 0.3 + keyword_match * 0.4 + length_score * 0.3)
        return min(1.0, max(0.0, final_score))

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度（Jaccard相似度）"""
        if not text1 or not text2:
            return 0.0
        set1 = set(text1.lower().split())
        set2 = set(text2.lower().split())
        if not set1 and not set2:
            return 1.0
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0
```

---

## 扩展开发

### 1. 实现新的评估器

要实现新的评估器，必须继承 `BaseEvaluator` 并实现两个抽象方法：

```python
from src.evaluators.base import BaseEvaluator, EvaluationResult
from typing import List, Optional

class MyEvaluator(BaseEvaluator):
    """自定义评估器"""

    def evaluate(
        self,
        questions: List[str],
        contexts: List[List[str]],
        answers: List[str],
        ground_truths: Optional[List[str]] = None
    ) -> EvaluationResult:
        # 实现评估逻辑
        pass

    def evaluate_retrieval(
        self,
        questions: List[str],
        retrieved_contexts: List[List[str]],
        relevant_contexts: List[List[str]]
    ) -> EvaluationResult:
        # 实现检索评估逻辑
        pass
```

### 2. 集成外部评估库

如需集成 BLEU/ROUGE 等外部评估库，按上述模板实现即可，在 `evaluate()` 方法中调用相应库的计算函数。

### 3. 注册新的评估器

在 `src/evaluators/__init__.py` 中导出新的评估器类：

```python
from .base import BaseEvaluator
from .ragas_evaluator import RAGASEvaluator
from .my_evaluator import MyEvaluator   # 添加新评估器

__all__ = [
    "BaseEvaluator",
    "RAGASEvaluator",
    "MyEvaluator",
]
```

---

## 常见问题

### Q1: 评估需要标准答案吗？

**答案**: 取决于评估指标：
- **需要标准答案的指标**: Context Recall（RAGAS），以及检索精确率/召回率
- **不需要标准答案的指标**: Faithfulness、Answer Relevancy、Context Precision（RAGAS指标）

**建议**:
1. 如果有标准答案，使用所有相关指标进行全面评估
2. 如果没有标准答案，使用无需标准答案的指标进行初步评估

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
3. 模拟评估模式下返回的是预设值，不代表真实性能

### Q3: 评估结果不一致怎么办？

**可能原因和解决方案**:
1. **数据质量问题**: 检查问题、上下文、答案的质量和一致性
2. **评估指标敏感度**: 不同指标可能关注不同方面，结果自然不同
3. **LLM 随机性**: RAGAS 使用 LLM 进行评估，不同模型/温度可能导致结果波动
4. **配置问题**: 检查评估器 LLM 配置是否正确（Ollama 是否运行？模型是否匹配？）

**建议做法**:
1. 多次评估取平均值
2. 使用多个评估指标综合判断
3. 人工抽查验证评估结果
4. 使用本地 Ollama 模型降低调用成本和延迟

### Q4: 如何配置本地 LLM 进行评估？

**步骤**:
1. 安装并启动 [Ollama](https://ollama.com/)
2. 下载所需模型：`ollama pull qwen3:4b`
3. 在配置中设置 `evaluator.ragas.llm.provider: "ollama"`
4. 确保 `base_url` 指向 Ollama 服务地址（默认 `http://localhost:11434/v1`）

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

### v1.1.0 (当前版本)
- 完整集成RAGAS库，使用 `EvaluationDataset.from_list()` 构建数据集
- 支持 LLM 灵活配置（OpenAI / Ollama 本地模型）
- 添加 `_init_ollama_llm()` 方法初始化本地模型
- 添加优雅降级机制，RAGAS 不可用时自动回退到模拟评估
- 添加 `evaluate_retrieval()` 方法评估检索性能
- 通过 `OutputManager` 统一管理评估结果输出
- 改进错误处理，API 密钥错误时给出清晰的提示信息
- 完善配置结构，支持 `evaluator.ragas.llm` 配置段

---

## 相关链接

- [RAGAS官方文档](https://docs.ragas.io/)
- [Ollama官方文档](https://ollama.com/)
- [OutputManager模块文档](./utils_module.md)
- [配置管理文档](./config.md)
