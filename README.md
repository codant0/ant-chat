# Ant Chat

个人 AI 聊天工具，基于 FastAPI + LangGraph 构建，支持多模型、多会话和流式输出。

## 技术栈

- **框架**: FastAPI + LangGraph
- **LLM**: MiniMax (MiniMax-M2.7)、智谱 AI (glm-4)，兼容 Anthropic API 协议
- **记忆**: PostgreSQL（通过 LangGraph PostgresSaver 实现短期记忆）
- **前端**: Streamlit
- **数据库**: PostgreSQL + pgvector（规划中，用于 RAG 和长期记忆）

## 项目结构

```
ant-chat/
├── main.py              # FastAPI 后端核心，/v1/chat 接口
├── models/
│   └── llms.py         # LLM 初始化，支持 MiniMax / GLM / Ollama
├── web/
│   └── chatbot_ui.py  # Streamlit 前端聊天界面
├── test_chat.py        # 非流式对话测试
├── test_stream.py      # 流式对话测试
├── graph.png           # LangGraph 工作流可视化（自动生成）
├── .env                # 环境变量配置
└── .env_template       # 环境变量模板
```

## 快速启动

### 1. 配置环境变量

复制 `.env_template` 为 `.env`，填入以下配置：

```env
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=postgres

MINIMAX_API_KEY=your_minimax_api_key
# 或 GLM_API_KEY=your_glm_api_key
```

### 2. 启动后端服务

```bash
python main.py
```

服务将在 `http://localhost:8012` 启动。

### 3. 启动前端 UI

```bash
streamlit run web/chatbot_ui.py
```

## API 接口

### POST /v1/chat

聊天接口，支持流式和非流式响应。

**请求体**:

```json
{
  "messages": [{"role": "user", "content": "你好"}],
  "is_stream": true,
  "user_id": "user_1",
  "conversation_id": "uuid-string"
}
```

**流式响应**: SSE 格式，文本内容经过 base64 编码避免冲突，发送 `data: [DONE]` 表示结束。

## 已实现功能

- [x] 多模型支持（MiniMax / 智谱 AI / Ollama 占位）
- [x] 基于 PostgreSQL 的短期会话记忆
- [x] 流式输出（SSE + 打字机效果）
- [x] LangGraph 工作流可视化（graph.png）
- [x] Streamlit 前端 UI（支持开启新对话、清空历史）

## 待实现功能

- [ ] 基于 PostgreSQL + pgvector 的长期记忆
- [ ] RAG（检索增强生成）
- [ ] 多 Agent 任务协同

## 注意事项

- 本项目为本地运行练习项目，**请勿直接部署到公网**
- PostgreSQL 数据库暂未启用加密，请确保网络隔离
- LLM 调用默认使用 `MiniMax-M2.7` 模型