# ant-chat 代码编写 Agent 功能增强设计方案

## 一、项目现状与差距分析

### 1.1 当前 ant-chat 已具备能力

| 能力模块 | 状态 | 说明 |
|----------|------|------|
| 对话管理 | ✅ 完成 | 创建、查询、逻辑删除、重命名 |
| 用户模块 | ✅ 完成 | 极简用户体系，username hash 生成 user_id |
| Reflex UI | ✅ 完成 | Web 前端界面 |
| 短期记忆 | ✅ 完成 | LangGraph PostgresSaver，同 conversation_id 保持 |
| 长期记忆 | ✅ 设计完成 | 已有设计文档（memory_design.md） |
| 上下文压缩 | ✅ 设计完成 | 已有设计文档（context_compression_design.md） |
| 聊天能力 | ✅ 完成 | 流式/非流式响应，支持多轮对话 |

### 1.2 与专业代码编写 Agent 的能力差距

对标专业代码编写 Agent（GitHub Copilot、Cursor、Claude Code、Devin）：

| 能力维度 | ant-chat 当前 | 专业 Agent | 差距等级 |
|----------|--------------|----------|----------|
| **文件操作** | ❌ 无 | ✅ 读写、搜索、创建 | 高 |
| **终端执行** | ❌ 无 | ✅ git/npm/python 等 | 高 |
| **代码编辑** | ❌ 无 | ✅ 智能修改、diff | 高 |
| **自主执行** | ❌ 纯问答 | ✅ 无人干预完成任务 | 高 |
| **任务规划** | ❌ 无 | ✅ 自动拆解复杂任务 | 中 |
| **测试调试** | ❌ 无 | ✅ 运行测试、debug | 中 |
| **项目理解** | ❌ 无 | ✅ 理解依赖、构建 | 中 |
| **多 Agent 协作** | ❌ 无 | ✅ Specialized agents | 低 |

---

## 二、需要补充的功能清单

### 2.1 核心功能（高优先级）

#### F1: 文件系统操作引擎
- **功能描述**: 赋予 Agent 读写、搜索、创建文件的能力
- **解决问题**: Agent 无法操作源代码，无法实现代码编写核心需求
- **实现方案**: 
  - 基于 LangGraph 节点封装文件系统操作
  - 支持目录遍历、文件查找、代码搜索（rg/grep）
  - 支持 read/write/edit 三种操作模式
- **优先级**: 🔴 高

#### F2: 终端命令执行引擎
- **功能描述**: 支持执行 Shell 命令（git、npm、python、docker 等）
- **解决问题**: 无法运行代码、测试、构建，无法与开发工具链集成
- **实现方案**:
  - 基于 subprocess 封装命令执行
  - 支持工作目录、超时、env 配置
  - 支持流式输出和结果捕获
- **优先级**: 🔴 高

#### F3: 代码编辑智能体
- **功能描述**: 智能修改代码文件（而非简单替换）
- **解决问题**: 实现真正的代码编写，而非仅仅输出文本
- **实现方案**:
  - 实现精确的代码定位（行号、函数、类）
  - 支持安全编辑（read-modify-write 模式）
  - 支持多文件批量修改
- **优先级**: 🔴 高

#### F4: 任务规划与执行智能体
- **功能描述**: 将复杂任务自动拆解为可执行步骤
- **解决问题**: 从"问答"升级为"自主执行"
- **实现方案**:
  - 基于 LangGraph 实现任务分解图
  - 实现"思考-执行-验证"循环
  - 支持回滚和重试机制
- **优先级**: 🔴 高

### 2.2 扩展功能（中优先级）

#### F5: 项目上下文理解
- **功能描述**: 理解项目结构、依赖、技术栈
- **解决问题**: Agent 需要理解项目才能写出正确代码
- **实现方案**:
  - 自动解析 package.json/pyproject.toml
  - 构建项目依赖图
  - 提取配置文件（.env, tsconfig, pytest.ini 等）
- **优先级**: 🟡 中

#### F6: 测试与调试运行器
- **功能描述**: 运行测试、获取结果、辅助调试
- **解决问题**: 完成代码编写后需要验证
- **实现方案**:
  - 自动检测项目测试框架（pytest/jest）
  - 执行测试并解析结果
  - ���取测试失败原因并反馈
- **优先级**: 🟡 中

#### F7: 代码审查增强
- **功能描述**: 自动审查代码质量问题
- **解决问题**: 提供质量保障
- **实现方案**:
  - 集成 linter（ESLint, pylint）
  - 集成类型检查（TypeScript, mypy）
  - 集成安全扫描（bandit, semgrep）
- **优先级**: 🟡 中

#### F8: 智能记忆增强
- **功能描述**: 增强现有长期记忆，存储代码知识
- **解决问题**: 记住项目规范、代码模式、技术债务
- **实现方案**:
  - 扩展现有 PostgresStore 方案
  - 实现代码片段存储和检索
  - 实现项目级别记忆
- **优先级**: 🟡 中

### 2.3 高级功能（低优先级）

#### F9: 多智能体协作
- **功能描述**: 支持 specialized agents（reviewer、tester、doc-writer）
- **解决问题**: 复杂任务分工协作
- **实现方案**:
  - 实现 Agent Registry
  - 实现 agent 通信协议
  - 实现任务分发机制
- **优先级**: 🟢 低

#### F10: 持续任务执行
- **功能描述**: 后台任务执行，支持长时间运行
- **解决问题**: 复杂任务需要持续执行
- **实现方案**:
  - 实现任务队列
  - 实现进度报告
  - 支持中断和恢复
- **优先级**: 🟢 低

---

## 三、详细架构设计

### 3.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                     ant-chat Agent                            │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│  │   Chat     │  │  Task      │  │  Review   │           │
│  │   Agent   │  │  Planner  │  │  Agent    │           │
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘           │
│        │             │             │                    │
│  ┌─────▼─────────────▼─────────────▼─────┐                │
│  │         LangGraph Orchestrator       │                │
│  │   (任务编排 + 状态管理 + 记忆)      │                │
│  └──────────────────┬────────────────┘                │
│                     │                                      │
│  ┌──────────────────▼────────────────┐                │
│  │        Tool Executor Layer         │                │
│  │  ┌─────────┐ ┌─────────┐ ┌───────┐ │                │
│  │  │  File   │ │ Command│ │ Edit  │ │                │
│  │  │  Ops    │ │ Runner │ │ Engine│ │                │
│  │  └─────────┘ └─────────┘ └───────┘ │                │
│  └───────────────────────────────────┘                │
│                     │                                      │
│  ┌──────────────────▼────────────────┐                │
│  │      Storage Layer (PostgreSQL)     │                │
│  │  ┌─────────┐ ┌─────────┐ ┌───────┐ │                │
│  │  │Memory  │ │Checkptr │ │Project│ │                │
│  │  │Store   │ │Saver   │ │Graph │ │                │
│  │  └─────────┘ └─────────┘ └───────┘ │                │
│  └───────────────────────────────────┘                │
└─────────────────────────────────────────────────────┘
```

### 3.2 核心模块详细设计

#### 3.2.1 文件系统操作引擎

```python
# 模块位置: tools/file_ops.py

class FileOperations:
    """文件操作引擎"""
    
    def read_file(self, path: str, offset: int = 0, limit: int = None) -> str:
        """读取文件内容"""
        pass
    
    def write_file(self, path: str, content: str) -> bool:
        """写入文件内容"""
        pass
    
    def edit_file(self, path: str, old_text: str, new_text: str) -> bool:
        """编辑文件（精确替换）"""
        pass
    
    def search_files(self, pattern: str, path: str = ".") -> List[SearchResult]:
        """代码搜索"""
        pass
    
    def list_directory(self, path: str, recursive: bool = False) -> List[FileInfo]:
        """列出目录"""
        pass
    
    def ensure_directory(self, path: str) -> bool:
        """确保目录存在"""
        pass
```

**与 LangGraph 集成**:

```python
def create_file_ops_node():
    """创建文件操作节点"""
    
    def file_ops_node(state: AgentState) -> dict:
        tool_calls = state.get("tool_calls", [])
        results = []
        
        for call in tool_calls:
            if call["tool"] == "read":
                result = file_ops.read_file(call["path"])
            elif call["tool"] == "write":
                result = file_ops.write_file(call["path"], call["content"])
            elif call["tool"] == "edit":
                result = file_ops.edit_file(call["path"], call["old"], call["new"])
            # ...
            results.append(result)
        
        return {"tool_results": results}
    
    return file_ops_node
```

#### 3.2.2 终端命令执行引擎

```python
# 模块位置: tools/command_runner.py

class CommandRunner:
    """命令执行引擎"""
    
    def __init__(self, workdir: str = ".", timeout: int = 300):
        self.workdir = workdir
        self.timeout = timeout
    
    def run(
        self, 
        command: str, 
        env: dict = None,
        timeout: int = None,
        capture_output: bool = True
    ) -> CommandResult:
        """执行命令"""
        pass
    
    def stream(
        self, 
        command: str, 
        callback: Callable[[str], None]
    ) -> CommandResult:
        """流式执行（用于长时间输出）"""
        pass
    
    def detect_framework(self) -> str:
        """自动检测项目框架类型"""
        pass
    
    def get_build_command(self) -> str:
        """获取构建命令"""
        pass
    
    def get_test_command(self) -> str:
        """获取测试命令"""
        pass
```

**支持检测的框架**:

| 框架 | 语言 | 检测文件 | 构建命令 | 测试命令 |
|------|------|----------|----------|----------|
| Node.js | JS/TS | package.json | npm run build | npm test |
| Python | Python | pyproject.toml | python -m build | pytest |
| Go | Go | go.mod | go build | go test |
| Rust | Rust | Cargo.toml | cargo build | cargo test |
| Django | Python | manage.py | python manage.py migrate | python manage.py test |

#### 3.2.3 代码编辑智能体

```python
# 模块位置: agents/code_editor.py

class CodeEditor:
    """代码编辑智能体"""
    
    def __init__(self, file_ops: FileOperations, llm: LLM):
        self.file_ops = file_ops
        self.llm = llm
    
    async def edit(
        self,
        path: str,
        instructions: str,
        context: dict = None
    ) -> EditResult:
        """根据自然语言指令编辑代码"""
        pass
    
    async def create(
        self,
        path: str,
        spec: str,
        context: dict = None
    ) -> EditResult:
        """根据规格创建新文件"""
        pass
    
    async def apply_patch(
        self,
        path: str,
        patch: str
    ) -> EditResult:
        """应用 Unified Diff Patch"""
        pass
    
    def validate(
        self,
        path: str,
        syntax: bool = True,
        types: bool = False
    ) -> ValidationResult:
        """验证代码语法"""
        pass
```

**编辑流程**:

```
1. 分析指令
   ↓
2. 读取原文件
   ↓
3. 定位编辑位置（函数/类/行）
   ↓
4. 生成修改内容（LLM）
   ↓
5. 应用修改
   ↓
6. 验证语法
   ↓
7. 返回结果
```

#### 3.2.4 任务规划与执行智能体

```python
# 模块位置: agents/task_planner.py

class TaskPlanner:
    """任务规划智能体"""
    
    def __init__(self, llm: LLM):
        self.llm = llm
    
    async def plan(
        self,
        goal: str,
        context: ProjectContext
    ) -> TaskPlan:
        """将目标拆解为任务步骤"""
        pass
    
    async def execute(
        self,
        plan: TaskPlan,
        executor: TaskExecutor
    ) -> ExecutionResult:
        """执行任务计划"""
        pass
    
    async def adjust(
        self,
        plan: TaskPlan,
        feedback: str
    ) -> TaskPlan:
        """根据反馈调整计划"""
        pass
```

**任务图定义**:

```python
def create_task_graph() -> StateGraph:
    """创建任务执行图"""
    
    graph = StateGraph(AgentState)
    
    # 节点定义
    graph.add_node("analyze", analyze_goal)
    graph.add_node("plan", create_plan)
    graph.add_node("execute", execute_step)
    graph.add_node("verify", verify_result)
    graph.add_node("retry", retry_failed)
    
    # 边定义
    graph.set_entry_point("analyze")
    graph.add_edge("analyze", "plan")
    graph.add_edge("plan", "execute")
    graph.add_edge("execute", "verify")
    
    # 条件边（根据验证结果分支）
    graph.add_conditional_edges(
        "verify",
        {
            "success": "execute",  # 继续下一步
            "retry": "retry",      # 重试当前步
            "adjust": "plan",     # 调整计划
            "complete": END       # 完成任务
        }
    )
    
    return graph.compile()
```

### 3.3 数据模型设计

#### 3.3.1 Agent State

```python
class AgentState(TypedDict):
    """Agent 状态"""
    
    # 对话相关
    messages: List[BaseMessage]
    
    # 任务相关
    current_task: Optional[Task]
    task_plan: Optional[TaskPlan]
    task_history: List[TaskResult]
    
    # 工具相关
    tool_calls: List[ToolCall]
    tool_results: List[ToolResult]
    
    # 项目上下文
    project_context: Optional[ProjectContext]
    
    # 记忆相关
    short_term_memory: List[MemoryItem]
    long_term_memory: List[MemoryItem]
    
    # 执行状态
    status: Literal["idle", "thinking", "executing", "verifying"]
    error: Optional[str]
```

#### 3.3.2 Project Context

```python
class ProjectContext(BaseModel):
    """项目上下文"""
    
    root: str                           # 项目根目录
    language: str                      # 主要语言 (python/js/go/rust)
    framework: Optional[str]           # 框架 (django/react/fastapi)
    build_system: str                 # 构建系统
    
    # 依赖信息
    dependencies: Dict[str, str]      # 依赖名 -> 版本
    dev_dependencies: Dict[str, str] # 开发依赖
    
    # 配置信息
    config_files: Dict[str, str]       # 配置文件名 -> 路径
    config: Dict[str, Any]           # 解析后的配置
    
    # 代码结构
    source_dirs: List[str]            # 源码目录
    test_dirs: List[str]             # 测试目录
    entry_points: List[str]          # 入口文件
```

#### 3.3.3 长期记忆存储

```python
# 表名: agent_memories

CREATE TABLE agent_memories (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         VARCHAR(64) NOT NULL,
    project_id     VARCHAR(64),
    memory_type    VARCHAR(32) NOT NULL,  -- 'code_pattern', 'project_spec', 'tech_debt'
    content        TEXT NOT NULL,
    embedding     VECTOR(1536),            -- OpenAI embedding
    importance    INTEGER DEFAULT 5,      -- 1-10
    access_count   INTEGER DEFAULT 0,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX idx_memories_user_project ON agent_memories(user_id, project_id);
CREATE INDEX idx_memories_embedding ON agent_memories USING ivfflat (embedding);
CREATE INDEX idx_memories_type ON agent_memories(memory_type);
```

---

## 四、API 设计

### 4.1 新增 API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /v1/execute | 执行任务 |
| POST | /v1/files/read | 读取文件 |
| POST | /v1/files/write | 写入文件 |
| POST | /v1/files/edit | 编辑文件 |
| POST | /v1/commands/run | 运行命令 |
| GET | /v1/project/context | 获取项目上下文 |
| POST | /v1/project/scan | 扫描项目 |

### 4.2 Execute API

```python
class ExecuteRequest(BaseModel):
    """任务执行请求"""
    goal: str                          # 目标描述
    context: Optional[ProjectContext]  # 项目上下文
    constraints: List[str] = []       # 约束条件
    max_steps: int = 10               # 最大步数
    stream: bool = False               # 是否流式输出

class ExecuteResponse(BaseModel):
    """任务执行响应"""
    task_id: str
    status: str                       # running/completed/failed
    steps: List[TaskStep]
    result: Optional[str]
    error: Optional[str]
```

---

## 五、实施路线图

### 5.1 阶段一：核心基础设施（2-3 周）

| 周次 | 任务 | 交付物 |
|------|------|--------|
| 1 | 文件操作引擎 | tools/file_ops.py |
| 1 | 命令执行引擎 | tools/command_runner.py |
| 2 | 代码编辑智能体 | agents/code_editor.py |
| 2 | 任务规划智能体 | agents/task_planner.py |
| 3 | LangGraph 集成 | main.py 扩展 |
| 3 | 单元测试 | tests/ |

**Milestone**: Agent 可以执行 "创建文件 X" 这类简单任务

### 5.2 阶段二：项目理解能力（2 周）

| 周次 | 任务 | 交付物 |
|------|------|--------|
| 4 | 项目扫描器 | tools/project_scanner.py |
| 4 | 依赖解析器 | tools/dependency_parser.py |
| 5 | 上下文构建器 | agents/context_builder.py |
| 5 | 智能记忆扩展 | models/memory.py 扩展 |

**Milestone**: Agent 理解项目结构，能写出正确的代码

### 5.3 阶段三：测试与质量（1-2 周）

| 周次 | 任务 | 交付物 |
|------|------|--------|
| 6 | 测试运行器 | tools/test_runner.py |
| 6 | 调试辅助 | tools/debugger.py |
| 7 | 代码审查 | agents/reviewer.py |
| 7 | Linter 集成 | tools/linter.py |

**Milestone**: Agent 可以完成代码编写-测试-修复的完整流程

### 5.4 阶段四：高级功能（2-3 周）

| 周次 | 任务 | 交付物 |
|------|------|--------|
| 8 | 多 Agent 协作 | agents/multi_agent.py |
| 8 | 持续执行 | services/executor.py |
| 9 | MCP 集成 | integrations/mcp.py |
| 9 | Webhook 回调 | services/webhook.py |

**Milestone**: 完整的企业级 Agent 能力

---

## 六、安全考虑

### 6.1 命令执行限制

```python
# 白名单允许列表
ALLOWED_COMMANDS = {
    "python": ["python", "python3", "pip", "pytest"],
    "node": ["node", "npm", "yarn", "pnpm"],
    "git": ["git"],
    "docker": ["docker", "docker-compose"],
    "system": ["ls", "cat", "grep", "find", "mkdir", "rm", "cp", "mv"],
}

# 黑名单禁止列表
BLOCKED_PATTERNS = [
    r"rm\s+-rf\s+/",           # 递归删除根目录
    r"curl.*\|.*sh",           # Pipe to shell
    r"wget.*\|.*sh",           # Pipe to shell
    r":(){.*:\|:}",            # Fork bomb
    r"chmod\s+777",            # 过度开放权限
    r"chown\s+-R",             # 递归修改所有者
]
```

### 6.2 文件操作保护

```python
# 禁止访问的路径
PROTECTED_PATTERNS = [
    "/etc/passwd",
    "/etc/shadow",
    "/.ssh/",
    "/.aws/",
    "**/.env",
    "**/credentials*",
    "**/secrets*",
    "**/keys*",
]

# 需要确认的危险操作
DANGEROUS_OPERATIONS = [
    "delete_file",
    "write_file",  # 覆���已有文件
    "create_file", # 创建可执行文件
]
```

---

## 七、总结

本设计文档详细描述了 ant-chat 从一个简单聊天机器人升级为专业代码编写 Agent 的完整方案。

### 核心价值

1. **完整工具链**: 文件操作 + 命令执行 + 代码编辑
2. **自主执行**: 任务规划 + 验证 + 重试
3. **项目理解**: 自动扫描 + 依赖解析 + 上下文构建
4. **质量保障**: 测试运行 + 代码审查 + 调试辅助

### 与现有架构集成

- **LangGraph**: 核心编排层扩展
- **PostgreSQL**: 记忆存储扩展
- **Reflex UI**: 交互界面扩展
- **现有设计文档**: 上下文压缩 + 长期记忆兼容

### 实施优先级

1. 🔴 高优先级：F1-F4（核心基础）
2. 🟡 中优先级：F5-F8（扩展能力）
3. 🟢 低优先级：F9-F10（高级特性）

---

*文档版本: 1.0*
*创建时间: 2026-04-10*