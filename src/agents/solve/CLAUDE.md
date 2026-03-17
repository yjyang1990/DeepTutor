[根目录](../../../CLAUDE.md) > [src](../../) > [agents](../) > **solve**

# Solve 模块 - 双循环问题求解系统

> 最后更新：2026-03-17 11:33:36

## 变更记录 (Changelog)

### 2026-03-17
- 初始化模块文档

---

## 模块职责

Solve 模块是一个基于**双循环架构**的智能问题求解系统，通过 Analysis Loop（分析循环）和 Solve Loop（求解循环）的协作，实现从问题理解到答案生成的完整工作流。

**核心能力**：
- 智能研究：Analysis Loop 动态判断何时停止研究
- 分块求解：Solve Loop 将复杂问题分解为可管理的块
- 质量保证：Check Agent 自动检查并纠正错误
- 持久化内存：JSON 格式存储，支持断点续跑
- 引用管理：自动引用管理与格式化
- 工具集成：RAG、Web Search、Code Execution

---

## 入口与启动

### Python API

```python
import asyncio
from src.agents.solve import MainSolver

async def main():
    solver = MainSolver(
        kb_name="ai_textbook",
        api_key=os.getenv("LLM_API_KEY"),
        base_url=os.getenv("LLM_HOST"),
    )

    result = await solver.solve(
        question="What is linear convolution?",
        verbose=True
    )

    print(f"Output: {result['output_md']}")

asyncio.run(main())
```

### CLI 启动

```bash
cd DeepTutor
python scripts/start.py  # 默认进入 Solve 模式
```

### WebSocket API

```javascript
const ws = new WebSocket('ws://localhost:8001/api/v1/solve');
ws.onopen = () => {
  ws.send(JSON.stringify({
    question: "Your question",
    kb_name: "ai_textbook"
  }));
};
```

---

## 对外接口

### MainSolver

**主控制器**，协调 Analysis Loop 和 Solve Loop。

**方法**：
```python
async def solve(
    question: str,
    verbose: bool = False
) -> Dict[str, Any]
```

**返回值**：
```python
{
    "output_md": str,              # final_answer.md 路径
    "output_json": str,            # solve_chain.json 路径
    "final_answer": str,           # 最终答案文本
    "citations": List[Dict],       # 引用列表
    "analysis_iterations": int,    # 分析循环迭代次数
    "solve_steps": int,            # 求解步骤数
    "metadata": {
        "output_dir": str,
        "total_steps": int,
        "coverage_rate": float,
        "avg_confidence": float
    }
}
```

### Analysis Loop Agents

**InvestigateAgent**：
- 基于知识链输出多个查询并调用工具
- 生成 `cite_id → raw_result` 映射

**NoteAgent**：
- 逐个处理新 `cite_id`
- 生成摘要和引用

### Solve Loop Agents

**PlanAgent**：生成问题求解计划（blocks）

**ManagerAgent**：为每个 block 安排具体步骤（steps）

**SolveAgent**：根据步骤调用工具并编写推理

**ToolAgent**：统一封装 RAG / Web Search / Code Execution / Query Item 工具

**ResponseAgent**：整理 SolveAgent 和 ToolAgent 的输出

**CheckAgent**：自动检查步骤并提供纠正建议

**PrecisionAnswerAgent**：生成精确答案摘要（可选）

---

## 关键依赖与配置

### 依赖

**核心依赖**：
- `src/agents/base_agent.py` - Agent 基类
- `src/tools/rag_tool.py` - RAG 工具
- `src/tools/web_search.py` - Web 搜索
- `src/tools/run_code.py` - 代码执行
- `src/services/llm/` - LLM 服务

**配置文件**：
- `config/main.yaml` - 系统配置
- `config/agents.yaml` - Agent 参数

### 配置示例

**config/main.yaml**：
```yaml
system:
  output_base_dir: "./data/user/solve"
  max_analysis_iterations: 5
  max_solve_correction_iterations: 3

tools:
  rag_tool:
    kb_base_dir: "./data/knowledge_bases"
    default_kb: "ai_textbook"
  web_search:
    enabled: true
  run_code:
    enabled: true
    workspace: "./data/user/run_code_workspace"
```

**config/agents.yaml**：
```yaml
solve:
  investigate_agent:
    temperature: 0.4
    max_iterations: 3
  solve_agent:
    max_tokens: 8192
  precision_answer_agent:
    enabled: true
    temperature: 0.2
```

---

## 数据模型

### InvestigateMemory

```python
{
    "user_question": str,
    "knowledge_chain": List[Dict],  # 收集的知识
    "reflections": Dict,            # 保留字段（当前仅记录剩余问题）
    "metadata": Dict                # 统计信息
}
```

### SolveMemory

```python
{
    "user_question": str,
    "plan": {
        "blocks": List[Dict]  # 问题求解计划
    },
    "progress": Dict,         # 执行进度
    "metadata": Dict          # 统计信息
}
```

---

## 测试与质量

### 单元测试

**测试文件**：`tests/agents/solve/`

**运行测试**：
```bash
pytest tests/agents/solve/ -v
```

### 质量工具

- Linter：Ruff
- Formatter：Black / Ruff Format
- Type Checker：MyPy（宽松模式）

---

## 常见问题 (FAQ)

**Q: 如何调整 Analysis Loop 的迭代次数？**

A: 在 `config/main.yaml` 中设置 `system.max_analysis_iterations`。

**Q: 如何启用精确答案功能？**

A: 在 `config/agents.yaml` 中设置 `solve.precision_answer_agent.enabled: true`。

**Q: 如何查看详细执行日志？**

A: 设置 `logging.level: "DEBUG"` 或在代码中启用 `verbose=True`。

**Q: 内存文件在哪里？**

A: 在 `{output_base_dir}/solve_{timestamp}/` 目录中。

**Q: 如何重置引用编号？**

A:
```python
from src.agents.solve.solve_loop.citation_manager import CitationManager
CitationManager().reset()
```

---

## 相关文件清单

### 核心文件

- `main_solver.py` - 主控制器
- `base_agent.py` - Agent 基类
- `analysis_loop/investigate_agent.py` - 研究 Agent
- `analysis_loop/note_agent.py` - 笔记 Agent
- `solve_loop/plan_agent.py` - 规划 Agent
- `solve_loop/manager_agent.py` - 管理 Agent
- `solve_loop/solve_agent.py` - 求解 Agent
- `solve_loop/tool_agent.py` - 工具执行 Agent
- `solve_loop/response_agent.py` - 聚合工具结果
- `solve_loop/check_agent.py` - 质量检查
- `solve_loop/precision_answer_agent.py` - 精确答案（可选）
- `solve_loop/citation_manager.py` - 引用管理器

### 内存系统

- `memory/investigate_memory.py` - Analysis Loop 内存
- `memory/solve_memory.py` - Solve Loop 内存

### 工具模块

- `utils/logger.py` - 日志系统
- `utils/performance_monitor.py` - 性能监控
- `utils/config_validator.py` - 配置验证
- `utils/json_utils.py` - JSON 工具
- `utils/error_handler.py` - 错误处理

### Prompt 模板

- `prompts/analysis_loop/` - Analysis Loop Prompts
- `prompts/solve_loop/` - Solve Loop Prompts

### 测试文件

- `tests/agents/solve/utils/test_json_utils.py`

---

## 输出文件

```
data/user/solve/solve_20251116_160009/
├── investigate_memory.json    # Analysis Loop 内存
├── solve_chain.json           # Solve Loop 步骤 & 工具记录
├── citation_memory.json       # 引用管理
├── final_answer.md            # 最终答案（Markdown）
├── performance_report.json    # 性能监控
├── cost_report.json           # 可选：token 成本
├── search_*.json              # 搜索缓存（如有）
└── artifacts/                 # 代码执行输出
```

---

**详细文档**：[analysis_loop/README.md](analysis_loop/README.md) | [solve_loop/README.md](solve_loop/README.md)
