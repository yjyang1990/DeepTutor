[根目录](../../../CLAUDE.md) > [src](../../) > [agents](../) > **research**

# Research 模块 - 深度研究系统 (DR-in-KG 2.0)

> 最后更新：2026-03-17 11:33:36

## 变更记录 (Changelog)

### 2026-03-17
- 初始化模块文档

---

## 模块职责

Research 模块是一个基于**动态主题队列**架构的系统化深度研究系统，通过三阶段流水线（Planning → Researching → Reporting）实现多智能体协作的学术研究。

**核心能力**：
- 动态主题队列：替代静态树结构，灵活调度研究任务
- 三阶段流水线：规划、研究、报告生成
- 多工具集成：RAG、Web Search、Paper Search、Code Execution
- 引用系统：可点击的内联引用与锚点链接
- 并行执行：支持串行/并行两种执行模式
- 断点续跑：完整的状态持久化

---

## 入口与启动

### CLI 启动

```bash
# 快速模式（5-10 分钟）
python src/agents/research/main.py --topic "Deep Learning Basics" --preset quick

# 中等模式（平衡深度）
python src/agents/research/main.py --topic "Transformer Architecture" --preset medium

# 深度模式（彻底研究）
python src/agents/research/main.py --topic "Graph Neural Networks" --preset deep

# 自动模式（Agent 决定深度）
python src/agents/research/main.py --topic "Reinforcement Learning" --preset auto
```

### Python API

```python
import asyncio
from src.agents.research import ResearchPipeline
from src.config import load_config
from src.services.llm import get_llm_config

async def main():
    config = load_config()
    llm_config = get_llm_config()

    pipeline = ResearchPipeline(
        config=config,
        api_key=llm_config["api_key"],
        base_url=llm_config["base_url"],
        kb_name="ai_textbook",
        progress_callback=lambda event: print(f"Progress: {event}")
    )

    result = await pipeline.run(topic="Attention Mechanisms")
    print(f"Report: {result['final_report_path']}")

asyncio.run(main())
```

### WebSocket API

```javascript
const ws = new WebSocket('ws://localhost:8001/api/v1/research/run');
ws.onopen = () => {
  ws.send(JSON.stringify({
    topic: "Your research topic",
    preset: "medium"
  }));
};
```

---

## 对外接口

### ResearchPipeline

**主流水线编排器**，协调三阶段执行。

**方法**：
```python
async def run(
    topic: str,
    preset: str = "medium"
) -> Dict[str, Any]
```

**返回值**：
```python
{
    "final_report_path": str,      # Markdown 报告路径
    "metadata_path": str,          # 元数据路径
    "queue_state": Dict,           # 队列最终状态
    "token_usage": Dict,           # Token 使用统计
    "execution_time": float        # 执行时间（秒）
}
```

### Planning Phase Agents

**RephraseAgent**：
- 优化用户输入的主题
- 支持多轮用户交互
- 输出：优化后的研究主题

**DecomposeAgent**：
- 将主题分解为子主题
- 支持 Manual 和 Auto 两种模式
- 输出：子主题列表

### Researching Phase Agents

**ManagerAgent**：
- 队列调度与任务分配
- 状态转换管理（PENDING → RESEARCHING → COMPLETED）
- 动态主题添加

**ResearchAgent**：
- 充分性检查（check_sufficiency）
- 查询计划生成（generate_query_plan）
- 动态主题发现

**NoteAgent**：
- 信息压缩
- ToolTrace 创建
- 引用 ID 生成

### Reporting Phase Agents

**ReportingAgent**：
- 去重（deduplicate_blocks）
- 大纲生成（generate_outline）
- 报告撰写（write_report）

---

## 关键依赖与配置

### 依赖

**核心依赖**：
- `src/agents/base_agent.py` - Agent 基类
- `src/tools/rag_tool.py` - RAG 工具
- `src/tools/web_search.py` - Web 搜索
- `src/tools/paper_search.py` - 论文搜索
- `src/tools/run_code.py` - 代码执行

**配置文件**：
- `config/main.yaml` - 模块配置（research 部分）
- `config/agents.yaml` - Agent 参数

### 配置示例

**config/main.yaml**：
```yaml
research:
  # Planning Phase
  planning:
    rephrase:
      enabled: false
      max_iterations: 3
    decompose:
      mode: "auto"              # "manual" or "auto"
      initial_subtopics: 5      # For manual mode
      auto_max_subtopics: 8     # For auto mode

  # Researching Phase
  researching:
    execution_mode: "parallel"  # "series" or "parallel"
    max_parallel_topics: 5
    max_iterations: 5
    new_topic_min_score: 0.85

    # Tool switches
    enable_rag_hybrid: true
    enable_rag_naive: true
    enable_paper_search: true
    enable_web_search: true
    enable_run_code: true

  # Queue
  queue:
    max_length: 5
```

**config/agents.yaml**：
```yaml
research:
  temperature: 0.5
  max_tokens: 12000
```

---

## 数据模型

### TopicBlock

```python
@dataclass
class TopicBlock:
    block_id: str           # e.g., "block_1"
    sub_topic: str          # 主题标题
    overview: str           # 主题描述
    status: TopicStatus     # PENDING|RESEARCHING|COMPLETED|FAILED
    tool_traces: List[ToolTrace]  # 工具调用历史
    iteration_count: int    # 当前迭代次数
    created_at: str
    updated_at: str
    metadata: Dict
```

### ToolTrace

```python
@dataclass
class ToolTrace:
    tool_id: str            # 唯一 ID（基于时间戳）
    citation_id: str        # 引用参考（e.g., CIT-3-01）
    tool_type: str          # 工具名称
    query: str              # 发出的查询
    raw_answer: str         # 完整工具响应
    summary: str            # 压缩摘要
    timestamp: str
```

### DynamicTopicQueue

```python
class DynamicTopicQueue:
    research_id: str
    blocks: List[TopicBlock]
    max_length: Optional[int]

    # Methods
    add_block(sub_topic, overview) -> TopicBlock
    get_pending_block() -> Optional[TopicBlock]
    mark_researching(block_id) -> bool
    mark_completed(block_id) -> bool
    has_topic(sub_topic) -> bool
    get_statistics() -> Dict
```

---

## 测试与质量

### 单元测试

**测试文件**：`tests/agents/research/`（待添加）

**运行测试**：
```bash
pytest tests/agents/research/ -v
```

### 质量工具

- Linter：Ruff
- Formatter：Black / Ruff Format
- Type Checker：MyPy（宽松模式）

---

## 常见问题 (FAQ)

**Q: ModuleNotFoundError: research_pipeline**

A: 从项目根目录运行：
```bash
python src/agents/research/main.py --topic "..." --preset quick
```

**Q: 如何使用不同的知识库？**

A:
```bash
# 通过 CLI（使用配置默认值）
# 编辑 config/main.yaml: research.rag.kb_name

# 通过 Python API
pipeline = ResearchPipeline(..., kb_name="my_kb")
```

**Q: 如何启用/禁用特定工具？**

A: 编辑 `config/main.yaml`：
```yaml
research:
  researching:
    enable_web_search: false
    enable_paper_search: false
```

**Q: 如何调整子主题数量？**

A: 编辑 `config/main.yaml`：
```yaml
research:
  planning:
    decompose:
      mode: "manual"
      initial_subtopics: 8  # 增加到 8 个
```

---

## 相关文件清单

### 核心文件

- `main.py` - CLI 入口点
- `research_pipeline.py` - 三阶段流水线编排
- `data_structures.py` - TopicBlock、ToolTrace、DynamicTopicQueue

### Agents

- `agents/rephrase_agent.py` - 主题优化
- `agents/decompose_agent.py` - 子主题分解
- `agents/manager_agent.py` - 队列管理
- `agents/research_agent.py` - 研究决策
- `agents/note_agent.py` - 信息压缩
- `agents/reporting_agent.py` - 报告生成

### Prompts

- `prompts/en/` - 英文 Prompts
- `prompts/cn/` - 中文 Prompts

### 工具

- `utils/citation_manager.py` - 引用 ID 管理
- `utils/json_utils.py` - JSON 解析工具
- `utils/token_tracker.py` - Token 使用跟踪

---

## 输出文件

```
data/user/research/
├── reports/
│   ├── research_YYYYMMDD_HHMMSS.md      # 最终 Markdown 报告
│   └── research_*_metadata.json          # 统计与元数据
└── cache/
    └── research_YYYYMMDD_HHMMSS/
        ├── queue.json                    # DynamicTopicQueue 状态
        ├── citations.json                # 引用注册表
        ├── step1_planning.json           # 规划结果
        ├── planning_progress.json        # 规划事件
        ├── researching_progress.json     # 研究事件
        ├── reporting_progress.json       # 报告事件
        ├── outline.json                  # 报告大纲
        └── token_cost_summary.json       # Token 使用
```

---

## Preset 模式

| Preset | 子主题数 | 迭代次数 | 模式 | 用例 |
|:---:|:---:|:---:|:---:|:---:|
| `quick` | 1 | 1 | Fixed | 快速概览 |
| `medium` | 5 | 4 | Fixed | 平衡深度 |
| `deep` | 8 | 7 | Fixed | 彻底研究 |
| `auto` | ≤8 | ≤6 | Flexible | Agent 决定 |

---

**详细文档**：[README.md](README.md)
