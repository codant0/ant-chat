# ant-chat 长期记忆功能设计方案

## 一、项目现状分析

### 1.1 现有架构
- **技术栈**: Python + FastAPI + LangGraph + PostgreSQL + pgvector
- **现有记忆机制**:
  - **短期记忆**: `PostgresSaver` - 基于 checkpointer，进程重启后不丢失，但仅限同一 conversation_id
  - **长期记忆**: `PostgresStore` - 跨 conversation_id 存储用户信息
- **用户模块**: 极简模块，通过用户名 hash 生成 user_id
- **会话管理**: 支持多 conversation_id，通过 user_id 关联用户

### 1.2 当前痛点
1. **PostgresStore 功能有限** - 仅支持基本的 k-v 存储和向量检索，缺少智能的记忆提取、衰减、更新机制
2. **缺乏记忆管理** - 无法自动识别重要信息、自动总结、自动遗忘
3. **配置不灵活** - 硬编码了 PostgreSQL，无法切换到本地文件或其他后端
4. **缺乏可观测性** - 无法追踪记忆的存取历史

---

## 二、三种方案对比

### 方案 A：纯自研（Build Your Own）

#### 架构描述
完全自己实现记忆的存储、检索、管理逻辑，不依赖任何外部框架。

#### 优点
| 优势 | 说明 |
|------|------|
| **完全可控** | 每一行代码都可定制，满足细分需求 |
| **无外部依赖** | 减少供应链风险和依赖升级困扰 |
| **灵活的数据模型** | 可根据业务需求自由设计存储结构 |
| **零成本** | 无需付费给第三方服务 |

#### 缺点
| 劣势 | 说明 |
|------|------|
| **开发量大** | 需要实现向量索引、查询重写、记忆衰减、重要性评分等 |
| **迭代周期长** | 每个功能都需要从零开发和测试 |
| **缺乏最佳实践** | 需要自己摸索，容易踩坑 |
| **可扩展性挑战** | 高并发、分布式场景需要额外设计 |

#### 实现复杂度: ⭐⭐⭐⭐⭐ (高)
- 需自己实现: 向量嵌入、相似度检索、记忆生命周期管理、GC 机制
- 预计开发时间: 4-8 周

#### 效果评估
- 基础功能可实现，但高级能力（智能提取、自动遗忘）需要大量迭代
- 与专业方案相比，效果差距明显

---

### 方案 B：使用成熟框架（Mem0 / Zep / Letta）

#### 主流框架对比

| 框架 | 定位 | 优势 | 劣势 | 适用场景 |
|------|------|------|------|----------|
| **Mem0** | 专为 AI Agent 设计的记忆层 | LoCoMo 基准领先、ECAI 2025 发表、语义搜索强、云原生 | 相对较新、文档尚在完善 | 需要高质量长期记忆的 Agent |
| **Zep** | 对话记忆与用户画像 | 成熟的用户理解能力、实体识别强 | 内存占用大(600K+ tokens/conversation) | 需要用户画像和实体理解 |
| **Letta** | 具身 Agent 记忆 | 多模态支持、内置 Agent 框架 | 与 LangGraph 集成复杂度高 | 需要复杂 Agent 状态的场景 |
| **Helicone** | LLM 可观测性 + 记忆 | 日志追踪强大 | 不是专门的记忆框架 | 需要追踪 LLM 调用历史 |
| **Cognee** | 知识图谱记忆 | 知识提取能力强 | 偏文档处理 | 知识密集型应用 |

#### 优点
| 优势 | 说明 |
|------|------|
| **开箱即用** | 集成后几乎不需要额外开发 |
| **经过验证** | 在生产环境经过考验 |
| **持续更新** | 社区活跃，持续迭代 |
| **高级特性** | 自动记忆提取、智能检索、衰减机制等 |

#### 缺点
| 劣势 | 说明 |
|------|------|
| **厂商锁定** | 数据模型和接口与框架绑定 |
| **成本** | 云服务有成本，自托管增加运维负担 |
| **灵活性受限** | 难以实现高度定制化需求 |
| **性能开销** | 网络调用或中间层带来的延迟 |

#### 实现复杂度: ⭐ (低)
- 集成时间: 1-3 天
- 主要是配置和适配工作

#### 效果评估
- 基础和高级功能都能获得
- 取决于所选框架的能力上限

---

### 方案 C：混合方案（自研核心 + 框架辅助）

#### 架构描述
保留现有 PostgreSQL + pgvector 作为核心存储和检索层，在其上构建自研的记忆管理层，同时可选集成 Mem0 的高级特性（如智能提取）作为辅助。

#### 优点
| 优势 | 说明 |
|------|------|
| **保持控制** | 核心存储逻辑自主可控 |
| **复用成熟能力** | 借助框架的高级特性提升效果 |
| **灵活切换** | 可独立替换某一层而不影响整体 |
| **性能最优** | 直接操作数据库，无中间层开销 |
| **数据主权** | 所有数据留在自己的基础设施 |

#### 缺点
| 劣势 | 说明 |
|------|------|
| **仍需开发** | 记忆管理层需要自研 |
| **集成复杂度** | 需要处理两套系统的对接 |
| **维护成本** | 需要同时维护自研和第三方组件 |

#### 实现复杂度: ⭐⭐⭐ (中)
- 自研部分: 记忆抽象层、配置驱动、事件系统
- 集成部分: 利用 pgvector 现有能力，按需引入框架

#### 效果评估
- 可达到方案 B 90% 的效果，同时保持更高的灵活性
- 适合有定制需求但不想全部自研的团队

---

## 三、方案推荐与架构设计

### 3.1 推荐方案: 方案 C（混合方案）

**理由**:
1. ant-chat 已有的 PostgreSQL + pgvector 是成熟的基础设施，弃用成本高
2. LangGraph 的 PostgresStore 已提供基础记忆能力，扩展即可
3. 记忆管理层自研复杂度可控，且能保持与现有模块的无缝集成
4. 可配置的设计支持未来平滑迁移到纯框架方案

### 3.2 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        ant-chat 应用                         │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   User      │  │ Conversation│  │   Memory Manager    │  │
│  │   Module    │  │   Module    │  │   (核心新模块)       │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│                                            │                 │
│                           ┌────────────────┴────────────────┐
│                           │     Memory Interface (抽象层)    │
│                           └────────────────┬────────────────┘
│                                            │                 │
│         ┌──────────────────────────────────┼───────────────┐
│         │                                  │               │
│  ┌──────▼──────┐                   ┌───────▼───────┐       │
│  │ Local       │                   │ PostgreSQL    │       │
│  │ Provider    │                   │ Provider      │       │
│  │ (文件系统)   │                   │ + pgvector    │       │
│  └─────────────┘                   └───────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

### 3.3 配置驱动设计

```json
{
  "memory": {
    "provider": "local",
    "local": {
      "path": "./memory"
    },
    "postgresql": {
      "connection": "postgresql://user:pass@host:port/db",
      "pool_size": 10,
      "vector_dim": 1536,
      "embedding_model": "text-embedding-3-small"
    },
    "memory": {
      "max_size_mb": 1024,
      "default_ttl_days": 90,
      "importance_threshold": 0.7,
      "gc_interval_hours": 24
    }
  }
}
```

---

## 四、核心模块详细设计

### 4.1 记忆存储模型

```sql
-- 记忆主表
CREATE TABLE memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(64) NOT NULL,
    session_id VARCHAR(64),
    
    -- 记忆内容
    content TEXT NOT NULL,
    content_hash VARCHAR(64) NOT NULL,  -- 用于去重
    memory_type VARCHAR(32) NOT NULL,   -- 'fact', 'preference', 'entity', 'summary'
    
    -- 元数据
    importance_score FLOAT DEFAULT 0.5,  -- 0.0-1.0
    source_message_id VARCHAR(64),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_accessed_at TIMESTAMP DEFAULT NOW(),
    
    -- 生命周期
    expires_at TIMESTAMP,
    is_pinned BOOLEAN DEFAULT FALSE,
    
    -- 向量（存储在 pgvector）
    embedding_id BIGINT,
    
    -- 索引
    INDEX idx_user_id (user_id),
    INDEX idx_session_id (session_id),
    INDEX idx_memory_type (memory_type),
    INDEX idx_importance (importance_score),
    INDEX idx_created_at (created_at),
    INDEX idx_expires_at (expires_at)
);

-- 向量表（与 pgvector 配合）
CREATE TABLE memory_embeddings (
    id BIGSERIAL PRIMARY KEY,
    memory_id UUID REFERENCES memories(id) ON DELETE CASCADE,
    embedding VECTOR(1536) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX ON memory_embeddings USING ivfflat (embedding vector_cosine_ops);
```

### 4.2 记忆类型定义

```python
from enum import Enum
from typing import Optional
from pydantic import BaseModel
from datetime import datetime

class MemoryType(str, Enum):
    FACT = "fact"           # 事实性信息（姓名、年龄等）
    PREFERENCE = "preference"  # 用户偏好（喜欢苹果不喜欢香蕉）
    ENTITY = "entity"        # 实体（项目、文档、联系人）
    SUMMARY = "summary"      # 对话摘要
    CUSTOM = "custom"        # 自定义

class Memory(BaseModel):
    id: Optional[str] = None
    user_id: str
    session_id: Optional[str] = None
    
    content: str
    content_hash: str
    memory_type: MemoryType
    
    importance_score: float = 0.5
    source_message_id: Optional[str] = None
    
    created_at: datetime = None
    updated_at: datetime = None
    last_accessed_at: datetime = None
    
    expires_at: Optional[datetime] = None
    is_pinned: bool = False
    
    embedding_id: Optional[int] = None
```

### 4.3 存储后端接口

```python
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from .memory import Memory, MemoryType, MemorySearchResult

class MemoryProvider(ABC):
    """记忆存储后端抽象接口"""
    
    @abstractmethod
    async def init(self) -> None:
        """初始化存储后端"""
        pass
    
    @abstractmethod
    async def store(self, memory: Memory) -> str:
        """存储单条记忆，返回记忆 ID"""
        pass
    
    @abstractmethod
    async def store_batch(self, memories: List[Memory]) -> List[str]:
        """批量存储记忆"""
        pass
    
    @abstractmethod
    async def get(self, memory_id: str) -> Optional[Memory]:
        """根据 ID 获取记忆"""
        pass
    
    @abstractmethod
    async def update(
        self, 
        memory_id: str, 
        updates: Dict[str, Any]
    ) -> bool:
        """更新记忆"""
        pass
    
    @abstractmethod
    async def delete(self, memory_id: str) -> bool:
        """删除记忆"""
        pass
    
    @abstractmethod
    async def search(
        self,
        query: str,
        user_id: str,
        limit: int = 10,
        memory_type: Optional[MemoryType] = None,
        min_importance: float = 0.0,
    ) -> List[MemorySearchResult]:
        """向量检索相关记忆"""
        pass
    
    @abstractmethod
    async def list_by_user(
        self,
        user_id: str,
        limit: int = 100,
        offset: int = 0,
        memory_type: Optional[MemoryType] = None,
    ) -> List[Memory]:
        """列出用户的所有记忆"""
        pass
    
    @abstractmethod
    async def delete_expired(self) -> int:
        """删除过期记忆，返回删除数量"""
        pass
    
    @abstractmethod
    async def get_stats(self, user_id: str) -> Dict[str, Any]:
        """获取用户记忆统计"""
        pass
```

### 4.4 PostgreSQL Provider 实现

```python
import hashlib
import json
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from psycopg import Connection
from psycopg.rows import dict_row
from .provider import MemoryProvider
from .memory import Memory, MemoryType, MemorySearchResult

class PostgreSQLMemoryProvider(MemoryProvider):
    """基于 PostgreSQL + pgvector 的记忆存储"""
    
    def __init__(
        self,
        connection_string: str,
        vector_dim: int = 1536,
        embedding_model: str = "text-embedding-3-small",
        default_ttl_days: int = 90,
    ):
        self.connection_string = connection_string
        self.vector_dim = vector_dim
        self.embedding_model = embedding_model
        self.default_ttl_days = default_ttl_days
        self._conn: Optional[Connection] = None
    
    async def init(self) -> None:
        """初始化数据库表结构"""
        self._conn = Connection.connect(
            self.connection_string,
            autocommit=True,
            prepare_threshold=0,
            row_factory=dict_row
        )
        await self._create_tables()
    
    async def _create_tables(self) -> None:
        """创建记忆相关表"""
        # 启用 pgvector 扩展
        await self._conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        
        # 创建主表
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id VARCHAR(64) NOT NULL,
                session_id VARCHAR(64),
                content TEXT NOT NULL,
                content_hash VARCHAR(64) NOT NULL,
                memory_type VARCHAR(32) NOT NULL,
                importance_score FLOAT DEFAULT 0.5,
                source_message_id VARCHAR(64),
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
                last_accessed_at TIMESTAMP DEFAULT NOW(),
                expires_at TIMESTAMP,
                is_pinned BOOLEAN DEFAULT FALSE,
                embedding_id BIGINT,
                UNIQUE(user_id, content_hash)
            )
        """)
        
        # 创建向量表
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS memory_embeddings (
                id BIGSERIAL PRIMARY KEY,
                memory_id UUID REFERENCES memories(id) ON DELETE CASCADE,
                embedding vector(1536) NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # 创建索引
        await self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_user_id ON memories(user_id)
        """)
        await self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_memory_type ON memories(memory_type)
        """)
        await self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_expires_at ON memories(expires_at)
        """)
    
    async def store(self, memory: Memory) -> str:
        """存储单条记忆"""
        # 生成内容 hash 用于去重
        memory.content_hash = hashlib.md5(
            f"{memory.user_id}:{memory.content}".encode()
        ).hexdigest()
        
        # 设置过期时间
        if not memory.expires_at and self.default_ttl_days > 0:
            memory.expires_at = datetime.now() + timedelta(days=self.default_ttl_days)
        
        result = await self._conn.execute(
            """
            INSERT INTO memories (
                user_id, session_id, content, content_hash, memory_type,
                importance_score, source_message_id, expires_at, is_pinned
            ) VALUES (
                %(user_id)s, %(session_id)s, %(content)s, %(content_hash)s,
                %(memory_type)s, %(importance_score)s, %(source_message_id)s,
                %(expires_at)s, %(is_pinned)s
            )
            ON CONFLICT (user_id, content_hash) DO UPDATE SET
                updated_at = NOW(),
                importance_score = GREATEST(memories.importance_score, EXCLUDED.importance_score)
            RETURNING id
            """,
            memory.model_dump(exclude_none=True)
        )
        
        memory_id = result.fetchone()["id"]
        
        # 如果有 embedding，存储向量
        if memory.embedding_id:
            await self._store_embedding(memory_id, memory.embedding_id)
        
        return str(memory_id)
    
    async def store_batch(self, memories: List[Memory]) -> List[str]:
        """批量存储记忆"""
        ids = []
        for memory in memories:
            memory_id = await self.store(memory)
            ids.append(memory_id)
        return ids
    
    async def get(self, memory_id: str) -> Optional[Memory]:
        """获取记忆"""
        row = await self._conn.execute(
            "SELECT * FROM memories WHERE id = %(id)s",
            {"id": memory_id}
        ).fetchone()
        
        if not row:
            return None
        
        # 更新最后访问时间
        await self._conn.execute(
            "UPDATE memories SET last_accessed_at = NOW() WHERE id = %(id)s",
            {"id": memory_id}
        )
        
        return Memory(**row)
    
    async def update(
        self,
        memory_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """更新记忆"""
        updates["updated_at"] = datetime.now()
        
        set_clause = ", ".join([f"{k} = %({k})s" for k in updates.keys()])
        
        result = await self._conn.execute(
            f"UPDATE memories SET {set_clause} WHERE id = %(id)s",
            {**updates, "id": memory_id}
        )
        
        return result.rowcount > 0
    
    async def delete(self, memory_id: str) -> bool:
        """删除记忆"""
        result = await self._conn.execute(
            "DELETE FROM memories WHERE id = %(id)s",
            {"id": memory_id}
        )
        return result.rowcount > 0
    
    async def search(
        self,
        query: str,
        user_id: str,
        limit: int = 10,
        memory_type: Optional[MemoryType] = None,
        min_importance: float = 0.0,
    ) -> List[MemorySearchResult]:
        """
        语义搜索记忆
        注意: 实际使用时需要调用 embedding API 获取向量
        这里假设 query_embedding 是已生成的向量
        """
        # TODO: 调用 embedding 服务获取 query_embedding
        # query_embedding = await self._get_embedding(query)
        
        conditions = [
            "m.user_id = %(user_id)s",
            "m.importance_score >= %(min_importance)s",
            "(m.expires_at IS NULL OR m.expires_at > NOW())",
        ]
        
        params = {
            "user_id": user_id,
            "min_importance": min_importance,
            "limit": limit,
        }
        
        if memory_type:
            conditions.append("m.memory_type = %(memory_type)s")
            params["memory_type"] = memory_type.value
        
        where_clause = " AND ".join(conditions)
        
        # 向量检索查询
        # 注意: 需要先获取 query_embedding
        # SELECT m.*, e.embedding <=> %(embedding)s AS similarity
        # FROM memories m
        # JOIN memory_embeddings e ON m.id = e.memory_id
        # WHERE {where_clause}
        # ORDER BY similarity
        # LIMIT %(limit)s
        
        # 简化版本：基于关键词搜索
        rows = await self._conn.execute(
            f"""
            SELECT m.*,
                   ts_rank(to_tsvector('simple', m.content), plainto_tsquery('simple', %(query)s)) AS rank
            FROM memories m
            WHERE {where_clause}
              AND to_tsvector('simple', m.content) @@ plainto_tsquery('simple', %(query)s)
            ORDER BY rank DESC, m.importance_score DESC
            LIMIT %(limit)s
            """,
            {**params, "query": query}
        ).fetchall()
        
        return [MemorySearchResult(
            memory=Memory(**{k: v for k, v in row.items() if k != 'rank'}),
            score=float(row.get('rank', 0))
        ) for row in rows]
    
    async def list_by_user(
        self,
        user_id: str,
        limit: int = 100,
        offset: int = 0,
        memory_type: Optional[MemoryType] = None,
    ) -> List[Memory]:
        """列出用户的记忆"""
        conditions = ["user_id = %(user_id)s"]
        params = {"user_id": user_id, "limit": limit, "offset": offset}
        
        if memory_type:
            conditions.append("memory_type = %(memory_type)s")
            params["memory_type"] = memory_type.value
        
        where_clause = " AND ".join(conditions)
        
        rows = await self._conn.execute(
            f"""
            SELECT * FROM memories
            WHERE {where_clause}
            ORDER BY importance_score DESC, created_at DESC
            LIMIT %(limit)s OFFSET %(offset)s
            """,
            params
        ).fetchall()
        
        return [Memory(**row) for row in rows]
    
    async def delete_expired(self) -> int:
        """删除过期记忆"""
        result = await self._conn.execute(
            """
            DELETE FROM memories
            WHERE expires_at IS NOT NULL AND expires_at < NOW()
            """
        )
        return result.rowcount
    
    async def get_stats(self, user_id: str) -> Dict[str, Any]:
        """获取用户记忆统计"""
        stats = await self._conn.execute(
            """
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE memory_type = 'fact') as fact_count,
                COUNT(*) FILTER (WHERE memory_type = 'preference') as preference_count,
                COUNT(*) FILTER (WHERE memory_type = 'entity') as entity_count,
                COUNT(*) FILTER (WHERE memory_type = 'summary') as summary_count,
                AVG(importance_score) as avg_importance,
                MAX(importance_score) as max_importance,
                MIN(importance_score) as min_importance
            FROM memories
            WHERE user_id = %(user_id)s
            """,
            {"user_id": user_id}
        ).fetchone()
        
        return dict(stats)
```

### 4.5 本地文件系统 Provider 实现

```python
import os
import json
import hashlib
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from .provider import MemoryProvider
from .memory import Memory, MemoryType, MemorySearchResult

class LocalMemoryProvider(MemoryProvider):
    """基于本地文件系统的记忆存储"""
    
    def __init__(self, base_path: str = "./memory"):
        self.base_path = Path(base_path)
        self._ensure_directories()
    
    def _ensure_directories(self) -> None:
        """创建必要的目录结构"""
        (self.base_path / "memories").mkdir(parents=True, exist_ok=True)
        (self.base_path / "index").mkdir(parents=True, exist_ok=True)
    
    def _get_memory_path(self, memory_id: str) -> Path:
        """获取记忆文件路径"""
        return self.base_path / "memories" / f"{memory_id}.json"
    
    def _get_index_path(self, user_id: str) -> Path:
        """获取用户索引文件路径"""
        return self.base_path / "index" / f"{user_id}.json"
    
    async def init(self) -> None:
        """初始化存储"""
        self._ensure_directories()
    
    async def store(self, memory: Memory) -> str:
        """存储单条记忆"""
        memory_id = memory.id or str(hashlib.md5(
            f"{memory.user_id}:{memory.content}:{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16])
        
        memory.id = memory_id
        memory.content_hash = hashlib.md5(
            f"{memory.user_id}:{memory.content}".encode()
        ).hexdigest()
        
        # 保存记忆文件
        memory_path = self._get_memory_path(memory_id)
        with open(memory_path, 'w', encoding='utf-8') as f:
            json.dump(memory.model_dump(), f, default=str, ensure_ascii=False)
        
        # 更新用户索引
        await self._update_user_index(memory)
        
        return memory_id
    
    async def store_batch(self, memories: List[Memory]) -> List[str]:
        """批量存储记忆"""
        ids = []
        for memory in memories:
            memory_id = await self.store(memory)
            ids.append(memory_id)
        return ids
    
    async def get(self, memory_id: str) -> Optional[Memory]:
        """获取记忆"""
        memory_path = self._get_memory_path(memory_id)
        if not memory_path.exists():
            return None
        
        with open(memory_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return Memory(**data)
    
    async def update(
        self,
        memory_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """更新记忆"""
        memory = await self.get(memory_id)
        if not memory:
            return False
        
        for key, value in updates.items():
            if hasattr(memory, key):
                setattr(memory, key, value)
        
        memory.updated_at = datetime.now()
        
        with open(self._get_memory_path(memory_id), 'w', encoding='utf-8') as f:
            json.dump(memory.model_dump(), f, default=str, ensure_ascii=False)
        
        return True
    
    async def delete(self, memory_id: str) -> bool:
        """删除记忆"""
        memory_path = self._get_memory_path(memory_id)
        if memory_path.exists():
            memory = await self.get(memory_id)
            memory_path.unlink()
            if memory:
                await self._remove_from_index(memory)
            return True
        return False
    
    async def search(
        self,
        query: str,
        user_id: str,
        limit: int = 10,
        memory_type: Optional[MemoryType] = None,
        min_importance: float = 0.0,
    ) -> List[MemorySearchResult]:
        """
        本地文件系统的记忆搜索
        实现简单版本: 基于关键词匹配
        后续可集成本地向量数据库(如 FAISS)提升搜索质量
        """
        memories = await self.list_by_user(
            user_id,
            limit=1000,
            memory_type=memory_type
        )
        
        query_lower = query.lower()
        scored_memories = []
        
        for memory in memories:
            if memory.importance_score < min_importance:
                continue
            
            # 简单的关键词匹配评分
            content_lower = memory.content.lower()
            
            # 计算包含的关键词数量
            words = query_lower.split()
            match_count = sum(1 for word in words if word in content_lower)
            
            if match_count > 0:
                # 综合评分: 匹配度 * 重要性
                score = (match_count / len(words)) * memory.importance_score
                scored_memories.append(MemorySearchResult(
                    memory=memory,
                    score=score
                ))
        
        # 排序并返回 top N
        scored_memories.sort(key=lambda x: x.score, reverse=True)
        return scored_memories[:limit]
    
    async def list_by_user(
        self,
        user_id: str,
        limit: int = 100,
        offset: int = 0,
        memory_type: Optional[MemoryType] = None,
    ) -> List[Memory]:
        """列出用户的记忆"""
        index_path = self._get_index_path(user_id)
        
        if not index_path.exists():
            return []
        
        with open(index_path, 'r', encoding='utf-8') as f:
            memory_ids = json.load(f)
        
        memories = []
        for memory_id in memory_ids[offset:offset+limit]:
            memory = await self.get(memory_id)
            if memory:
                if memory_type and memory.memory_type != memory_type:
                    continue
                memories.append(memory)
        
        return memories
    
    async def delete_expired(self) -> int:
        """删除过期记忆"""
        count = 0
        memories_dir = self.base_path / "memories"
        
        for memory_file in memories_dir.glob("*.json"):
            with open(memory_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            memory = Memory(**data)
            
            if memory.expires_at:
                expires_at = datetime.fromisoformat(memory.expires_at)
                if expires_at < datetime.now():
                    memory_file.unlink()
                    await self._remove_from_index(memory)
                    count += 1
        
        return count
    
    async def get_stats(self, user_id: str) -> Dict[str, Any]:
        """获取用户记忆统计"""
        memories = await self.list_by_user(user_id, limit=10000)
        
        type_counts = {t: 0 for t in MemoryType}
        total_importance = 0.0
        
        for m in memories:
            type_counts[m.memory_type] = type_counts.get(m.memory_type, 0) + 1
            total_importance += m.importance_score
        
        return {
            "total": len(memories),
            "by_type": type_counts,
            "avg_importance": total_importance / len(memories) if memories else 0,
        }
    
    async def _update_user_index(self, memory: Memory) -> None:
        """更新用户索引"""
        index_path = self._get_index_path(memory.user_id)
        
        if index_path.exists():
            with open(index_path, 'r', encoding='utf-8') as f:
                memory_ids = json.load(f)
        else:
            memory_ids = []
        
        if memory.id not in memory_ids:
            memory_ids.append(memory.id)
        
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(memory_ids, f)
    
    async def _remove_from_index(self, memory: Memory) -> None:
        """从用户索引中移除"""
        index_path = self._get_index_path(memory.user_id)
        
        if not index_path.exists():
            return
        
        with open(index_path, 'r', encoding='utf-8') as f:
            memory_ids = json.load(f)
        
        if memory.id in memory_ids:
            memory_ids.remove(memory.id)
        
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(memory_ids, f)
```

### 4.6 记忆管理器（核心业务逻辑）

```python
import json
from typing import List, Optional, Dict, Any
from pathlib import Path

from .memory import Memory, MemoryType, MemorySearchResult
from .provider import MemoryProvider
from .postgres import PostgreSQLMemoryProvider
from .local import LocalMemoryProvider

class MemoryManager:
    """
    记忆管理器 - 核心业务逻辑层
    
    职责:
    1. 提供统一的记忆存取接口
    2. 管理记忆生命周期（创建、更新、过期处理）
    3. 协调不同存储后端
    4. 与 LangGraph 的 PostgresStore 集成
    """
    
    def __init__(self, config_path: str = "config.json"):
        self.config = self._load_config(config_path)
        self.provider: MemoryProvider = self._create_provider()
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """加载配置文件"""
        if Path(config_path).exists():
            with open(config_path, 'r') as f:
                return json.load(f)
        return self._default_config()
    
    def _default_config(self) -> Dict[str, Any]:
        """默认配置"""
        return {
            "memory": {
                "provider": "postgresql",
                "postgresql": {
                    "connection": "postgresql://user:pass@localhost:5432/antchat",
                    "vector_dim": 1536,
                    "embedding_model": "text-embedding-3-small"
                },
                "local": {
                    "path": "./memory"
                },
                "memory": {
                    "max_size_mb": 1024,
                    "default_ttl_days": 90,
                    "importance_threshold": 0.7,
                    "gc_interval_hours": 24
                }
            }
        }
    
    def _create_provider(self) -> MemoryProvider:
        """根据配置创建存储后端"""
        memory_config = self.config.get("memory", {})
        provider_type = memory_config.get("provider", "postgresql")
        
        if provider_type == "local":
            local_config = memory_config.get("local", {})
            return LocalMemoryProvider(
                base_path=local_config.get("path", "./memory")
            )
        elif provider_type == "postgresql":
            pg_config = memory_config.get("postgresql", {})
            mem_config = memory_config.get("memory", {})
            return PostgreSQLMemoryProvider(
                connection_string=pg_config.get("connection", ""),
                vector_dim=pg_config.get("vector_dim", 1536),
                embedding_model=pg_config.get("embedding_model", "text-embedding-3-small"),
                default_ttl_days=mem_config.get("default_ttl_days", 90),
            )
        else:
            raise ValueError(f"Unknown memory provider: {provider_type}")
    
    async def init(self) -> None:
        """初始化记忆管理器"""
        await self.provider.init()
    
    # ============ 记忆存取 ============
    
    async def remember(
        self,
        user_id: str,
        content: str,
        session_id: Optional[str] = None,
        memory_type: MemoryType = MemoryType.FACT,
        importance: float = 0.5,
        source_message_id: Optional[str] = None,
    ) -> str:
        """存储新的记忆"""
        memory = Memory(
            user_id=user_id,
            session_id=session_id,
            content=content,
            content_hash="",  # 将由 provider 生成
            memory_type=memory_type,
            importance_score=importance,
            source_message_id=source_message_id,
        )
        
        return await self.provider.store(memory)
    
    async def recall(
        self,
        user_id: str,
        query: str,
        limit: int = 10,
        memory_type: Optional[MemoryType] = None,
    ) -> List[MemorySearchResult]:
        """检索相关记忆"""
        return await self.provider.search(
            query=query,
            user_id=user_id,
            limit=limit,
            memory_type=memory_type,
        )
    
    async def get_memory(
        self,
        memory_id: str
    ) -> Optional[Memory]:
        """获取单条记忆"""
        return await self.provider.get(memory_id)
    
    async def forget(
        self,
        memory_id: str
    ) -> bool:
        """删除记忆"""
        return await self.provider.delete(memory_id)
    
    async def update_importance(
        self,
        memory_id: str,
        importance: float
    ) -> bool:
        """更新记忆重要性"""
        return await self.provider.update(
            memory_id,
            {"importance_score": importance}
        )
    
    async def pin_memory(
        self,
        memory_id: str,
        pinned: bool = True
    ) -> bool:
        """置顶记忆（不会被自动清理）"""
        return await self.provider.update(
            memory_id,
            {"is_pinned": pinned}
        )
    
    # ============ 记忆管理 ============
    
    async def list_memories(
        self,
        user_id: str,
        memory_type: Optional[MemoryType] = None,
        limit: int = 100,
    ) -> List[Memory]:
        """列出用户的所有记忆"""
        return await self.provider.list_by_user(
            user_id=user_id,
            memory_type=memory_type,
            limit=limit,
        )
    
    async def get_user_profile(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """
        获取用户画像（从记忆中提取）
        用于向 AI 提供用户背景信息
        """
        facts = await self.provider.search(
            query="",
            user_id=user_id,
            memory_type=MemoryType.FACT,
            limit=20,
        )
        
        preferences = await self.provider.search(
            query="",
            user_id=user_id,
            memory_type=MemoryType.PREFERENCE,
            limit=20,
        )
        
        return {
            "facts": [r.memory.content for r in facts],
            "preferences": [r.memory.content for r in preferences],
        }
    
    async def cleanup_expired(self) -> int:
        """清理过期记忆，返回删除数量"""
        return await self.provider.delete_expired()
    
    async def get_stats(self, user_id: str) -> Dict[str, Any]:
        """获取用户记忆统计"""
        return await self.provider.get_stats(user_id)
    
    # ============ 与 LangGraph 集成 ============
    
    async def get_recent_memories(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[str]:
        """
        获取最近的记忆内容列表
        用于在对话开始时注入上下文
        """
        memories = await self.provider.list_by_user(
            user_id=user_id,
            limit=limit,
        )
        
        return [m.content for m in memories]
    
    def build_memory_context(
        self,
        user_id: str,
        memories: List[Memory]
    ) -> str:
        """
        构建记忆上下文字符串
        用于插入到 system prompt 或对话历史中
        """
        if not memories:
            return ""
        
        sections = []
        
        # 按类型分组
        by_type = {}
        for m in memories:
            by_type.setdefault(m.memory_type, []).append(m)
        
        for memory_type, items in by_type.items():
            if items:
                type_label = {
                    MemoryType.FACT: "已知事实",
                    MemoryType.PREFERENCE: "偏好",
                    MemoryType.ENTITY: "相关实体",
                    MemoryType.SUMMARY: "历史摘要",
                    MemoryType.CUSTOM: "其他信息",
                }.get(memory_type, memory_type)
                
                sections.append(f"【{type_label}】")
                for item in items:
                    sections.append(f"- {item.content}")
                sections.append("")
        
        return "\n".join(sections).strip()
```

### 4.7 与现有模块的集成

```python
# 在 main.py 中的集成示例

from models.memory_manager import MemoryManager, MemoryType

# 全局记忆管理器实例
memory_manager: MemoryManager

def create_graph() -> CompiledStateGraph:
    global memory_manager
    
    graph = StateGraph(MessagesState)
    graph.add_node("chatbot", chatbot)
    graph.set_entry_point("chatbot")
    graph.set_finish_point("chatbot")
    
    # ... 现有的 checkpointer 和 store 配置 ...
    
    return graph.compile(checkpointer=checkpointer, store=store)

@asynccontextmanager
async def lifespan(app: FastAPI):
    global memory_manager
    
    # ... 其他初始化 ...
    
    # 初始化记忆管理器
    memory_manager = MemoryManager(config_path="config.json")
    await memory_manager.init()
    
    yield
    
    # 清理
    del memory_manager

# 对话处理中的记忆调用示例
async def handle_chat(request: ChatRequest) -> ChatResponse:
    global memory_manager
    
    user_id = request.user_id
    conversation_id = request.conversation_id
    
    # 1. 获取用户背景记忆
    recent_memories = await memory_manager.get_recent_memories(
        user_id=user_id,
        limit=5
    )
    
    # 2. 构建记忆上下文
    memory_context = ""
    if recent_memories:
        memory_context = "\n\n【用户背景】\n" + "\n".join(f"- {m}" for m in recent_memories)
    
    # 3. 在调用 LLM 时注入记忆上下文（通过 system message 或在消息处理中）
    
    # 4. 对话结束后，提取并保存新记忆
    # 这里需要调用 LLM 或使用规则来识别重要信息
    # await extract_and_save_memories(user_id, conversation_id, messages, response)
    
    return response
```

---

## 五、API 接口设计

### 5.1 记忆管理 API

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter(prefix="/v1/memory", tags=["memory"])

class RememberRequest(BaseModel):
    user_id: str
    content: str
    session_id: Optional[str] = None
    memory_type: str = "fact"  # fact, preference, entity, summary, custom
    importance: float = 0.5

class RecallRequest(BaseModel):
    user_id: str
    query: str
    limit: int = 10
    memory_type: Optional[str] = None

class MemoryResponse(BaseModel):
    id: str
    user_id: str
    content: str
    memory_type: str
    importance_score: float
    created_at: str
    is_pinned: bool

@router.post("/remember", response_model=dict)
async def remember(request: RememberRequest):
    """存储新记忆"""
    memory_id = await memory_manager.remember(
        user_id=request.user_id,
        content=request.content,
        session_id=request.session_id,
        memory_type=MemoryType(request.memory_type),
        importance=request.importance,
    )
    return {"id": memory_id, "status": "stored"}

@router.post("/recall", response_model=List[dict])
async def recall(request: RecallRequest):
    """检索相关记忆"""
    results = await memory_manager.recall(
        user_id=request.user_id,
        query=request.query,
        limit=request.limit,
        memory_type=MemoryType(request.memory_type) if request.memory_type else None,
    )
    return [
        {
            "id": r.memory.id,
            "content": r.memory.content,
            "memory_type": r.memory.memory_type,
            "importance_score": r.memory.importance_score,
            "score": r.score,
        }
        for r in results
    ]

@router.get("/{memory_id}", response_model=MemoryResponse)
async def get_memory(memory_id: str):
    """获取单条记忆"""
    memory = await memory_manager.get_memory(memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    return MemoryResponse(**memory.model_dump())

@router.delete("/{memory_id}")
async def forget(memory_id: str):
    """删除记忆"""
    success = await memory_manager.forget(memory_id)
    return {"status": "deleted" if success else "not_found"}

@router.get("/user/{user_id}", response_model=List[MemoryResponse])
async def list_user_memories(
    user_id: str,
    memory_type: Optional[str] = None,
    limit: int = 100,
):
    """列出用户的所有记忆"""
    memories = await memory_manager.list_memories(
        user_id=user_id,
        memory_type=MemoryType(memory_type) if memory_type else None,
        limit=limit,
    )
    return [MemoryResponse(**m.model_dump()) for m in memories]

@router.get("/user/{user_id}/stats")
async def get_user_stats(user_id: str):
    """获取用户记忆统计"""
    return await memory_manager.get_stats(user_id)

@router.post("/cleanup")
async def cleanup_expired():
    """清理过期记忆"""
    count = await memory_manager.cleanup_expired()
    return {"deleted_count": count}
```

---

## 六、配置管理

### 6.1 配置文件示例 (config.json)

```json
{
  "memory": {
    "provider": "postgresql",
    
    "local": {
      "path": "./memory"
    },
    
    "postgresql": {
      "connection": "postgresql://user:password@localhost:5432/antchat",
      "pool_size": 10,
      "vector_dim": 1536,
      "embedding_model": "text-embedding-3-small"
    },
    
    "memory": {
      "max_size_mb": 1024,
      "default_ttl_days": 90,
      "importance_threshold": 0.7,
      "gc_interval_hours": 24,
      "max_memories_per_user": 10000
    }
  }
}
```

### 6.2 环境变量覆盖

```bash
# .env
MEMORY_PROVIDER=postgresql
MEMORY_POSTGRESQL_CONNECTION=postgresql://user:password@localhost:5432/antchat
MEMORY_LOCAL_PATH=./memory
MEMORY_DEFAULT_TTL_DAYS=90
```

---

## 七、目录结构

```
ant-chat/
├── main.py                      # 应用入口
├── config.json                  # 配置文件
├── models/
│   ├── user.py                  # 用户模块（已有）
│   ├── conversation.py          # 会话管理（已有）
│   └── memory/                  # 新增：记忆模块
│       ├── __init__.py
│       ├── memory.py            # 记忆数据模型
│       ├── types.py             # 记忆类型枚举
│       ├── provider.py          # 存储后端抽象接口
│       ├── postgres.py          # PostgreSQL Provider
│       ├── local.py             # 本地文件系统 Provider
│       ├── manager.py           # 记忆管理器
│       └── api.py               # 记忆管理 API
├── docs/
│   └── memory_design.md         # 本文档
└── tests/
    └── test_memory.py           # 记忆模块测试
```

---

## 八、迁移策略

### 8.1 从现有 PostgresStore 迁移

现有系统使用 LangGraph 的 `PostgresStore`，迁移步骤：

1. **保留现有数据**：可将 PostgresStore 中的数据导出并导入新系统
2. **双写阶段**：新系统与 PostgresStore 同时写入，验证一致性
3. **灰度切换**：逐步将流量切换到新系统
4. **完全切换**：确认无误后，关闭 PostgresStore 相关代码

### 8.2 存储后端切换

通过修改 `config.json` 中的 `memory.provider` 字段，可以无缝切换存储后端：

```bash
# 切换到本地存储
# 1. 修改配置
sed -i 's/"provider": "postgresql"/"provider": "local"/' config.json

# 2. 重启服务
# 新数据将写入本地文件系统

# 切换回 PostgreSQL
# 1. 修改配置
sed -i 's/"provider": "local"/"provider": "postgresql"/' config.json

# 2. 重启服务
```

---

## 九、总结

### 9.1 推荐方案

| 方面 | 推荐 |
|------|------|
| **方案选择** | 方案 C（混合方案） |
| **存储后端** | PostgreSQL + pgvector（保持现有投资） |
| **记忆类型** | FACT / PREFERENCE / ENTITY / SUMMARY |
| **扩展方向** | 可按需集成 Mem0 的高级提取能力 |

### 9.2 实施计划

| 阶段 | 任务 | 预估时间 |
|------|------|----------|
| Phase 1 | 基础存储层（Provider 抽象 + PostgreSQL 实现） | 3-5 天 |
| Phase 2 | 本地文件系统 Provider | 1-2 天 |
| Phase 3 | 记忆管理器核心逻辑 | 3-4 天 |
| Phase 4 | API 接口与 main.py 集成 | 2-3 天 |
| Phase 5 | 测试与调优 | 2-3 天 |
| **总计** | | **11-17 天** |

### 9.3 风险与缓解

| 风险 | 缓解措施 |
|------|----------|
| 向量检索性能不足 | 使用 pgvector 的 IVFFlat 索引，预分区 |
| 存储空间快速增长 | 实现记忆衰减和重要性阈值过滤 |
| 与现有模块兼容性问题 | 提供 Adapter 模式，保持接口兼容 |
| 迁移数据丢失 | 双写验证，灰度发布 |

---

*文档版本: 1.0*
*创建日期: 2026-04-09*
*项目: ant-chat 长期记忆功能设计*
