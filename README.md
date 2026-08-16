# AI Agent Workspace

AI Agent Workspace 是一个可视化、可追踪、可扩展的单 Agent 工作空间。用户提交任务后，Agent 可以通过 LLM 判断是否需要工具，选择并执行工具，维护运行状态，展示执行 Trace，并生成最终结果。

项目重点不是继续做普通聊天机器人，而是把 Agent Runtime 的核心机制跑通并讲清楚：

- Tool Calling
- Agent Loop
- State
- Workflow
- Human-in-the-loop
- Evaluation
- MCP

## 当前状态

- 项目文档已根据开发方案整理完成。
- GitHub 仓库已连接到 `https://github.com/cesuogaoshou/ai-agent-workspace.git`。
- `docs/` 和 `agent/` 按当前约定作为本地文档目录，不再进入 Git 跟踪。
- 应用源码尚未创建。
- 下一步建议进入 v0.1 Minimal Agent，实现最小可运行后端/API 和工具调用闭环。

## 技术方向

前端：

- Vue 3
- TypeScript
- Vite
- Pinia
- Vue Router
- Element Plus

后端：

- Python
- FastAPI
- Pydantic
- SQLAlchemy
- SQLite
- Uvicorn
- httpx

LLM：

- 统一 LLM Provider 层
- 第一阶段至少接入一个支持 Tool Calling 的模型
- 预留 OpenAI、DeepSeek 和 OpenAI-compatible Provider 扩展

## 版本路线

```text
v0.1 Minimal Agent
  -> Tool Calling / Tool Registry / Agent Loop / 基础工具

v0.2 Agent Loop + Execution Trace
  -> 多步骤执行 / Tool Call Trace / SSE 实时事件

v0.3 Persistence
  -> SQLite / SQLAlchemy / 历史 Run 和 Step

v0.4 LangGraph
  -> 显式 State / Node / Edge / Conditional Edge

v0.5 Human-in-the-loop
  -> 敏感工具调用审批

v0.6 Memory / State
  -> 短期状态和 SQLite 长期记录

v0.7 Agent Evaluation
  -> 固定评估集和量化指标

v0.8 MCP
  -> 迁移一到两个工具为 MCP Server

v1.0 Project Freeze
  -> Docker / Tests / CI / Demo / 完整项目展示
```

## 推荐实现结构

```text
frontend/
  src/
    api/
    components/
    views/
    stores/
    router/
    types/
    utils/
  package.json

backend/
  app/
    api/
    agent/
    tools/
    llm/
    models/
    schemas/
    services/
    db/
    main.py
  tests/
  evaluation/
  requirements.txt

docker-compose.yml
.env.example
```

## 文档

本地文档位于 `docs/`，包括：

- `docs/PROJECT_INDEX.md`
- `docs/BACKGROUND.md`
- `docs/REQUIREMENTS.md`
- `docs/ARCHITECTURE.md`
- `docs/API.md`
- `docs/ROADMAP.md`

AI 工作文档位于 `agent/`，用于记录任务、交接、操作日志和决策。`docs/` 与 `agent/` 默认不进入 Git。

## 本地运行

应用尚未实现，因此暂无安装、启动、测试和构建命令。进入 v0.1 后应补充：

- 后端依赖安装命令
- 后端启动命令
- 前端依赖安装命令
- 前端启动命令
- 单元测试或最小验证命令
