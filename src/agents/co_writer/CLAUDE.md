[根目录](../../../CLAUDE.md) > [src](../../) > [agents](../) > **co_writer**

# Co-Writer 模块 - AI 文本编辑与旁白

> 最后更新：2026-03-17 11:33:36

## 变更记录 (Changelog)

### 2026-03-17
- 初始化模块文档

---

## 模块职责

Co-Writer 模块提供 AI 驱动的文本编辑和旁白功能，包括文本重写、自动标注和文本转语音（TTS）生成。

**核心能力**：
- 文本编辑：重写、缩短、扩展
- 上下文增强：可选的 RAG 或 Web 搜索上下文
- 自动标注：专业学术阅读标注
- TTS 旁白：将文本内容转换为旁白脚本并生成音频

---

## 入口与启动

### Python API - 文本编辑

```python
from src.agents.co_writer.edit_agent import EditAgent

agent = EditAgent()

# 使用 RAG 上下文重写
result = await agent.process(
    text="Original text...",
    instruction="Make it more formal",
    action="rewrite",
    source="rag",
    kb_name="ai_textbook"
)

print(result["edited_text"])
```

### Python API - TTS 旁白

```python
from src.agents.co_writer.narrator_agent import NarratorAgent

agent = NarratorAgent()

result = await agent.generate_narration(
    content="Your text content here...",
    voice="Cherry",
    language="English"
)

print(f"Audio URL: {result['audio_url']}")
```

### REST API

```bash
# 文本编辑
POST /api/v1/co_writer/edit
{
  "text": "Original text...",
  "instruction": "Make it more formal",
  "action": "rewrite",
  "source": "rag",
  "kb_name": "ai_textbook"
}

# 自动标注
POST /api/v1/co_writer/automark
{
  "text": "Academic text..."
}

# 生成旁白
POST /api/v1/co_writer/narrate
{
  "content": "Text to narrate...",
  "voice": "Cherry",
  "language": "English"
}
```

---

## 对外接口

### EditAgent

**文本编辑 Agent**，提供 AI 驱动的文本编辑功能。

**方法**：
```python
async def process(
    text: str,
    instruction: str,
    action: Literal["rewrite", "shorten", "expand"] = "rewrite",
    source: Optional[Literal["rag", "web"]] = None,
    kb_name: Optional[str] = None
) -> Dict[str, Any]
```

**返回值**：
```python
{
    "edited_text": str,        # 编辑后的文本
    "operation_id": str,       # 唯一操作 ID
    "tool_call_file": str      # 工具调用历史路径（如果使用了 source）
}
```

### NarratorAgent

**TTS 旁白 Agent**，将文本转换为旁白脚本并生成音频。

**方法**：
```python
async def generate_narration(
    content: str,
    voice: Optional[str] = None,
    language: Optional[str] = None
) -> Dict[str, Any]
```

**返回值**：
```python
{
    "audio_url": str,          # 生成的音频文件 URL
    "audio_path": str,          # 本地音频文件路径
    "script": str,              # 生成的旁白脚本
    "operation_id": str        # 唯一操作 ID
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
- DashScope TTS API - TTS 服务

**配置文件**：
- `config/main.yaml` - TTS 配置
- `config/agents.yaml` - Agent 参数
- `prompts/en/edit_agent.yaml` - 英文 Prompts
- `prompts/zh/edit_agent.yaml` - 中文 Prompts

### 配置示例

**config/main.yaml**：
```yaml
tts:
  default_voice: "Cherry"
  default_language: "English"
```

**环境变量（.env）**：
```bash
# DashScope TTS API
DASHSCOPE_API_KEY=your_dashscope_api_key
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/api/v1
DASHSCOPE_TTS_MODEL=sambert-zhichu-v1

# LLM API（用于 EditAgent）
LLM_API_KEY=your_api_key
LLM_HOST=https://api.openai.com/v1
LLM_MODEL=gpt-4o
```

---

## 数据模型

### Edit Request

```python
{
    "text": str,
    "instruction": str,
    "action": "rewrite" | "shorten" | "expand",
    "source": Optional["rag" | "web"],
    "kb_name": Optional[str]
}
```

### Narrate Request

```python
{
    "content": str,
    "voice": Optional[str],  # Cherry, Stella, Annie, Cally, Eva, Bella
    "language": Optional[str]  # English, Chinese
}
```

---

## 测试与质量

### 单元测试

**测试文件**：`tests/agents/co_writer/`（待添加）

**运行测试**：
```bash
pytest tests/agents/co_writer/ -v
```

### 质量工具

- Linter：Ruff
- Formatter：Black / Ruff Format
- Type Checker：MyPy（宽松模式）

---

## 常见问题 (FAQ)

**Q: 如何添加新的编辑动作？**

A:
1. 在 `edit_agent.py` 中添加动作类型到 `Literal` 类型提示
2. 在 `prompts/en/` 和 `prompts/zh/` 的 YAML 文件中添加对应 Prompts
3. 测试新动作

**Q: 如何添加新的 TTS 语音？**

A:
1. 查看 DashScope TTS API 文档获取可用语音
2. 在 `narrator_agent.py` 中更新语音验证
3. 更新 `config/main.yaml`（如需要）

**Q: TTS API Key 在哪里配置？**

A: 在 `.env` 或 `DeepTutor.env` 文件中配置 `DASHSCOPE_API_KEY`。

**Q: 音频文件存储在哪里？**

A: `data/user/co-writer/audio/`，通过 `/api/outputs/` 提供访问。

**Q: 如何查看工具调用历史？**

A: 所有 RAG/Web 搜索调用记录在 `data/user/co-writer/tool_calls/` 目录。

---

## 相关文件清单

### 核心文件

- `edit_agent.py` - 文本编辑 Agent
- `narrator_agent.py` - TTS 旁白 Agent

### Prompts

- `prompts/en/` - 英文 Prompts
  - `edit_agent.yaml`
  - `narrator_agent.yaml`
- `prompts/zh/` - 中文 Prompts
  - `edit_agent.yaml`
  - `narrator_agent.yaml`

---

## 输出文件

```
data/user/co-writer/
├── audio/                    # TTS 音频文件
│   └── {operation_id}.mp3
├── tool_calls/               # 工具调用历史
│   └── {operation_id}_{tool_type}.json
└── history.json              # 编辑历史
```

---

## 使用场景

### 1. 文本重写

```python
result = await edit_agent.process(
    text="The quick brown fox jumps over the lazy dog.",
    instruction="Make it more academic and formal",
    action="rewrite"
)
```

### 2. 文本压缩

```python
result = await edit_agent.process(
    text="Long text content...",
    instruction="Summarize to 50 words",
    action="shorten"
)
```

### 3. 文本扩展

```python
result = await edit_agent.process(
    text="Brief description...",
    instruction="Add more technical details",
    action="expand",
    source="rag",
    kb_name="ai_textbook"
)
```

### 4. 音频旁白

```python
result = await narrator_agent.generate_narration(
    content="Your educational content...",
    voice="Cherry",
    language="English"
)
```

---

**详细文档**：[README.md](README.md)
