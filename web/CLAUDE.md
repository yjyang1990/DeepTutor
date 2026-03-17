[根目录](../CLAUDE.md) > **web**

# Web 前端 - Next.js 应用

> 最后更新：2026-03-17 11:33:36

## 变更记录 (Changelog)

### 2026-03-17
- 初始化模块文档

---

## 模块职责

Web 前端是一个 Next.js 16 应用，为 DeepTutor 系统提供用户界面。

**核心能力**：
- 仪表板与活动跟踪
- 知识库管理
- 问题求解界面
- 题目生成界面
- 研究界面
- 引导式学习界面
- Co-Writer 界面
- 笔记本管理
- 创意生成界面

---

## 入口与启动

### 安装依赖

```bash
cd web
npm install
```

### 开发模式

```bash
npm run dev
```

使用 **Turbopack** 默认启用，提供更快的开发构建。

前端将在 `http://localhost:3782` 可用（或 `config/main.yaml` 中配置的端口）。

### 构建

```bash
npm run build
npm start
```

---

## 对外接口

### 页面路由

- `/` - 仪表板（主页）
- `/knowledge` - 知识库管理
- `/solver` - 问题求解
- `/question` - 题目生成
- `/research` - 研究
- `/guide` - 引导式学习
- `/co_writer` - Co-Writer
- `/notebook` - 笔记本
- `/ideagen` - 创意生成
- `/settings` - 设置
- `/history` - 历史记录

### API 客户端

**REST API**：
```typescript
import { apiUrl } from "@/lib/api";

const response = await fetch(`${apiUrl}/knowledge/list`);
const data = await response.json();
```

**WebSocket**：
```typescript
import { wsUrl } from "@/lib/api";

const ws = new WebSocket(`${wsUrl}/api/v1/solve`);
ws.onopen = () => {
  ws.send(JSON.stringify({
    question: "Your question",
    kb_name: "ai_textbook",
  }));
};
```

---

## 关键依赖与配置

### 依赖

**核心依赖**：
- Next.js 16.1.1
- React 19.0.0
- TypeScript 5
- Tailwind CSS 3.4
- Lucide React（图标）
- Framer Motion 12（动画）
- react-markdown + KaTeX（Markdown 渲染）
- i18next + react-i18next（国际化）

**配置文件**：
- `package.json` - 依赖与脚本
- `tsconfig.json` - TypeScript 配置
- `tailwind.config.js` - Tailwind CSS 配置
- `next.config.js` - Next.js 配置

### 配置示例

**环境变量（.env.local）**：
```bash
NEXT_PUBLIC_API_BASE=http://localhost:8001
NEXT_PUBLIC_WS_BASE=ws://localhost:8001
```

**next.config.js**：
```javascript
const nextConfig = {
  devIndicators: {
    position: "bottom-right",
  },
  turbopack: {
    resolveAlias: {
      cytoscape: "cytoscape/dist/cytoscape.cjs.js",
    },
  },
  transpilePackages: ["mermaid"],
};
```

---

## 数据模型

### API 响应

**成功**：
```typescript
{
  success: true,
  data: {...}
}
```

**错误**：
```typescript
{
  success: false,
  error: string
}
```

### WebSocket 消息

**客户端 → 服务器**：
```typescript
{
  question: string,
  kb_name: string
}
```

**服务器 → 客户端**：
```typescript
{
  type: "progress" | "result" | "error",
  content: string,
  data?: any
}
```

---

## 测试与质量

### E2E 测试

**测试框架**：Playwright

**测试文件**：`tests/e2e/`

**运行测试**：
```bash
npm run audit        # 运行 UI 审计测试
npm run audit:ui     # 交互式 UI 模式
npm run audit:report # 查看报告
```

### 质量工具

- Linter：ESLint
- Formatter：Prettier
- Type Checker：TypeScript Compiler

---

## 常见问题 (FAQ)

**Q: 如何添加新页面？**

A:
1. 在 `app/` 中创建页面目录和 `page.tsx`
2. 在 `components/Sidebar.tsx` 中添加导航链接

**Q: 如何添加新组件？**

A:
1. 在 `components/` 中创建组件文件
2. 如需要，从 `components/index.ts` 导出

**Q: 如何配置 API URL？**

A: 在 `web/.env.local` 中设置 `NEXT_PUBLIC_API_BASE` 和 `NEXT_PUBLIC_WS_BASE`。

**Q: 如何查看国际化翻译？**

A: 翻译文件位于 `locales/en/` 和 `locales/zh/`。

**Q: 如何调试 WebSocket 连接？**

A:
```typescript
ws.onmessage = (event) => {
  console.log("WS Message:", JSON.parse(event.data));
};
```

---

## 相关文件清单

### 核心文件

- `app/layout.tsx` - 根布局
- `app/page.tsx` - 仪表板（主页）
- `app/globals.css` - 全局样式

### 页面

- `app/knowledge/page.tsx` - 知识库页面
- `app/solver/page.tsx` - 问题求解页面
- `app/question/page.tsx` - 题目生成页面
- `app/research/page.tsx` - 研究页面
- `app/guide/page.tsx` - 引导式学习页面
- `app/co_writer/page.tsx` - Co-Writer 页面
- `app/notebook/page.tsx` - 笔记本页面
- `app/ideagen/page.tsx` - 创意生成页面
- `app/settings/page.tsx` - 设置页面

### 组件

- `components/Sidebar.tsx` - 导航侧边栏
- `components/SystemStatus.tsx` - 系统状态指示器
- `components/ActivityDetail.tsx` - 活动详情视图
- `components/CoWriterEditor.tsx` - Co-Writer 编辑器
- `components/AddToNotebookModal.tsx` - 添加到笔记本模态框
- `components/ui/` - UI 组件
  - `Button.tsx`
  - `Modal.tsx`

### Context

- `context/GlobalContext.tsx` - 全局状态管理
- `context/CompositeProvider.tsx` - 组合 Provider
- `context/chat/ChatContext.tsx` - 聊天上下文
- `context/question/QuestionContext.tsx` - 题目上下文
- `context/research/ResearchContext.tsx` - 研究上下文
- `context/solver/SolverContext.tsx` - 求解器上下文
- `context/settings/` - 设置上下文

### 工具

- `lib/api.ts` - API 客户端
- `lib/datetime.ts` - 日期时间工具
- `lib/latex.ts` - LaTeX 工具
- `lib/pdfExport.ts` - PDF 导出
- `lib/theme.ts` - 主题工具

### 国际化

- `i18n/index.ts` - i18n 配置
- `i18n/init.ts` - i18n 初始化
- `locales/en/` - 英文翻译
- `locales/zh/` - 中文翻译

---

## 样式指南

### Tailwind CSS

项目使用 Tailwind CSS 进行样式设计。配置在 `tailwind.config.js`。

### 全局样式

全局样式在 `app/globals.css` 中，包括：
- 基础样式
- 自定义 CSS 变量
- 工具类

### 组件样式

- 使用 Tailwind CSS 工具类
- 遵循现有组件模式
- 使用 Lucide React 图标
- 保持响应式设计

---

## 开发指南

### 添加新页面

1. 在 `app/` 中创建页面：
   ```typescript
   // app/my-page/page.tsx
   export default function MyPage() {
     return <div>My Page</div>
   }
   ```

2. 在 `components/Sidebar.tsx` 中添加导航链接

### 添加新组件

1. 在 `components/` 中创建组件：
   ```typescript
   // components/MyComponent.tsx
   export default function MyComponent() {
     return <div>My Component</div>
   }
   ```

2. 如需要，从 `components/index.ts` 导出

### 样式指南

- 使用 Tailwind CSS 工具类
- 遵循现有组件模式
- 使用 Lucide React 图标
- 保持响应式设计

---

## 注意事项

1. **API URL**：确保 API 基础 URL 与后端配置匹配
2. **WebSocket**：生产环境应使用 `wss://`（本地开发使用 `ws://`）
3. **CORS**：后端必须在 CORS 设置中允许前端源
4. **环境变量**：客户端变量使用 `NEXT_PUBLIC_` 前缀
5. **Turbopack**：开发模式默认使用 Turbopack 以加快构建速度

---

**详细文档**：[README.md](README.md)
