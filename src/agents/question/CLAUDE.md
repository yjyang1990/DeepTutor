[根目录](../../../CLAUDE.md) > [src](../../) > [agents](../) > **question**

# Question 模块 - 智能题目生成系统

> 最后更新：2026-03-17 11:33:36

## 变更记录 (Changelog)

### 2026-03-17
- 初始化模块文档

---

## 模块职责

Question 模块是一个基于**模块化 Agent 架构**的智能题目生成系统，支持知识库驱动的自定义生成和参考试卷模仿两种模式。

**核心能力**：
- 自定义模式：基于知识库生成定制题目
- 模仿模式：基于参考试卷生成相似题目
- 单次生成 + 分析：无迭代循环，单次生成后进行相关性分析
- 双语 Prompt：支持中英文
- 实时流式输出：WebSocket 进度更新

---

## 入口与启动

### Python API - 批量生成

```python
import asyncio
from src.agents.question import AgentCoordinator

async def main():
    coordinator = AgentCoordinator(
        kb_name="math2211",
        output_dir="data/user/question",
        language="en"
    )

    result = await coordinator.generate_questions_custom(
        requirement={
            "knowledge_point": "Multivariable limits",
            "difficulty": "medium",
            "question_type": "choice"
        },
        num_questions=3
    )

    print(f"✅ Generated {result['completed']}/{result['requested']} questions")

asyncio.run(main())
```

### Python API - 单题生成

```python
requirement = {
    "knowledge_point": "Limits and continuity",
    "difficulty": "medium",
    "question_type": "choice"
}

result = await coordinator.generate_question(requirement)

if result["success"]:
    print(f"Question: {result['question']['question']}")
    print(f"Relevance: {result['validation']['relevance']}")
```

### 模仿模式 - PDF 上传

```python
from src.tools.question import mimic_exam_questions

result = await mimic_exam_questions(
    pdf_path="exams/midterm.pdf",
    kb_name="math2211",
    output_dir="data/user/question/mimic_papers",
    max_questions=5
)

print(f"✅ Generated {result['successful_generations']} questions")
```

### WebSocket API

```javascript
const ws = new WebSocket('ws://localhost:8001/api/v1/question/generate');
ws.onopen = () => {
  ws.send(JSON.stringify({
    requirement: {
      knowledge_point: "Linear Algebra",
      difficulty: "medium",
      question_type: "choice"
    },
    num_questions: 3
  }));
};
```

---

## 对外接口

### AgentCoordinator

**工作流编排器**，协调 RetrieveAgent、GenerateAgent、RelevanceAnalyzer。

**方法**：
```python
async def generate_question(
    requirement: Dict[str, Any],
    reference_question: Optional[str] = None
) -> Dict[str, Any]

async def generate_questions_custom(
    requirement: Dict[str, Any],
    num_questions: int = 1
) -> Dict[str, Any]
```

**返回值（单题）**：
```python
{
    "success": True,
    "question": {
        "question_type": "choice",
        "question": "Question content",
        "options": {"A": "...", "B": "...", "C": "...", "D": "..."},
        "correct_answer": "A",
        "explanation": "Detailed explanation",
        "knowledge_point": "Topic name"
    },
    "validation": {
        "decision": "approve",
        "relevance": "high",    # or "partial"
        "kb_coverage": "This question tests...",
        "extension_points": ""  # Only if relevance is "partial"
    },
    "rounds": 1
}
```

### RetrieveAgent

**知识检索 Agent**，从知识库检索背景知识。

**方法**：
```python
async def process(
    requirement: Dict[str, Any],
    num_queries: int = 3
) -> Dict[str, Any]
```

**返回值**：
```python
{
    "queries": List[str],
    "retrievals": List[Dict],
    "summary": str,
    "has_content": bool
}
```

### GenerateAgent

**题目生成 Agent**，基于知识上下文生成题目。

**方法**：
```python
async def process(
    requirement: Dict[str, Any],
    knowledge_context: str,
    focus: Dict[str, Any],
    reference_question: Optional[str] = None
) -> Dict[str, Any]
```

### RelevanceAnalyzer

**相关性分析 Agent**，替代旧的 ValidationWorkflow。

**关键差异**：
- 无拒绝：所有题目都被接受
- 无迭代：单次分析
- 输出：相关性等级（high/partial）+ 解释

**方法**：
```python
async def process(
    question: Dict[str, Any],
    knowledge_context: str
) -> Dict[str, Any]
```

**返回值**：
```python
{
    "relevance": "high",  # or "partial"
    "kb_coverage": "This question tests...",
    "extension_points": ""  # Only if relevance is "partial"
}
```

---

## 关键依赖与配置

### 依赖

**核心依赖**：
- `src/agents/base_agent.py` - Agent 基类
- `src/tools/rag_tool.py` - RAG 工具
- `src/tools/question/pdf_parser.py` - PDF 解析（MinerU）
- `src/tools/question/question_extractor.py` - 题目提取
- `src/tools/question/exam_mimic.py` - 参考题目生成

**配置文件**：
- `config/main.yaml` - 模块配置（question 部分）
- `config/agents.yaml` - Agent 参数

### 配置示例

**config/main.yaml**：
```yaml
question:
  rag_query_count: 3
  max_parallel_questions: 1
  rag_mode: naive
  agents:
    retrieve:
      top_k: 30
    generate:
      max_retries: 2
    relevance_analyzer:
      enabled: true
```

**config/agents.yaml**：
```yaml
question:
  temperature: 0.7
  max_tokens: 4000
```

---

## 数据模型

### Requirement

```python
{
    "knowledge_point": str,      # 知识点
    "difficulty": str,           # easy/medium/hard
    "question_type": str         # choice/written/calculation
}
```

### Question

```python
{
    "question_type": str,
    "question": str,
    "options": Dict[str, str],   # For choice questions
    "correct_answer": str,
    "explanation": str,
    "knowledge_point": str
}
```

### Validation Result

```python
{
    "decision": "approve",       # Always approve
    "relevance": str,            # "high" or "partial"
    "kb_coverage": str,
    "extension_points": str      # Only if relevance is "partial"
}
```

---

## 测试与质量

### 单元测试

**测试文件**：`tests/agents/question/`（待添加）

**运行测试**：
```bash
pytest tests/agents/question/ -v
```

### 质量工具

- Linter：Ruff
- Formatter：Black / Ruff Format
- Type Checker：MyPy（宽松模式）

---

## 常见问题 (FAQ)

**Q: 如何调整 RAG 查询数量？**

A: 在 `config/main.yaml` 中设置 `question.rag_query_count`。

**Q: 如何禁用相关性分析？**

A: 在 `config/main.yaml` 中设置 `question.agents.relevance_analyzer.enabled: false`。

**Q: 如何使用不同的知识库？**

A:
```python
coordinator = AgentCoordinator(kb_name="my_kb", ...)
```

**Q: 模仿模式如何工作？**

A:
1. 使用 MinerU 解析 PDF
2. 提取参考题目
3. 为每个参考题目生成相似题目

**Q: 如何自定义 Prompt？**

A: 编辑 `prompts/en/` 或 `prompts/zh/` 中的 YAML 文件。

---

## 相关文件清单

### 核心文件

- `coordinator.py` - 工作流编排
- `agents/retrieve_agent.py` - 知识检索
- `agents/generate_agent.py` - 题目生成
- `agents/relevance_analyzer.py` - 相关性分析

### Prompts

- `prompts/zh/` - 中文 Prompts
  - `retrieve_agent.yaml`
  - `generate_agent.yaml`
  - `relevance_analyzer.yaml`
  - `coordinator.yaml`
- `prompts/en/` - 英文 Prompts（同结构）

### 工具（已移至 src/tools/question/）

- `src/tools/question/pdf_parser.py` - PDF 解析
- `src/tools/question/question_extractor.py` - 题目提取
- `src/tools/question/exam_mimic.py` - 参考题目生成

---

## 输出文件

### 自定义模式

```
data/user/question/batch_YYYYMMDD_HHMMSS/
├── knowledge.json       # RAG 查询和检索
├── plan.json            # 题目焦点
├── q_1/
│   ├── result.json      # 题目 + 分析
│   └── question.md      # 人类可读格式
├── q_2/
│   ├── result.json
│   └── question.md
└── summary.json         # 总体摘要
```

### 模仿模式

```
data/user/question/mimic_papers/{paper_name}/
├── auto/{paper_name}.md                              # MinerU 解析的 Markdown
├── {paper_name}_YYYYMMDD_HHMMSS_questions.json       # 提取的参考题目
└── {paper_name}_YYYYMMDD_HHMMSS_generated.json       # 生成的题目
```

---

## 架构变更

### ✅ 新架构

1. **统一 BaseAgent**：所有 Agent 继承自 `src/agents/base_agent.py`
2. **专用 Agents**：RetrieveAgent、GenerateAgent、RelevanceAnalyzer
3. **无迭代/拒绝**：单次生成 + 分析，所有题目接受并分类
4. **工具移动**：`src/agents/question/tools/` → `src/tools/question/`

### ❌ 已移除

1. **旧 ReAct 架构**：`agents/base_agent.py`（ReAct 范式）
2. **迭代逻辑**：无验证循环、无任务拒绝
3. **消息队列**：简化为直接方法调用

---

**详细文档**：[README.md](README.md)
