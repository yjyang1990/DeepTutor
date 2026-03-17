[根目录](../../../CLAUDE.md) > [src](../../) > [agents](../) > **chat**

# Chat 模块 - 多轮对话系统

> 最后更新：2026-03-17 11:33:36

## 变更记录 (Changelog)

### 2026-03-17
- 初始化模块文档

---

## 模块职责

Chat 模块是一个轻量级的对话 AI 模块，支持多轮对话、会话管理、RAG 集成和 Web 搜索增强。

**核心能力**：
- 多轮对话：维护对话历史作为 LLM 上下文
- Token 管理：自动截断历史以适应 Token 限制
- RAG 集成：可选的知识库检索
- Web 搜索：可选的 Web 搜索获取最新信息
- 会话管理：持久化存储聊天会话
- 流式支持：通过 WebSocket 实时响应流

---

## 入口与启动

### Python API

```python
from src.agents.chat import ChatAgent, SessionManager

# 初始化 Agent
agent = ChatAgent(language="en")

# 处理消息
response = await agent.process(
    message="What is backpropagation?",
    history=[
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi! How can I help?"}
    ],
    kb_name="ai_textbook",
    enable_rag=True,
    enable_web_search=False
)

# 会话管理
session_mgr = SessionManager()
session = session_mgr.create_session("First question")
session_mgr.update_session(session["session_id"], messages)
```

### WebSocket API

```javascript
const ws = new WebSocket('ws://localhost:8001/api/v1/chat');
ws.onopen = () => {
  ws.send(JSON.stringify({
    message: "Your question",
    history: [],
    kb_name: "ai_textbook",
    enable_rag: true
  }));
};
```

---

## 对外接口

### ChatAgent

**主对话 Agent**，处理多轮对话。

**方法**：
```python
async def process(
    message: str,
    history: List[Dict[str, str]] = None,
    kb_name: Optional[str] = None,
    enable_rag: bool = False,
    enable_web_search: bool = False
) -> str
```

**参数**：
- `message`：用户消息
- `history`：对话历史（`[{"role": "user|assistant", "content": "..."}]`）
- `kb_name`：知识库名称（如果 `enable_rag=True`）
- `enable_rag`：是否启用 RAG 增强
- `enable_web_search`：是否启用 Web 搜索

**返回值**：
- `str`：Assistant 的回复

### SessionManager

**会话管理器**，管理聊天会话。

**方法**：
```python
def create_session(first_message: str) -> Dict[str, Any]
def update_session(session_id: str, messages: List[Dict]) -> None
def get_session(session_id: str) -> Optional[Dict[str, Any]]
def list_sessions(limit: int = 10) -> List[Dict[str, Any]]
def delete_session(session_id: str) -> bool
```

**会话结构**：
```python
{
    "session_id": str,
    "title": str,
    "created_at": str,
    "updated_at": str,
    "messages": List[Dict[str, str]]
}
```

---

## 关键依赖与配置

### 依赖

**核心依赖**：
- `src/agents/base_agent.py` - Agent 基类
- `src/tools/rag_tool.py` - RAG 工具
- `src/tools/web_search.py` - Web 搜索
- `src/services/llm/` - LLM 服务

**配置文件**：
- `config/agents.yaml` - Agent 参数
- `prompts/en/chat_agent.yaml` - 英文 Prompts
- `prompts/zh/chat_agent.yaml` - 中文 Prompts

### 配置示例

**config/agents.yaml**：
```yaml
chat:
  temperature: 0.7
  max_tokens: 2048
  max_history_tokens: 4096  # Token 限制
```

---

## 数据模型

### Message

```python
{
    "role": str,      # "user" or "assistant"
    "content": str    # 消息内容
}
```

### Session

```python
{
    "session_id": str,
    "title": str,
    "created_at": str,
    "updated_at": str,
    "messages": List[Message]
}
```

---

## 测试与质量

### 单元测试

**测试文件**：`tests/agents/chat/`（待添加）

**运行测试**：
```bash
pytest tests/agents/chat/ -v
```

### 质量工具

- Linter：Ruff
- Formatter：Black / Ruff Format
- Type Checker：MyPy（宽松模式）

---

## 常见问题 (FAQ)

**Q: 如何调整历史 Token 限制？**

A: 在 `config/agents.yaml` 中设置 `chat.max_history_tokens`。

**Q: 如何启用 RAG 增强？**

A:
```python
response = await agent.process(
    message="...",
    kb_name="ai_textbook",
    enable_rag=True
)
```

**Q: 如何查看会话列表？**

A:
```python
session_mgr = SessionManager()
sessions = session_mgr.list_sessions(limit=10)
```

**Q: 会话存储在哪里？**

A: `data/user/chat_sessions.json`

---

## 相关文件清单

### 核心文件

- `chat_agent.py` - 主对话 Agent
- `session_manager.py` - 会话管理器

### Prompts

- `prompts/en/chat_agent.yaml` - 英文 Prompts
- `prompts/zh/chat_agent.yaml` - 中文 Prompts

---

## 输出文件

```
data/user/
└── chat_sessions.json  # 所有会话的持久化存储
```

---

**详细文档**：[README.md](README.md)
