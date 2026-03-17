[根目录](../../CLAUDE.md) > [src](../) > **api**

# API 模块 - FastAPI 后端服务

> 最后更新：2026-03-17 11:33:36

## 变更记录 (Changelog)

### 2026-03-17
- 初始化模块文档

---

## 模块职责

API 模块基于 FastAPI 构建，提供 REST 和 WebSocket 端点，实现前后端通信和实时流式传输。

**核心能力**：
- REST API：标准 HTTP 请求端点
- WebSocket：实时流式传输
- 静态文件服务：生成的工件文件访问
- CORS 中间件：跨域请求支持
- 统一错误处理和日志记录

---

## 入口与启动

### 使用 run_server.py

```bash
python src/api/run_server.py
```

### 使用 uvicorn 直接启动

```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8001 --reload
```

### 使用 main.py

```bash
python src/api/main.py
```

---

## 对外接口

### WebSocket 端点

**Solve**：
```
WS /api/v1/solve
```

**Question**：
```
WS /api/v1/question/generate
```

**Research**：
```
WS /api/v1/research/run
```

**Guide**：
```
WS /api/v1/guide/ws/{session_id}
```

### REST 端点

**Knowledge**：
- `GET /api/v1/knowledge/list` - 列出知识库
- `GET /api/v1/knowledge/{kb_name}` - 获取知识库详情
- `POST /api/v1/knowledge/create` - 创建知识库
- `POST /api/v1/knowledge/{kb_name}/upload` - 上传文档

**Guide**：
- `POST /api/v1/guide/create_session` - 创建学习会话
- `POST /api/v1/guide/start` - 开始学习
- `POST /api/v1/guide/next` - 移动到下一个知识点
- `POST /api/v1/guide/chat` - 发送聊天消息

**Co-Writer**：
- `POST /api/v1/co_writer/edit` - 文本编辑
- `POST /api/v1/co_writer/automark` - 自动标注
- `POST /api/v1/co_writer/narrate` - 生成旁白

**Notebook**：
- `GET /api/v1/notebook/list` - 列出笔记本
- `POST /api/v1/notebook/create` - 创建笔记本
- `GET /api/v1/notebook/{id}` - 获取笔记本详情
- `PUT /api/v1/notebook/{id}` - 更新笔记本
- `DELETE /api/v1/notebook/{id}` - 删除笔记本

**Dashboard**：
- `GET /api/v1/dashboard/recent` - 获取最近活动

**System**：
- `GET /api/v1/system/health` - 健康检查

---

## 关键依赖与配置

### 依赖

**核心依赖**：
- FastAPI 0.100+
- Uvicorn（ASGI 服务器）
- WebSockets
- Python Multipart（文件上传）
- Pydantic（数据验证）

**内部依赖**：
- `src/agents/` - Agent 实现
- `src/tools/` - 工具实现
- `src/services/` - 服务层
- `src/config/` - 配置管理
- `src/logging/` - 日志系统

**配置文件**：
- `config/main.yaml` - 服务器配置

### 配置示例

**config/main.yaml**：
```yaml
server:
  backend_port: 8001
  frontend_port: 3782
```

**CORS 配置（main.py）**：
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应指定具体 URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 数据模型

### WebSocket 消息格式

**客户端 → 服务器**：
```json
{
  "question": "Your question",
  "kb_name": "ai_textbook"
}
```

**服务器 → 客户端**：
```json
{
  "type": "progress" | "result" | "error",
  "content": "...",
  "data": {...}
}
```

### REST 响应格式

**成功**：
```json
{
  "success": true,
  "data": {...}
}
```

**错误**：
```json
{
  "success": false,
  "error": "Error message"
}
```

---

## 测试与质量

### 单元测试

**测试文件**：`tests/api/`（待添加）

**运行测试**：
```bash
pytest tests/api/ -v
```

### 质量工具

- Linter：Ruff
- Formatter：Black / Ruff Format
- Type Checker：MyPy（宽松模式）

---

## 常见问题 (FAQ)

**Q: 如何添加新端点？**

A:
1. 在 `routers/` 中创建或更新路由文件
2. 在 `main.py` 中导入并注册路由

**Q: 如何添加 WebSocket 支持？**

A:
1. 在路由中创建 WebSocket 端点
2. 使用 `LogInterceptor` 进行流式日志传输

**Q: 静态文件如何访问？**

A: 通过 `/api/outputs/{module}/{path}` 访问 `data/user/{module}/{path}`。

**Q: 如何配置 CORS？**

A: 在 `main.py` 中修改 `CORSMiddleware` 配置。

**Q: 如何查看 API 文档？**

A: 启动服务器后访问 `http://localhost:8001/docs`。

---

## 相关文件清单

### 核心文件

- `main.py` - FastAPI 应用设置
- `run_server.py` - 服务器启动脚本

### 路由模块

- `routers/solve.py` - 问题求解端点
- `routers/question.py` - 题目生成端点
- `routers/research.py` - 研究端点
- `routers/knowledge.py` - 知识库端点
- `routers/guide.py` - 引导式学习端点
- `routers/co_writer.py` - Co-Writer 端点
- `routers/notebook.py` - 笔记本端点
- `routers/ideagen.py` - 创意生成端点
- `routers/dashboard.py` - 仪表板端点
- `routers/settings.py` - 设置端点
- `routers/system.py` - 系统端点

### 工具模块

- `utils/history.py` - 活动历史管理
- `utils/log_interceptor.py` - 日志拦截（流式传输）
- `utils/notebook_manager.py` - 笔记本管理
- `utils/progress_broadcaster.py` - 进度广播
- `utils/task_id_manager.py` - 任务 ID 管理

---

## 静态文件服务

**URL 模式**：`/api/outputs/{module}/{path}`

**物理路径**：`data/user/{module}/{path}`

**示例**：
- URL：`/api/outputs/solve/solve_20250101_120000/final_answer.md`
- 路径：`data/user/solve/solve_20250101_120000/final_answer.md`

---

## WebSocket 模式

所有 WebSocket 端点遵循相似模式：

1. **连接**：客户端连接到 WebSocket 端点
2. **初始消息**：客户端发送带参数的初始请求
3. **流式传输**：服务器流式传输进度更新和结果
4. **完成**：服务器发送最终结果并关闭连接

**示例（Solve）**：
```javascript
const ws = new WebSocket('ws://localhost:8001/api/v1/solve');
ws.onopen = () => {
  ws.send(JSON.stringify({
    question: "Your question here",
    kb_name: "ai_textbook"
  }));
};
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data);
};
```

---

**详细文档**：[README.md](README.md)
