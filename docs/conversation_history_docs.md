# 对话历史功能设计

## 一、数据库选型评估

**结论：使用 PostgreSQL（关系型）**

| 评估项 | 关系型(PostgreSQL) | 非关系型 |
|--------|-------------------|---------|
| 数据结构 | 结构化，适合对话表 | 可用，但需额外设计 |
| 查询需求 | 支持时间/用户/名称查询 | 支持但语法复杂 |
| 现有集成 | 已使用 pgvector | 需引入新数据库 |
| 事务支持 | ✅ 原生支持 | 需额外处理 |

---

## 二、数据库设计

### 2.1 conversations 表

```sql
CREATE TABLE conversations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         VARCHAR(64) NOT NULL,
    username        VARCHAR(128) NOT NULL,
    conversation_name    VARCHAR(64) NOT NULL DEFAULT '',  -- 对话命名
    is_deleted      BOOLEAN DEFAULT FALSE,            -- 逻辑删除标记
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_conversations_user_id ON conversations(user_id);
CREATE INDEX idx_conversations_created_at ON conversations(created_at DESC);
```

### 2.2 说明

- `user_id`：用户唯一标识
- `username`：用户名（冗余存储，便于查询展示）
- `conversation_name`：对话名称，默认空字符串，创建后自动归纳或用户自定义
- `is_deleted`：逻辑删除标记，删除时置为 TRUE

---

## 三、后端修改点

### 3.1 新建文件

| 文件路径 | 说明 |
|---------|------|
| `models/conversation.py` | Conversation 数据模型定义 |

### 3.2 修改文件

| 文件 | 修改内容 |
|------|---------|
| `main.py` | 新增 `GET /v1/conversations` - 获取用户对话列表 |
| `main.py` | 新增 `POST /v1/conversations` - 创建新对话 |
| `main.py` | 新增 `DELETE /v1/conversations/{id}` - 逻辑删除对话 |
| `main.py` | 新增 `PATCH /v1/conversations/{id}` - 更新对话名称 |
| `main.py` | 修改 `/v1/chat` - 首条消息时自动生成 conversation_name |

---

## 四、API 设计

### 4.1 获取对话列表

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
      "created_at": "2026-04-08T10:00:00Z",
      "updated_at": "2026-04-08T10:30:00Z"
    }
  ]
}
```

### 4.2 创建对话

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

### 4.3 删除对话（逻辑删除）

```
DELETE /v1/conversations/{id}
```

### 4.4 更新对话名称

```
PATCH /v1/conversations/{id}
```

请求：
```json
{
  "conversation_name": "新的对话名称"
}
```

---

## 五、前端修改点

| 文件 | 修改内容 |
|------|---------|
| `web/chatbot_ui.py` | 侧边栏增加「对话列表」展示区 |
| `web/chatbot_ui.py` | 新增「创建对话」「删除对话」按钮 |
| `web/chatbot_ui.py` | 对话命名：首次对话时自动总结 / 支持点击编辑 |
| `web/chatbot_ui.py` | 选择不同对话时加载对应历史记录 |

### 5.1 对话命名规则

- **自动命名**：默认根据用户第一条问题归纳至20字以内
  - 示例：用户提问"如何用Python写一个快速排序" → 自动命名为"如何用Python写快速排序"
- **自定义命名**：用户可点击编辑对话名称

---

## 六、实现顺序

1. **数据库表** - 创建 `conversations` 表
2. **后端模型** - `models/conversation.py`
3. **后端 API** - 对话 CRUD 接口
4. **修改 /v1/chat** - 自动命名逻辑
5. **前端 UI** - 侧边栏对话管理
