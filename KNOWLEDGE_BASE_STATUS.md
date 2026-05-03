# HSK-RAG 知识库状态与使用方法

> 文档路径：`D:\Code\HSKRAG\doc_rag_v2\KNOWLEDGE_BASE_STATUS.md`
> 最后更新：2026-04-27
> 维护者：WorkBuddy AI

---

## 一、知识库当前状态

### 1.1 系统概览

| 项目 | 数值 |
|------|------|
| **向量数据库总片段数** | 16,710 |
| **已处理文件数** | 1,533 / 1,537 |
| **文件处理状态** | 完成率 99.7%（4个缺失音频文件） |
| **向量维度** | 768（BGE-base-zh-v1.5） |
| **Embedding 模型** | `BAAI/bge-base-zh-v1.5`（本地缓存） |
| **向量数据库** | Chroma（`./chroma_db`，持久化） |

### 1.2 收录资源总览

知识库 **仅收录 HSK 1-6 级** 汉语水平考试资源，**不包含 HSK 7-9 级**。

| 资源类别 | 路径 | 说明 |
|---------|------|------|
| **HSK 1-6 级真题（主流资源）** | `CA16-hsk/真题/{级别}级真题 N套/` | 含 PDF 试卷、听力音频（mp3/wma）、听力文本（doc）、答案（doc/pdf） |
| **HSK 1-6 级真题（旧版）** | `CA16-hsk/真题/{级别}真题 N份/` | 与主流资源部分重叠 |
| **新版 HSK 考试结构与样题** | `HSK3.0-样题-12.18/` | 2025.12 发布 / 2026.07 实施的 1-6 级新版考试大纲与样题（含音频 wav） |
| **新版 HSK 口语** | `HSK3.0-样题-12.18/新版HSK口语/` | 口语考试样题 |
| **HSK 词汇书（6本）** | `CA16-hsk/HSK 词汇 6本/` | 各级别词汇大纲 |
| **HSK PPT 课件（9本）** | `CA16-hsk/HSK PPT 9本/` | 标准教程课件（1-6 级上下册） |
| **HSK 教师用书（9本）** | `CA16-hsk/HSK教师用书 9本/` | 各级别教师用书 PDF |
| **学生用书和练习册** | `CA16-hsk/学生用书和练习册/` | 教材与配套练习 |
| **新版 HSK 考试大纲** | `CA16-hsk/新版HSK考试大纲1219.pdf` | 2024.12 发布版考试大纲 |
| **HSK3.0 能力描述** | `CA16-hsk/HSK3.0考试能力描述.pdf` | 新版能力等级描述 |

### 1.3 真题套数明细

| 级别 | 主流资源 | 旧版资源 | 合计 |
|------|---------|---------|------|
| HSK 一级 | 34 套 | 27 份（部分重叠） | ~34 套 |
| HSK 二级 | 30 套 | 23 份（部分重叠） | ~30 套 |
| HSK 三级 | 32 套 | 28 份（部分重叠） | ~32 套 |
| HSK 四级 | 32 套 | 26 份（部分重叠） | ~32 套 |
| HSK 五级 | 35 套 | 32 份（部分重叠） | ~35 套 |
| HSK 六级 | 32 套 | 28 份（部分重叠） | ~32 套 |
| **合计** | **~195 套** | **~164 份** | **≥200 套** |

> 注：真题编号规律（如 H31330、H31553B）代表考试日期/批次，31553B 表示 2024 年 5 月第 53 场考试，B 卷（同一场次的不同版本）。

---

## 二、系统架构

```
输入文件（PDF/MP3/DOC/WMA/PPT/CAJ）
        ↓
   [Loader]  多格式文档加载
        ↓
   [Cleaner] 文本清洗（编码修复/繁简转换/结构清理）
        ↓
   [Chunker] 文本分块（chunk_size=500, overlap=50）
        ↓
   [Deduper] 多级去重（MD5 → SimHash）
        ↓
   [Encoder] BGE-base-zh-v1.5 生成 768维向量
        ↓
 [Chroma DB] 持久化向量数据库
        ↓
  [Retriever] 向量检索 + BGE Reranker 重排序
```

---

## 三、使用方法

### 3.1 基础环境准备

```powershell
# 激活 conda 环境
conda activate RAG

# 切换到 RAG 项目目录
cd D:\Code\HSKRAG\doc_rag_v2
```

### 3.2 检索知识库（最常用）

```powershell
# 简单检索（返回 top-5 结果）
python -m src.main retrieve --query "你的问题"

# 指定返回数量
python -m src.main retrieve --query "你的问题" --top-k 10

# 启用重排序（更精确但更慢）
python -m src.main retrieve --query "你的问题" --top-k 5 --rerank
```

**Python 脚本方式（可内嵌使用）：**

```python
import subprocess

def rag_retrieve(query, top_k=5):
    result = subprocess.run(
        ["conda", "run", "-n", "RAG", "python", "-m", "src.main",
         "retrieve", "--query", query, "--top-k", str(top_k)],
        capture_output=True, text=True,
        cwd=r"D:\Code\HSKRAG\doc_rag_v2"
    )
    return result.stdout + result.stderr
```

### 3.3 查看系统状态

```powershell
# 查看已入库的片段数量和文件处理进度
python -m src.main status
```

### 3.4 重建/增量更新知识库

```powershell
# 增量更新（新文件 + 变化文件）
python -m src.main build --input-dir D:\Code\HSKRAG\CA16-hsk --incremental

# 完整重建（慎用，会清空旧数据）
python -m src.main build --input-dir D:\Code\HSKRAG\CA16-hsk
```

### 3.5 清理与导出

```powershell
# 清理缓存
python -m src.main clean

# 导出向量数据库（规划中）
python -m src.main export --output export.zip
```

---

## 四、检索技巧

### 4.1 检索表达建议

| 目标 | 示例查询 |
|------|---------|
| 指定级别 | `HSK3级 听力` / `HSK五级 阅读真题` |
| 指定卷号 | `H31553B 答案` / `H31327 听力` |
| 指定题型 | `HSK4 选词填空` / `HSK6 写作 议论文` |
| 指定话题 | `HSK2 数字 时间 表达` |
| 查找样题 | `新版HSK 三级 样题 听力` |
| 查找大纲 | `HSK 词汇量 要求 四级` |

### 4.2 检索结果解读

每条检索结果包含：

| 字段 | 说明 |
|------|------|
| **相似度** | 0-1 之间，越高越相关（通常 >0.7 较可靠） |
| **来源** | 文件绝对路径（PDF/DOC/MP3 等） |
| **内容** | 匹配到的文档片段原文 |

### 4.3 结果数量选择

| 使用场景 | 建议 `--top-k` |
|---------|---------------|
| 快速验证/单选题 | 3-5 |
| 综述类问题（考试结构介绍） | 5-8 |
| 研究类问题（评分标准、等级对应） | 8-10 |
| 需要穷举某套卷子全部内容 | 15-20 |

---

## 五、注意事项与已知限制

### 5.1 已知限制

1. **HSK 7-9 级真题未收录**：知识库仅包含 1-6 级真题。7-9 级可访问汉考国际官网 chinsesetest.cn 获取信息。
2. **音频文件索引不完整**：部分 `.wma` 格式听力音频未成功解析（共 4 个文件），但 PDF 和 DOC 内容已全部入库。
3. **听力原文与题目分离**：听力原文（`Hxxxxx听力文本.doc`）和答案（`Hxxxxx答案.doc`）为独立文件，检索时可同时命中。
4. **DOC 格式编码问题**：少数 `.doc` 文件（答案/听力文本）存在 GB2312 编码问题，建议优先检索 PDF 格式的试卷原卷。
5. **Reranker 未启用**：当前检索默认不使用重排序模型（如需提高精度，可加 `--rerank` 参数）。

### 5.2 检索优先级

当同一内容在多个文件中出现时，系统按**相似度分数**排序。如需找特定卷子的完整题目，建议：

1. 先用卷号精确检索（如 `H31553B`）
2. 再用题型检索（如 `H31553B 阅读 答案`）
3. 交叉验证多份材料

### 5.3 文件命名规范（知识库内）

| 文件类型 | 命名示例 |
|---------|---------|
| 试卷 | `H31553B.pdf` |
| 听力音频 | `H31553B.mp3` / `H31553B.wma` |
| 听力原文 | `H31553B听力文本.doc` |
| 答案 | `H31553B答案.doc` / `H31553B答案.pdf` |
| 单独试题 | `H31553B试题.pdf` |

---

## 六、快速参考命令卡

```powershell
# === 激活环境 ===
conda activate RAG
cd D:\Code\HSKRAG\doc_rag_v2

# === 检索（最常用）===
python -m src.main retrieve --query "你的检索内容"
python -m src.main retrieve --query "H31553B" --top-k 10
python -m src.main retrieve --query "HSK三级 听力" --top-k 5

# === 系统状态 ===
python -m src.main status

# === 增量更新知识库 ===
python -m src.main build --input-dir D:\Code\HSKRAG\CA16-hsk --incremental

# === 清理缓存 ===
python -m src.main clean
```

---

## 七、相关文档索引

| 文档 | 路径 | 用途 |
|------|------|------|
| DocRAG 用户指南 | `D:\Code\HSKRAG\doc_rag_v2\README.md` | 系统安装、配置、全局命令 |
| DocRAG Agent 协作指南 | `D:\Code\HSKRAG\doc_rag_v2\AGENTS.md` | 开发者架构、模块关系 |
| 用户配置 | `D:\Code\HSKRAG\doc_rag_v2\config.yaml` | 当前生效的配置参数 |
| 新版 HSK 考试大纲 | `D:\Code\HSKRAG\CA16-hsk\新版HSK考试大纲1219.pdf` | 2024.12 版大纲全文 |
| 新版 HSK 样题与结构 | `D:\Code\HSKRAG\CA16-hsk\HSK3.0-样题-12.18\新版HSK（1-6级）考试结构与样题示例.pdf` | 2025.12 发布 / 2026.07 实施的新版样题 |
| HSK3.0 能力描述 | `D:\Code\HSKRAG\CA16-hsk\HSK3.0考试能力描述.pdf` | 各等级能力描述 |
