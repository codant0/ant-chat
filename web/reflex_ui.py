"""
Ant Chat - Reflex UI
基于 Reflex 框架重构的个人AI聊天工具

配色方案：
- 联通品牌蓝色系：#0071BC, #1996E5
- 强调色：红色 #E60000
- 背景：浅灰 #F5F5F5
- 卡片：白色 #FFFFFF

使用方法:
    cd /root/.openclaw/workspace/data/projects/ant-chat
    reflex run web.reflex_ui:app
"""

import hashlib
import uuid
from typing import List, Dict, Optional

import reflex as rx


# ============ 颜色常量 =============

COLORS = {
    "primary_blue": "#0071BC",
    "light_blue": "#1996E5",
    "accent_red": "#E60000",
    "bg_gray": "#F5F5F5",
    "card_white": "#FFFFFF",
    "text_dark": "#333333",
    "text_light": "#666666",
    "border_light": "#E0E0E0",
}


# ============ 应用状态 ============

class State(rx.State):
    """聊天应用状态"""
    
    # 用户状态
    user_initialized: bool = False
    username: str = ""
    user_id: str = ""
    
    # 对话状态
    conversation_id: str = ""
    conversations: List[Dict] = []
    messages: List[Dict] = []
    
    # UI状态
    editing_conversation_id: str = ""
    editing_name: str = ""
    input_message: str = ""
    is_streaming: bool = True
    is_loading: bool = False
    is_pending: bool = False  # 显示pending状态
    streaming_content: str = ""  # 流式输出的中间内容
    pending_indicator: str = ""  # pending动画指示器
    
    # ===== 用户管理 =====
    
    def get_user_id(self, username: str) -> str:
        """根据用户名生成用户ID"""
        return hashlib.md5(username.encode()).hexdigest()[:12]
    
    def init_user(self, form_data: Dict):
        """初始化用户"""
        username = form_data.get("username", "").strip()
        if username:
            self.username = username
            self.user_id = self.get_user_id(username)
            self.conversations = self.get_conversations_api()
            self.user_initialized = True
            self.conversation_id = ""  # 不创建默认对话，等用户发消息时再创建
            self.messages = []

    def get_messages_api(self, conversation_id: str) -> List[Dict]:
        """获取对话的消息历史"""
        import requests
        try:
            response = requests.get(
                f"http://localhost:8012/v1/conversations/{conversation_id}/messages",
                timeout=10
            )
            response.raise_for_status()
            return response.json().get("messages", [])
        except Exception:
            return []

    # ===== API 调用 =====
    
    def get_conversations_api(self) -> List[Dict]:
        """获取对话列表"""
        import requests
        try:
            response = requests.get(
                "http://localhost:8012/v1/conversations",
                params={"user_id": self.user_id},
                timeout=10
            )
            response.raise_for_status()
            return response.json().get("conversations", [])
        except Exception:
            return self.conversations
    
    def create_conversation_api(self, conversation_name: str = "") -> Optional[Dict]:
        """创建新对话"""
        import requests
        try:
            response = requests.post(
                "http://localhost:8012/v1/conversations",
                json={
                    "user_id": self.user_id,
                    "username": self.username,
                    "conversation_name": conversation_name
                },
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception:
            return {"id": str(uuid.uuid4()), "conversation_name": conversation_name or "新对话"}
    
    def delete_conversation_api(self, conversation_id: str) -> bool:
        """删除对话"""
        import requests
        try:
            response = requests.delete(
                f"http://localhost:8012/v1/conversations/{conversation_id}",
                timeout=10
            )
            response.raise_for_status()
            return True
        except Exception:
            return True
    
    def rename_conversation_api(self, conversation_id: str, new_name: str) -> Optional[Dict]:
        """重命名对话"""
        import requests
        try:
            response = requests.patch(
                f"http://localhost:8012/v1/conversations/{conversation_id}",
                json={"conversation_name": new_name},
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception:
            return {"id": conversation_id, "conversation_name": new_name}
    
    # ===== 对话管理 =====

    def create_conversation(self):
        """创建新对话（立即创建）"""
        # 立即创建新对话，使用临时名称
        new_conv = self.create_conversation_api("新对话")
        if new_conv:
            self.conversation_id = new_conv.get("id", str(uuid.uuid4()))
            new_conv["conversation_name"] = "新对话"
            self.conversations = [new_conv] + self.conversations
        else:
            self.conversation_id = str(uuid.uuid4())
            self.conversations.insert(0, {
                "id": self.conversation_id,
                "conversation_name": "新对话"
            })
        self.messages = []
        self.editing_conversation_id = ""
    
    def switch_conversation(self, conversation_id: str):
        """切换对话"""
        self.conversation_id = conversation_id
        self.messages = self.get_messages_api(conversation_id)
        self.editing_conversation_id = ""
    
    def delete_conversation(self, conversation_id: str):
        """删除对话"""
        self.delete_conversation_api(conversation_id)
        self.conversations = [c for c in self.conversations if c["id"] != conversation_id]

        if conversation_id == self.conversation_id:
            if self.conversations:
                self.conversation_id = self.conversations[0]["id"]
                self.messages = self.get_messages_api(self.conversation_id)
            else:
                self.create_conversation()
    
    def start_rename(self, conversation_id: str):
        """开始重命名"""
        conv = next((c for c in self.conversations if c["id"] == conversation_id), None)
        self.editing_conversation_id = conversation_id
        self.editing_name = conv.get("conversation_name", "") if conv else ""
    
    def save_rename(self):
        """保存重命名"""
        if self.editing_conversation_id and self.editing_name.strip():
            new_name = self.editing_name.strip()
            for conv in self.conversations:
                if conv["id"] == self.editing_conversation_id:
                    conv["conversation_name"] = new_name
                    break
            self.rename_conversation_api(self.editing_conversation_id, new_name)
        
        self.editing_conversation_id = ""
        self.editing_name = ""
    
    def cancel_rename(self):
        """取消重命名"""
        self.editing_conversation_id = ""
        self.editing_name = ""
    
    # ===== 聊天功能 =====
    
    def generate_conversation_name(self, first_question: str, max_length: int = 20) -> str:
        """根据用户第一条问题生成对话名称"""
        question = ' '.join(first_question.split())
        if len(question) <= max_length:
            return question
        truncated = question[:max_length]
        if truncated[-1] not in ' \t\n.,!?;:':
            last_space = truncated.rfind(' ')
            if last_space > 0:
                truncated = truncated[:last_space]
        return truncated.strip()
    
    def send_message(self):
        """发送消息 - 处理对话创建和AI回复"""
        if not self.input_message.strip():
            return

        import requests
        import base64

        user_message = self.input_message.strip()
        self.input_message = ""

        # 检查当前对话是否已存在于对话列表中
        current_conv_exists = any(c["id"] == self.conversation_id for c in self.conversations)

        # 如果是对话列表中没有的对话，需要先创建
        # 或者当前对话名称是"新对话"，需要更新为基于第一条消息的名称
        if not current_conv_exists or not self.conversation_id:
            # 使用前端生成对话名称
            conv_name = self.generate_conversation_name(user_message)
            new_conv = self.create_conversation_api(conv_name)
            if new_conv:
                self.conversation_id = new_conv.get("id", str(uuid.uuid4()))
                # 更新返回的对话名称（后端可能进一步处理）
                if new_conv.get("conversation_name"):
                    conv_name = new_conv["conversation_name"]
                # 确保使用最新的名称
                new_conv["conversation_name"] = conv_name
                self.conversations = [new_conv] + self.conversations
            else:
                self.conversation_id = str(uuid.uuid4())
                self.conversations.insert(0, {
                    "id": self.conversation_id,
                    "conversation_name": conv_name
                })
        elif current_conv_exists:
            # 检查当前对话名称是否为"新对话"，如果是则更新
            current_conv = next((c for c in self.conversations if c["id"] == self.conversation_id), None)
            if current_conv and current_conv.get("conversation_name") == "新对话":
                conv_name = self.generate_conversation_name(user_message)
                # 更新本地列表中的名称
                current_conv["conversation_name"] = conv_name
                # 也在后端更新
                self.rename_conversation_api(self.conversation_id, conv_name)

        # 添加用户消息
        self.messages = self.messages + [{"role": "user", "content": user_message}]
        self.is_pending = True
        self.streaming_content = ""
        self.pending_indicator = "⠋"

        # yield 让UI更新，显示pending状态
        yield

        try:
            response = requests.post(
                "http://localhost:8012/v1/chat",
                json={
                    "messages": self.messages,
                    "is_stream": self.is_streaming,
                    "user_id": self.user_id,
                    "conversation_id": self.conversation_id
                },
                stream=self.is_streaming,
                timeout=120
            )
            response.raise_for_status()

            # 非流式响应处理
            if not self.is_streaming:
                result = response.json()
                full_content = result.get("content", "")
                self.streaming_content = ""
                self.messages = self.messages + [{"role": "assistant", "content": full_content}]
                self.conversations = self.get_conversations_api()
                self.is_pending = False
                self.pending_indicator = ""
                return

            full_content = ""
            pending_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
            pending_idx = 0

            # 处理SSE流式响应
            for line in response.iter_lines(decode_unicode=True):
                line = line.strip()
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        decoded = base64.b64decode(data.encode('ascii')).decode('utf-8')
                    except Exception:
                        decoded = data

                    # 逐字符添加并立即更新UI（打字机效果）
                    for char in decoded:
                        full_content += char
                        self.streaming_content = full_content + "▌"
                        pending_idx = (pending_idx + 1) % len(pending_chars)
                        self.pending_indicator = pending_chars[pending_idx]
                        # 立即yield触发UI更新
                        yield

            # 最终更新：移除光标并保存完整消息
            self.streaming_content = ""
            self.messages = self.messages + [{"role": "assistant", "content": full_content}]

            # 重新获取对话列表，确保左侧标题已更新为后端归纳的名称
            yield
            self.conversations = self.get_conversations_api()
        except Exception as e:
            print(f"请求失败: {e}")
            self.streaming_content = ""
            self.messages = self.messages + [{"role": "assistant", "content": f"抱歉，发生了错误: {str(e)}"}]
        finally:
            self.is_pending = False
            self.pending_indicator = ""


# ============ UI 组件 ============

def render_username_modal() -> rx.Component:
    """用户名输入模态框"""
    return rx.box(
        # 遮罩层
        rx.box(
            position="fixed",
            top="0",
            left="0",
            right="0",
            bottom="0",
            background="rgba(0, 0, 0, 0.5)",
            display="flex",
            align_items="center",
            justify_content="center",
            z_index="1000",
        ),
        # 弹窗内容 - 使用flex居中
        rx.box(
            rx.heading(
                "欢迎使用 Ant Chat",
                font_size="24px",
                font_weight="600",
                color=COLORS["primary_blue"],
                margin_bottom="8px",
            ),
            rx.text(
                "请输入用户名以便开始聊天",
                font_size="14px",
                color=COLORS["text_light"],
                margin_bottom="24px",
            ),
            rx.form(
                rx.input(
                    placeholder="请输入用户名",
                    name="username",
                    max_length=20,
                    width="100%",
                    height="48px",
                    min_height="48px",
                    padding="12px 16px",
                    border_radius="8px",
                    border=f"1px solid {COLORS['border_light']}",
                    margin_bottom="16px",
                ),
                rx.button(
                    "进入聊天",
                    type="submit",
                    width="100%",
                    padding="12px",
                    background=f"linear-gradient(135deg, {COLORS['primary_blue']}, {COLORS['light_blue']})",
                    color="white",
                    border_radius="8px",
                    font_weight="500",
                    _hover={"transform": "translateY(-1px)", "box_shadow": "0 4px 12px rgba(0, 113, 188, 0.3)"},
                ),
                on_submit=State.init_user,
            ),
            background=COLORS["card_white"],
            border_radius="16px",
            padding="40px",
            box_shadow="0 10px 40px rgba(0, 0, 0, 0.2)",
            max_width="400px",
            width="90%",
            text_align="center",
            position="fixed",
            top="50%",
            left="50%",
            transform="translate(-50%, -50%)",
            z_index="1001",
        ),
    )


def render_conversation_item(conv: Dict) -> rx.Component:
    """单个对话项"""
    is_active = State.conversation_id == conv["id"]
    
    # 重命名模式
    if_state = rx.cond(
        State.editing_conversation_id == conv["id"],
        rx.box(
            rx.input(
                value=State.editing_name,
                on_change=State.set_editing_name,
                size="1",
                width="100%",
                margin_bottom="4px",
            ),
            rx.hstack(
                rx.button("保存", on_click=State.save_rename, color_scheme="blue"),
                rx.button("取消", on_click=State.cancel_rename, variant="outline"),
                spacing="2",
            ),
            padding="8px",
            border_radius="8px",
            bg="blue.50",
        ),
        rx.box(
            # 对话名称
            rx.hstack(
                rx.cond(
                    is_active,
                    rx.text("▶", color="blue.500", font_size="xs"),
                    rx.box(width="12px"),
                ),
                rx.text(
                    conv.get("conversation_name", "未命名"),
                    font_weight=rx.cond(is_active, "bold", "normal"),
                    color=rx.cond(is_active, "blue.600", "gray.700"),
                    flex=1,
                ),
                on_click=lambda: State.switch_conversation(conv["id"]),
                cursor="pointer",
            ),
            # 操作按钮
            rx.hstack(
                rx.button(
                    "✏️",
                    on_click=lambda: State.start_rename(conv["id"]),
                    size="1",
                    variant="ghost",
                    opacity=0.6,
                ),
                rx.button(
                    "🗑️",
                    on_click=lambda: State.delete_conversation(conv["id"]),
                    size="1",
                    variant="ghost",
                    color="red",
                    opacity=0.6,
                ),
                spacing="1",
            ),
            padding="8px 12px",
            border_radius="8px",
            bg=rx.cond(is_active, "blue.50", "transparent"),
            _hover={"bg": "gray.50"},
            cursor="pointer",
            transition="background 0.2s",
        ),
    )
    
    return if_state


def render_sidebar() -> rx.Component:
    """侧边栏"""
    return rx.box(
        # 标题
        rx.box(
            rx.text("对话历史", font_size="lg", font_weight="bold"),
            rx.text(f"用户: {State.username}", font_size="sm", color="gray.500"),
            padding="16px",
            border_bottom=f"1px solid {COLORS['border_light']}",
            background=COLORS["card_white"],
        ),
        # 新建对话按钮
        rx.button(
            "+ 新建对话",
            on_click=State.create_conversation,
            width="calc(100% - 32px)",
            margin="16px 16px 8px 16px",
            padding="12px",
            background=f"linear-gradient(135deg, {COLORS['primary_blue']}, {COLORS['light_blue']})",
            color="white",
            border_radius="8px",
            font_weight="500",
            _hover={"transform": "translateY(-1px)", "box_shadow": "0 4px 12px rgba(0, 113, 188, 0.3)"},
        ),
        # 流式输出开关
        rx.box(
            rx.hstack(
                rx.text("流式输出", font_size="sm", color=COLORS["text_dark"]),
                rx.switch(
                    is_checked=State.is_streaming,
                    on_change=State.set_is_streaming,
                    color_scheme="blue",
                ),
                justify_content="space-between",
                align_items="center",
                width="100%",
            ),
            padding="8px 16px",
        ),
        # 对话列表
        rx.box(
            rx.cond(
                State.conversations.length() > 0,
                rx.vstack(
                    rx.foreach(
                        State.conversations[:10],
                        render_conversation_item,
                    ),
                    spacing="2",
                ),
                rx.text("暂无对话记录", color="gray.500", font_size="sm", padding="16px"),
            ),
            padding="0 8px 16px",
        ),
        # 侧边栏容器
        position="fixed",
        left="0",
        top="0",
        width="280px",
        height="100vh",
        background=COLORS["card_white"],
        border_right=f"1px solid {COLORS['border_light']}",
        overflow_y="auto",
    )


def render_message(msg: Dict) -> rx.Component:
    """聊天消息"""
    is_user = msg["role"] == "user"

    return rx.box(
        rx.text(
            msg["content"],
            background=rx.cond(
                is_user,
                f"linear-gradient(135deg, {COLORS['primary_blue']}, {COLORS['light_blue']})",
                COLORS["card_white"],
            ),
            color=rx.cond(is_user, "white", COLORS["text_dark"]),
            border_radius=rx.cond(is_user, "18px 18px 4px 18px", "18px 18px 18px 4px"),
            padding="12px 16px",
            max_width="70%",
            box_shadow=rx.cond(is_user, "none", "0 1px 4px rgba(0, 0, 0, 0.08)"),
            white_space="pre-wrap",
            word_wrap="break-word",
        ),
        display="flex",
        justify_content=rx.cond(is_user, "flex-end", "flex-start"),
        width="100%",
        margin_bottom="12px",
    )


def render_pending_indicator() -> rx.Component:
    """Pending状态指示器 - AI正在输入"""
    return rx.box(
        rx.hstack(
            rx.text(
                State.pending_indicator,
                font_size="16px",
            ),
            rx.text(
                "AI正在思考...",
                color=COLORS["text_light"],
                font_size="14px",
            ),
            spacing="2",
            align_items="center",
        ),
        background=COLORS["card_white"],
        border_radius="18px 18px 18px 4px",
        padding="12px 16px",
        box_shadow="0 1px 4px rgba(0, 0, 0, 0.08)",
        display="flex",
        justify_content="flex-start",
        width="100%",
        margin_bottom="12px",
    )


def render_streaming_message() -> rx.Component:
    """流式输出中的消息（打字机效果）"""
    return rx.box(
        rx.text(
            State.streaming_content,
            background=COLORS["card_white"],
            color=COLORS["text_dark"],
            border_radius="18px 18px 18px 4px",
            padding="12px 16px",
            max_width="70%",
            box_shadow="0 1px 4px rgba(0, 0, 0, 0.08)",
            white_space="pre-wrap",
            word_wrap="break-word",
        ),
        display="flex",
        justify_content="flex-start",
        width="100%",
        margin_bottom="12px",
    )


def render_chat_area() -> rx.Component:
    """主聊天区域"""
    # 获取当前对话名称
    current_name = rx.cond(
        State.conversation_id != "",
        rx.cond(
            State.conversations.length() > 0,
            rx.foreach(
                State.conversations,
                lambda c: rx.cond(c["id"] == State.conversation_id, c["conversation_name"], ""),
            ),
            "新对话",
        ),
        "新对话",
    )

    return rx.box(
        # 顶部标题栏
        rx.box(
            rx.text(f"当前对话: ", font_size="lg", font_weight="bold"),
            rx.text(
                current_name,
                font_size="lg",
                font_weight="bold",
                color=COLORS["primary_blue"],
            ),
            rx.cond(
                State.is_pending,
                rx.text(
                    " ●",  # 显示一个点表示AI正在处理
                    color="orange",
                    font_size="lg",
                ),
            ),
            padding="16px",
            border_bottom=f"1px solid {COLORS['border_light']}",
            background=COLORS["card_white"],
            display="flex",
            align_items="center",
        ),
        # 消息列表
        rx.box(
            rx.vstack(
                rx.foreach(State.messages, render_message),
                # Pending状态时显示正在输入指示器
                rx.cond(
                    State.is_pending,
                    rx.cond(
                        State.streaming_content == "",
                        render_pending_indicator(),
                    ),
                ),
                # 流式输出时显示打字机效果的消息
                rx.cond(
                    State.streaming_content != "",
                    render_streaming_message(),
                ),
                spacing="0",
                align_items="stretch",
            ),
            flex="1",
            overflow_y="auto",
            padding="16px",
            min_height="calc(100vh - 140px)",
            background=COLORS["bg_gray"],
        ),
        # 输入区域
        rx.box(
            rx.form(
                rx.hstack(
                    rx.input(
                        value=State.input_message,
                        placeholder="请输入您的问题...",
                        on_change=State.set_input_message,
                        flex="1",
                        height="48px",
                        min_height="48px",
                        padding="12px 16px",
                        border_radius="8px",
                        border=f"1px solid {COLORS['border_light']}",
                        background=COLORS["card_white"],
                        disabled=State.is_pending,  # pending时禁用输入
                    ),
                    rx.button(
                        "发送",
                        type="submit",
                        padding="12px 24px",
                        background=rx.cond(
                            State.is_pending,
                            "gray.400",
                            f"linear-gradient(135deg, {COLORS['primary_blue']}, {COLORS['light_blue']})",
                        ),
                        color="white",
                        border_radius="8px",
                        font_weight="500",
                        _hover={"transform": "translateY(-1px)", "box_shadow": "0 4px 12px rgba(0, 113, 188, 0.3)"},
                    ),
                    spacing="2",
                    align_items="stretch",
                ),
                on_submit=State.send_message,
            ),
            padding="16px",
            border_top=f"1px solid {COLORS['border_light']}",
            background=COLORS["card_white"],
        ),
        # 布局容器
        display="flex",
        flex_direction="column",
        height="100vh",
        margin_left="280px",
    )


# ============ 主页面 ============

@rx.page(route="/", title="Ant Chat")
def index() -> rx.Component:
    """主页面"""
    return rx.box(
        rx.cond(
            ~State.user_initialized,
            render_username_modal(),
        ),
        rx.cond(
            State.user_initialized,
            rx.box(
                render_sidebar(),
                render_chat_area(),
            ),
        ),
    )


# ============ 应用配置 ============

app = rx.App(
    theme=rx.theme(
        appearance="light",
        has_background=True,
        radius="large",
        accent_color="blue",
    ),
)