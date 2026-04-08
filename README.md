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
│   ├── llms.py         # LLM 初始化，支持 MiniMax / GLM / Ollama
│   ├── user.py        # 用户模块
│   └── conversation.py # 对话历史模块
├── web/
│   └── chatbot_ui.py  # Streamlit 前端聊天界面
├── test_chat.py        # 非流式对话测试
├── test_stream.py      # 流式对话测试
├── test_memory.py      # 记忆功能测试
├── graph.png           # LangGraph 工作流可视化（自动生成）
├── .env                # 环境变量配置
└── .env_template       # 环境变量模板
```

## 前置准备

### 安装 pgvector 插件

本项目使用 PostgreSQL + pgvector 作为向量数据库，需要先安装 pgvector 扩展：

```bash
# 安装pgvector
git clone --branch v0.6.0 https://github.com/pgvector/pgvector.git
cd pgvector
make
make install

# 启用扩展
CREATE EXTENSION IF NOT EXISTS vector;
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

### 对话历史接口

#### 获取对话列表

```
GET /v1/conversations?user_id=xxx
```

响应：
```json
{
  "conversations": [
    {
      "id": "uuid",
      "user_id": "xxx",
      "username": "张三",
      "conversation_name": "关于Python的问题",
      "is_deleted": false,
      "created_at": "2026-04-08T10:00:00Z",
      "updated_at": "2026-04-08T10:30:00Z"
    }
  ]
}
```

#### 创建对话

```
POST /v1/conversations
```

请求：
```json
{
  "user_id": "xxx",
  "username": "张三",
  "conversation_name": "我的第一个对话"
}
```

#### 删除对话（逻辑删除）

```
DELETE /v1/conversations/{id}
```

响应：
```json
{
  "message": "Conversation deleted successfully"
}
```

#### 更新对话名称

```
PATCH /v1/conversations/{id}
```

请求：
```json
{
  "conversation_name": "新的对话名称"
}
```

### 聊天接口

#### POST /v1/chat

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

**自动命名**: 当对话名称为空时，自动根据用户第一条问题归纳至20字以内作为对话名称。

## 数据库设计

### conversations 表

```sql
CREATE TABLE conversations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         VARCHAR(64) NOT NULL,
    username        VARCHAR(128) NOT NULL,
    conversation_name VARCHAR(64) NOT NULL DEFAULT '',
    is_deleted      BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_conversations_user_id ON conversations(user_id);
CREATE INDEX idx_conversations_created_at ON conversations(created_at DESC);
```

## 已实现功能

- [x] 多模型支持（MiniMax / 智谱 AI / Ollama 占位）
- [x] 基于 PostgreSQL 的短期会话记忆
- [x] 对话历史管理（对话默认命名、创建、查询、删除、重命名）
- [x] 流式输出（SSE + 打字机效果）
- [x] LangGraph 工作流可视化（graph.png）
- [x] Streamlit 前端 UI（支持开启新对话、清空历史）
- [x] 极简用户模块（首次访问输入用户名，相同用户名识别为同一用户）

## 待实现功能

- [ ] 基于 PostgreSQL + pgvector 的长期记忆（简易，后续考虑引入框架，如MemU）
- [ ] 长期记忆框架 + 可选长期、短期记忆存储方案（默认本地保存）
- [ ] RAG（检索增强生成）
- [ ] 上下文压缩
- [ ] 多 Agent 任务协同

## 注意事项

- 本项目为本地运行练习项目，**请勿直接部署到公网**
- PostgreSQL 数据库暂未启用加密，请确保网络隔离
- LLM 调用默认使用 `MiniMax-M2.7` 模型
