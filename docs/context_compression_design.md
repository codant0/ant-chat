# ant-chat 上下文压缩功能设计文档

## 1. 背景与目标

ant-chat 当前使用 LangGraph + PostgreSQL 实现对话管理功能。在长对话场景下，上下文窗口（context window）会逐渐耗尽，导致以下问题：
1. 消息历史过长，超出 LLM 上下文窗口限制
2. 每次请求的 token 开销增加，响应延迟和成本上升
3. 关键信息被稀释，模型难以聚焦核心内容

本文档旨在设计一套上下文压缩方案，解决上述问题。

---

## 2. 上下文压缩方案对比

### 2.1 LangChain ContextualCompression

**方案描述：**  
LangChain 的 ContextualCompressionRetriever 是一个文档压缩器，对检索到的文档进行二次过滤，只返回最相关的内容。它使用 LLM 来判断文档与查询的相关性，并移除冗余信息。

**压缩器类型：**
- `LLMChainFilter`: 使用 LLM 判断文档是否相关，仅返回相关文档
- `EmbeddingsFilter`: 基于嵌入相似度过滤
- `DocumentCompressorPipeline`: 串联多个压缩器

**优点：**
- 开箱即用，API 简洁
- 与 LangChain 生态深度集成
- 支持多种压缩策略组合

**缺点：**
- 主要面向 RAG 场景，非对话历史压缩设计
- 每次压缩仍需调用 LLM，开销较高
- 无法保留对话上下文中的关键语义

**适用场景：** RAG 检索优化

---

### 2.2 LangGraph 内置压缩（Checkpoint + Store）

**方案描述：**  
LangGraph 通过 `PostgresSaver` (checkpoint) 和 `PostgresStore` (长期记忆) 实现状态持久化，但本身不提供压缩功能。它保存完整的消息历史，压缩需要额外实现。

**当前 ant-chat 使用：**
```python
# 短期记忆（checkpoint）
checkpointer = PostgresSaver(conn)
checkpointer.setup()

# 长期记忆（store）
store = PostgresStore(conn)
store.setup()

graph.compile(checkpointer=checkpointer, store=store)
```

**优点：**
- 与现有架构无缝集成
- 支持多线程（thread_id）隔离
- 基于 PostgreSQL，运维简单

**缺点：**
- 无内置压缩，需手动实现压缩逻辑
- 历史消息全部保存，长对话会超出上下文窗口

**适用场景：** 状态持久化（非压缩）

---

### 2.3 自研方案

**方案描述：**  
根据业务需求自主设计压缩策略，常见方法包括：

| 方法 | 描述 | 压缩率 |
|------|------|--------|
| 滑动窗口 | 只保留最近 N 轮对话 | 固定 |
| 摘要压缩 | 用 LLM 将历史压缩为摘要 | 高 |
| 重要性过滤 | 保留关键消息，过滤噪音 | 动态 |
| 分块摘要 | 分块压缩后拼接 | 中 |

**优点：**
- 完全可控，可针对业务优化
- 无外部依赖，部署简单
- 可渐进式实现

**缺点：**
- 需要自行实现和维护
- 摘要质量依赖 LLM 能力

---

### 2.4 第三方框架（MemGPT / Hedgehog）

**MemGPT：**  
借鉴操作系统分层内存思想，将记忆分为：
- **主上下文（Main Context）**: 当前对话窗口
- **工作上下文（Working Context）**: 最近活跃的对话历史
- **归档存储（Archive Storage）**: 长期记忆数据库

自动管理三级记忆间的数据流动，实现"无限上下文"。

**Hedgehog：**  
轻量级上下文管理框架，专注于对话压缩。

**优点：**
- 设计成熟，有学术背景
- 自动化管理，开发工作量小

**缺点：**
- 学习曲线较陡
- 与 LangGraph 集成需要适配层
- MemGPT 主活跃于研究场景，生产稳定性待验证

---

## 3. 方案对比矩阵

| 维度 | LangChain Compression | LangGraph 内置 | 自研方案 | MemGPT |
|------|-------------------|--------------|----------|-------|
| **压缩效果** | 中（RAG 优化） | 无 | 高（可控） | 高 |
| **实现复杂度** | 低 | N/A | 中 | 高 |
| **架构兼容性** | 高（LangChain） | 极高 | 高 | 中 |
| **性能开销** | 中（需 LLM 调用） | 低 | 低 | 中 |
| **维护成本** | 低 | 低 | 中 | 高 |
| **扩展性** | 中 | 高 | 高 | 中 |

---

## 4. 针对 ant-chat 的建议方案

### 4.1 推荐：自研方案（滑动窗口 + 摘要压缩）

**理由：**
1. 与现有 LangGraph + PostgreSQL 架构无缝集成
2. 实现可控，渐进式增强
3. 兼顾性能与压缩质量
4. 无外部依赖，运维简单

### 4.2 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                      用户请求                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  MessageProcessor                         │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  1. 检查当前上下文大小                              │  │
│  │  2. 判断是否需要压缩 (阈值: 80% 上下文)           │  │
│  │  3. 执行压缩策略                                   │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
     ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
     │  滑动窗口    │ │  摘要压缩   │ │  重要性过滤│
     │  (默认5轮)   │ │  (LLM)      │ │  (规则)     │
     └──────────────┘ └──────────────┘ └──────────────┘
              │               │               │
              └───────────────┼───────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  LangGraph Checkpoint                     │
│              (PostgresSaver 保存状态)                     │
└─────────────────────────────────────────────────────────────┘
```

### 4.3 核心组件

```python
# contexts/compression.py

from enum import Enum
from typing import List, Protocol
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

class CompressionStrategy(Protocol):
    """压缩策略接口"""
    def compress(self, messages: List[BaseMessage], max_tokens: int) -> List[BaseMessage]: ...

class SlidingWindowStrategy:
    """滑动窗���压缩"""
    def __init__(self, window_size: int = 5):
        self.window_size = window_size
    
    def compress(self, messages: List[BaseMessage], max_tokens: int) -> List[BaseMessage]:
        # 保留系统消息 + 最近 N 轮
        system_msgs = [m for m in messages if isinstance(m, SystemMessage)]
        recent = messages[len(system_msgs):][-self.window_size * 2:]  # user + assistant
        return system_msgs + recent

class SummaryStrategy:
    """摘要压缩"""
    def __init__(self, llm, summary_prompt: str = None):
        self.llm = llm
        self.summary_prompt = summary_prompt or DEFAULT_SUMMARY_PROMPT
    
    def compress(self, messages: List[BaseMessage], max_tokens: int) -> List[BaseMessage]:
        # 保留系统消息 + 最近对话 + 历史摘要
        system_msgs = [m for m in messages if isinstance(m, SystemMessage)]
        recent = messages[len(system_msgs):][-2:]  # 最近一轮
        older = messages[len(system_msgs):][:-2]
        
        if not older:
            return system_msgs + recent
        
        # 调用 LLM 生成摘要
        summary = self.llm.invoke(f"{self.summary_prompt}\n\n内容:\n{older}")
        summary_msg = SystemMessage(content=f"[历史摘要] {summary.content}")
        return [summary_msg] + recent

class ContextCompressor:
    """上下文压缩器主类"""
    def __init__(
        self,
        llm,
        max_context_ratio: float = 0.8,
        strategies: List[CompressionStrategy] = None
    ):
        self.llm = llm
        self.max_context_ratio = max_context_ratio
        self.strategies = strategies or [
            SlidingWindowStrategy(window_size=5),
            SummaryStrategy(llm)
        ]
    
    def compress(self, messages: List[BaseMessage], current_tokens: int, max_tokens: int) -> List[BaseMessage]:
        if current_tokens < max_tokens * self.max_context_ratio:
            return messages  # 无需压缩
        
        for strategy in self.strategies:
            compressed = strategy.compress(messages, max_tokens)
            # 验证压缩后大小
            if self._estimate_tokens(compressed) < max_tokens * self.max_context_ratio:
                return compressed
        
        return compressed  # 兜底策略
```

### 4.4 与 LangGraph 集成

```python
# 在 main.py 中集成

from contexts.compression import ContextCompressor, SlidingWindowStrategy, SummaryStrategy

class ChatRequest(BaseModel):
    messages: List[Message]
    is_stream: bool = False
    user_id: str
    conversation_id: str
    max_context_tokens: int = 8000  # 可配置

def chatbot_with_compression(state: MessagesState) -> dict:
    global client, compressor
    
    messages = state["messages"]
    current_tokens = estimate_tokens(messages)
    
    # 自动压缩
    if current_tokens > request.max_context_tokens * 0.8:
        messages = compressor.compress(messages, current_tokens, request.max_context_tokens)
    
    # ... 原有 chatbot 逻辑
```

### 4.5 数据库扩展

```sql
-- 对话消息表扩展，支持压缩标记

ALTER TABLE conversation_messages ADD COLUMN is_compressed BOOLEAN DEFAULT FALSE;
ALTER TABLE conversation_messages ADD COLUMN summary_id UUID;

CREATE TABLE IF NOT EXISTS message_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id),
    summary_text TEXT NOT NULL,
    message_range_start INT NOT NULL,
    message_range_end INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 5. 实现路线图

### Phase 1: 滑动窗口（1-2 天）
- 实现 `SlidingWindowStrategy`
- 集成到 `main.py`
- 配置默认窗口大小（5 轮）

### Phase 2: 摘要压缩（2-3 天）
- 实现 `SummaryStrategy`
- 创建摘要存储表
- ��加��要生成逻辑

### Phase 3: 重要性过滤（可选，2 天）
- 基于规则的关键消息识别
- 自动保留关键信息（日期、数量、决策等）

### Phase 4: 监控与调优（1 天）
- 压缩效果监控
- 参数调优（窗口大小、阈值）

---

## 6. 风险与缓解

| 风险 | 缓解措施 |
|------|---------|
| 摘要质量不稳定 | 人工评估 + 反馈循环 |
| Token 估算误差 | 预留缓冲空间（20%） |
| 压缩后丢失重要信息 | 支持手动标记关键消息 |

---

## 7. 参考资料

- [LangChain Contextual Compression](https://python.langchain.com/docs/modules/data_connection/retrievers/contextual_compression/)
- [LangGraph Checkpointing](https://python.langchain.com/docs/langgraph/checkpointing/)
- [MemGPT: Towards LLMs as Operating Systems](https://memgpt.ai/)
- [Recurrent Context Compression (ICLR 2025)](https://openreview.net/forum?id=GYk0thSY1M)

---

**文档版本:** v1.0  
**创建时间:** 2026-04-10  
**作者:** ant-chat subagent