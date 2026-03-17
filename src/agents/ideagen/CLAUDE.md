[根目录](../../../CLAUDE.md) > [src](../../) > [agents](../) > **ideagen**

# IdeaGen 模块 - 研究创意生成系统

> 最后更新：2026-03-17 11:33:36

## 变更记录 (Changelog)

### 2026-03-17
- 初始化模块文档

---

## 模块职责

IdeaGen 模块从笔记本记录中提取知识点，并通过多阶段过滤和探索工作流生成研究创意。

**核心能力**：
- 知识点提取：从笔记本记录中提取核心知识点
- 宽松过滤：移除明显不适合的知识点
- 创意探索：为每个知识点生成至少 5 个研究创意
- 严格过滤：严格评估研究创意（至少保留 1 个，至少淘汰 2 个）
- Markdown 组织：将最终创意组织为结构化 Markdown

---

## 入口与启动

### Python API

```python
from src.agents.ideagen.material_organizer_agent import MaterialOrganizerAgent
from src.agents.ideagen.idea_generation_workflow import IdeaGenerationWorkflow

# 1. 提取知识点
organizer = MaterialOrganizerAgent()
records = [...]  # 笔记本记录
knowledge_points = await organizer.process(records, user_thoughts="Focus on ML")

# 2. 生成创意
workflow = IdeaGenerationWorkflow(
    progress_callback=print  # 可选进度回调
)

# 宽松过滤
filtered_points = await workflow.loose_filter(knowledge_points)

# 为每个知识点探索创意
ideas_map = {}
for point in filtered_points:
    ideas = await workflow.explore_ideas(point)
    filtered_ideas = await workflow.strict_filter(point, ideas)
    ideas_map[point["knowledge_point"]] = filtered_ideas

# 生成 Markdown
markdown = await workflow.generate_markdown(filtered_points, ideas_map)
```

### REST API

```bash
POST /api/v1/ideagen/generate
{
  "notebook_id": "notebook_123",
  "user_thoughts": "Optional user thoughts and preferences"
}
```

---

## 对外接口

### MaterialOrganizerAgent

**知识点提取 Agent**，从笔记本记录中提取核心知识点。

**方法**：
```python
async def process(
    records: List[Dict[str, Any]],
    user_thoughts: Optional[str] = None
) -> List[Dict[str, Any]]
```

**返回值**：
```python
[
    {
        "knowledge_point": str,      # 知识点名称
        "description": str            # 系统响应中的描述
    },
    ...
]
```

### IdeaGenerationWorkflow

**创意生成工作流编排器**，协调多阶段过滤和探索。

**方法**：

**1. 宽松过滤**：
```python
async def loose_filter(
    knowledge_points: List[Dict[str, Any]]
) -> List[Dict[str, Any]]
```

**2. 探索创意**：
```python
async def explore_ideas(
    knowledge_point: Dict[str, Any]
) -> List[str]  # 至少 5 个创意
```

**3. 严格过滤**：
```python
async def strict_filter(
    knowledge_point: Dict[str, Any],
    research_ideas: List[str]
) -> List[str]  # 至少保留 1 个，至少淘汰 2 个
```

**4. 生成 Markdown**：
```python
async def generate_markdown(
    knowledge_points: List[Dict[str, Any]],
    ideas_map: Dict[str, List[str]]
) -> str
```

---

## 关键依赖与配置

### 依赖

**核心依赖**：
- `src/agents/base_agent.py` - Agent 基类（通过 BaseIdeaAgent）
- `src/api/utils/notebook_manager.py` - 笔记本记录管理
- `src/services/llm/` - LLM 服务

**配置文件**：
- `config/agents.yaml` - Agent 参数
- `prompts/en/` - 英文 Prompts
- `prompts/zh/` - 中文 Prompts

### 配置示例

**config/agents.yaml**：
```yaml
ideagen:
  temperature: 0.7
  max_tokens: 4096
```

---

## 数据模型

### Knowledge Point

```python
{
    "knowledge_point": str,      # 知识点名称
    "description": str            # 描述
}
```

### Research Idea

```python
str  # 研究创意描述
```

### Ideas Map

```python
{
    "knowledge_point_1": List[str],  # 该知识点的研究创意列表
    "knowledge_point_2": List[str],
    ...
}
```

---

## 测试与质量

### 单元测试

**测试文件**：`tests/agents/ideagen/`（待添加）

**运行测试**：
```bash
pytest tests/agents/ideagen/ -v
```

### 质量工具

- Linter：Ruff
- Formatter：Black / Ruff Format
- Type Checker：MyPy（宽松模式）

---

## 常见问题 (FAQ)

**Q: 如何调整每个知识点的创意数量？**

A: 编辑 `prompts/en/idea_generation.yaml` 或 `prompts/zh/idea_generation.yaml` 中的 `explore_ideas_user_template`，修改"至少 5 个"为其他数量。

**Q: 如何自定义过滤标准？**

A: 编辑 Prompt YAML 文件中的 `loose_filter_system` 和 `strict_filter_system`。

**Q: 如何添加进度回调？**

A:
```python
async def progress_callback(stage: str, data: Any):
    print(f"Stage: {stage}, Data: {data}")

workflow = IdeaGenerationWorkflow(progress_callback=progress_callback)
```

**Q: 如何查看统计信息？**

A:
```python
from src.agents.ideagen.base_idea_agent import BaseIdeaAgent
BaseIdeaAgent.print_stats()
```

---

## 相关文件清单

### 核心文件

- `base_idea_agent.py` - Agent 基类
- `material_organizer_agent.py` - 知识点提取
- `idea_generation_workflow.py` - 工作流编排

### Prompts

- `prompts/zh/` - 中文 Prompts
  - `material_organizer.yaml`
  - `idea_generation.yaml`
- `prompts/en/` - 英文 Prompts
  - `material_organizer.yaml`
  - `idea_generation.yaml`

---

## 输出格式

最终 Markdown 输出包括：

```markdown
# 研究创意

## 知识点 1
描述：...

### 研究创意
1. 创意 1...
2. 创意 2...

## 知识点 2
...
```

---

## 工作流

```
笔记本记录
    ↓
MaterialOrganizerAgent → 提取知识点
    ↓
IdeaGenerationWorkflow.loose_filter → 过滤知识点
    ↓
IdeaGenerationWorkflow.explore_ideas → 生成研究创意（≥5 个/知识点）
    ↓
IdeaGenerationWorkflow.strict_filter → 严格过滤创意（保留 ≥1，淘汰 ≥2）
    ↓
IdeaGenerationWorkflow.generate_markdown → 生成最终 Markdown
```

---

**详细文档**：[README.md](README.md)
