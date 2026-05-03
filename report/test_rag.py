"""
HSK-RAG 知识库批量测试脚本
用法：conda activate RAG && python D:\Code\HSKRAG\doc_rag_v2\test_rag.py
"""
import sys
import os

# 关键：添加项目路径到 sys.path
PROJECT_DIR = r'D:\Code\HSKRAG\doc_rag_v2'
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)
os.chdir(PROJECT_DIR)  # 切换工作目录

import subprocess
import json
import re
from src.main import PipelineManager
from src.config_manager import ConfigManager

# ========== 测试问题 ==========
questions = [
    ('Q1', 'HSK考试分为哪几个等级？每个等级的考试时长和题型分布是怎样的？'),
    ('Q2', 'HSK5级考试的评分标准是什么？多少分可以通过？'),
    ('Q3', 'HSK口试的考试形式和评分维度有哪些？'),
    ('Q4', 'HSK3级教材中要求掌握的核心词汇有多少个？主要包括哪些类别？'),
    ('Q5', 'HSK4级语法重点包括哪些内容？请列举至少5个关键语法点。'),
    ('Q6', '某本HSK5级教材的单元结构是怎样的？每个单元包含哪些学习模块？'),
    ('Q7', 'HSK阅读部分的常见题型有哪些？每种题型的解题策略是什么？'),
    ('Q8', 'HSK听力考试的难度梯度如何？不同等级的听力材料有什么特点？'),
    ('Q9', 'HSK6级写作部分的评分标准有哪些？如何提高写作得分？'),
    ('Q10', 'HSK的全称是什么？它的中文名称是什么？'),
    ('Q11', 'HSK考试由哪个机构主办？主要用途是什么？'),
    ('Q12', 'HSK考试的适用人群有哪些？'),
    ('Q13', 'HSK考试在全球哪些国家和地区设有考点？'),
    ('Q14', 'HSK成绩的有效期是多久？'),
    ('Q15', 'HSK考试可以重复参加吗？'),
    ('Q16', '2026年HSK考试的改革内容有哪些？与之前版本有何不同？'),
    ('Q17', '2026年HSK考试的具体考试日期安排是怎样的？'),
    ('Q18', '最新的HSK词汇表有哪些变化？新增了哪些词汇？'),
    ('Q19', '2025-2026年出版的HSK教材有哪些新特点？'),
    ('Q20', '最新版HSK真题集包含哪些年份的试题？'),
    ('Q21', 'HSK4级要求掌握的常用量词有哪些？请举例说明用法。'),
    ('Q22', 'HSK5级的固定搭配和习惯用语有哪些？请列举至少10个。'),
    ('Q23', 'HSK6级的语法难点包括哪些？如何突破这些难点？'),
    ('Q24', '针对HSK3级考试，如何制定有效的备考计划？'),
    ('Q25', 'HSK4级听力考试的常见陷阱有哪些？如何避免？'),
    ('Q26', 'HSK5级阅读部分的时间分配策略是什么？如何提高阅读速度？'),
    ('Q27', '如果一个零基础的学习者想在1年内通过HSK4级，应该如何安排学习计划？请详细说明。'),
    ('Q28', '根据HSK等级要求，如何判断自己当前的汉语水平适合报考哪个等级？'),
    ('Q29', '为什么很多学习者在HSK5级考试中阅读部分得分较低？可能的原因有哪些？如何改进？'),
    ('Q30', 'HSK口试中，如何在有限时间内组织语言，提高表达的流畅度和准确性？'),
]

def clean_output(text):
    """清除ANSI控制码"""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

def extract_results(output_text):
    """从原始输出中提取关键信息"""
    lines = output_text.split('\n')
    results = []
    current_item = {}
    for line in lines:
        line = line.strip()
        if not line or '加载' in line or 'it/s]' in line or 'Loading' in line or 'Batches' in line:
            continue
        if line.startswith('[') and '相似度' in line:
            if current_item:
                results.append(current_item)
            # 解析 [1] 相似度: 0.9994 | 来源: ...
            m = re.match(r'\[(\d+)\]\s*相似度[:：]\s*([\d.]+)\s*\|来源[:：]\s*(.+)', line)
            if m:
                current_item = {'similarity': float(m.group(2)), 'source': m.group(3).strip(), 'content': ''}
            else:
                current_item = {'content': ''}
        elif '来源' in line and '相似度' not in line and current_item:
            current_item['source'] = line.replace('来源', '').replace(':', '').replace('：', '').strip()
        elif len(line) > 30 and current_item and 'content' in current_item:
            current_item['content'] += line + '\n'
        elif '检索结果' in line and '条' in line:
            continue
    if current_item and current_item.get('content'):
        results.append(current_item)
    return results

def rag_retrieve(question, top_k=5):
    """使用RAG系统检索"""
    config = ConfigManager()
    pipeline = PipelineManager(config)
    results = pipeline.retrieve(question, top_k=top_k)
    return results

def main():
    print("=" * 60)
    print("HSK-RAG 知识库批量测试")
    print("=" * 60)

    rag_results = {}
    all_results = {}

    # ========== 实验组：RAG 检索 ==========
    print("\n[实验组] 正在使用 RAG 知识库检索...")
    for i, (qid, question) in enumerate(questions, 1):
        print(f"  [{i}/30] {qid}: {question[:40]}...")
        try:
            raw_results = rag_retrieve(question, top_k=5)
            # 格式化结果
            formatted = []
            if isinstance(raw_results, list):
                for r in raw_results:
                    if isinstance(r, dict):
                        formatted.append({
                            'similarity': r.get('score', r.get('similarity', 0)),
                            'source': r.get('metadata', {}).get('source', r.get('source', '')),
                            'content': r.get('content', '')[:300]
                        })
                    elif isinstance(r, str):
                        formatted.append({'content': r[:300]})
            rag_results[qid] = {
                'question': question,
                'results': formatted,
                'has_results': len(formatted) > 0
            }
            print(f"    -> 找到 {len(formatted)} 条结果")
        except Exception as e:
            rag_results[qid] = {
                'question': question,
                'error': str(e),
                'has_results': False
            }
            print(f"    -> 错误: {e}")

    # 保存RAG结果
    output_dir = r'c:\Users\26752\WorkBuddy\20260427111810'
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, 'rag_results.json'), 'w', encoding='utf-8') as f:
            json.dump(rag_results, f, ensure_ascii=False, indent=2)
    print(f"\nRAG检索完成！结果已保存到 rag_results.json")

    # 统计
    has_results = sum(1 for r in rag_results.values() if r.get('has_results', False))
    print(f"  有结果: {has_results}/30")

    all_results['rag'] = rag_results
    return all_results

if __name__ == '__main__':
    all_results = main()
    print("\n完成！")
