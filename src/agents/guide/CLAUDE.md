[根目录](../../../CLAUDE.md) > [src](../../) > [agents](../) > **guide**

# Guide 模块 - 引导式学习系统

> 最后更新：2026-03-17 11:33:36

## 变更记录 (Changelog)

### 2026-03-17
- 初始化模块文档

---

## 模块职责

Guide 模块是一个基于笔记本内容的个性化学习系统，通过分析笔记本记录生成渐进式知识点学习计划，并通过交互式页面和智能问答帮助用户逐步掌握所有内容。

**核心能力**：
- 智能知识点定位：分析笔记本记录，识别核心知识点
- 学习进度管理：跟踪当前学习状态，管理知识点转换
- 交互式页面生成：将知识点转换为可视化、交互式 HTML 页面
- 智能问答助手：在学习过程中回答用户问题
- 学习总结生成：完成所有知识点后生成个性化学习总结

---

## 入口与启动

### REST API

```bash
# 创建学习会话
POST /api/v1/guide/create_session
{
  "notebook_id": "notebook_123"
}

# 开始学习
POST /api/v1/guide/start
{
  "session_id": "session_456"
}

# 移动到下一个知识点
POST /api/v1/guide/next
{
  "session_id": "session_456"
}

# 发送聊天消息
POST /api/v1/guide/chat
{
  "session_id": "session_456",
  "message": "Can you explain this concept?"
}

# 修复 HTML 页面
POST /api/v1/guide/fix_html
{
  "session_id": "session_456",
  "error_description": "Button not working"
}
```

### WebSocket

```javascript
const ws = new WebSocket('ws://localhost:8001/api/v1/guide/ws/session_456');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  // 处理实时交互
};
```

---

## 对外接口

### GuideManager

**会话管理器**，包含学习进度管理逻辑。

**方法**：
```python
def create_session(notebook_id: str) -> Dict[str, Any]
def get_session(session_id: str) -> Optional[Dict[str, Any]]
def update_session(session_id: str, updates: Dict) -> None
def delete_session(session_id: str) -> bool
```

### LocateAgent

**知识点定位 Agent**，分析笔记本内容。

**方法**：
```python
async def process(
    records: List[Dict[str, Any]]
) -> List[Dict[str, Any]]
```

**返回值**：
```python
[
    {
        "title": str,           # 知识点标题
        "description": str,     # 知识点描述
        "order": int            # 学习顺序
    },
    ...
]
```

### InteractiveAgent

**交互式页面生成 Agent**，将知识点转换为 HTML。

**方法**：
```python
async def process(
    knowledge_point: Dict[str, Any],
    context: str
) -> str  # HTML content
```

### ChatAgent

**问答 Agent**，在学习过程中回答问题。

**方法**：
```python
async def process(
    message: str,
    knowledge_point: Dict[str, Any],
    chat_history: List[Dict[str, str]]
) -> str
```

### SummaryAgent

**总结生成 Agent**，完成学习后生成总结。

**方法**：
```python
async def process(
    knowledge_points: List[Dict[str, Any]],
    chat_history: List[Dict[str, str]]
) -> str
```

---

## 关键依赖与配置

### 依赖

**核心依赖**：
- `src/agents/base_agent.py` - Agent 基类
- `src/api/utils/notebook_manager.py` - 笔记本管理
- `src/services/llm/` - LLM 服务

**配置文件**：
- `config/agents.yaml` - Agent 参数
- `prompts/zh/` - 中文 Prompts
- `prompts/en/` - 英文 Prompts（可选）

### 配置示例

**config/agents.yaml**：
```yaml
guide:
  temperature: 0.7
  max_tokens: 4096
```

---

## 数据模型

### Session

```python
{
    "session_id": str,
    "notebook_id": str,
    "knowledge_points": List[Dict],
    "current_index": int,
    "current_html": str,
    "chat_history": List[Dict],
    "status": str,  # "planning" | "learning" | "completed"
    "created_at": str,
    "updated_at": str
}
```

### Knowledge Point

```python
{
    "title": str,
    "description": str,
    "order": int,
    "html": Optional[str],
    "chat_history": List[Dict]
}
```

---

## 测试与质量

### 单元测试

**测试文件**：`tests/agents/guide/`（待添加）

**运行测试**：
```bash
pytest tests/agents/guide/ -v
```

### 质量工具

- Linter：Ruff
- Formatter：Black / Ruff Format
- Type Checker：MyPy（宽松模式）

---

## 常见问题 (FAQ)

**Q: 如何调整知识点数量？**

A: 系统自动生成 3-5 个知识点，无需手动配置。

**Q: HTML 生成有问题怎么办？**

A: 使用 Debug 功能（`/api/v1/guide/fix_html`）修复。

**Q: 聊天历史如何管理？**

A: 每个知识点的聊天历史独立，便于上下文管理。

**Q: 会话数据存储在哪里？**

A: `data/user/guide/session_{session_id}.json`

**Q: 如何自定义 Prompt？**

A: 编辑 `prompts/zh/` 或 `prompts/en/` 中的 YAML 文件。

---

## 相关文件清单

### 核心文件

- `guide_manager.py` - 会话管理器
- `agents/locate_agent.py` - 知识点定位
- `agents/interactive_agent.py` - 交互式页面生成
- `agents/chat_agent.py` - 问答 Agent
- `agents/summary_agent.py` - 总结生成

### Prompts

- `prompts/zh/` - 中文 Prompts
  - `locate_agent.yaml`
  - `interactive_agent.yaml`
  - `chat_agent.yaml`
  - `summary_agent.yaml`
- `prompts/en/` - 英文 Prompts（可选）

---

## 输出文件

```
data/user/guide/
└── session_{session_id}.json  # 会话状态
```

---

## 使用流程

1. **选择笔记本**：用户在前端选择包含记录的笔记本
2. **生成学习计划**：LocateAgent 分析笔记本内容，生成 3-5 个渐进式知识点
3. **开始学习**：用户点击"开始学习"，系统为第一个知识点生成交互式页面
4. **学习交互**：用户可在左侧聊天框提问，ChatAgent 基于当前知识点回答
5. **完成学习**：完成所有知识点后，系统生成学习总结

---

**详细文档**：[README.md](README.md)
