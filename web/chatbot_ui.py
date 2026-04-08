"""
个人AI聊天工具 - Streamlit UI
调用 main.py 中定义的 /v1/chat 接口
支持对话历史管理
"""

import base64
import re
import time
from datetime import datetime

import requests
import streamlit as st
import uuid

from models.user import render_username_modal, get_current_user

# 配置
API_BASE_URL = "http://localhost:8012"

# 页面配置
st.set_page_config(
    page_title="Ant Chat",
    page_icon="💬",
    layout="centered"
)

# 渲染聊天界面标题（作为弹窗背景）
st.title("💬 Ant Chat")

# 用户初始化检查（模态弹窗）
if not render_username_modal():
    st.stop()


# ============ API 调用函数 ============

def get_conversations_api(user_id: str) -> list:
    """获取用户对话列表"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/v1/conversations",
            params={"user_id": user_id},
            timeout=10
        )
        response.raise_for_status()
        return response.json().get("conversations", [])
    except Exception as e:
        st.warning(f"获取对话列表失败，将使用缓存: {str(e)}")
        return []


def create_conversation_api(user_id: str, username: str, conversation_name: str = "") -> dict:
    """创建新对话"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/v1/conversations",
            json={
                "user_id": user_id,
                "username": username,
                "conversation_name": conversation_name
            },
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"创建对话失败: {str(e)}")
        return None


def delete_conversation_api(conversation_id: str) -> bool:
    """删除对话"""
    try:
        response = requests.delete(
            f"{API_BASE_URL}/v1/conversations/{conversation_id}",
            timeout=10
        )
        response.raise_for_status()
        return True
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            st.warning("对话不存在或已被删除")
        else:
            st.error(f"删除对话失败: {str(e)}")
        return False
    except Exception as e:
        st.error(f"删除对话失败: {str(e)}")
        return False


def rename_conversation_api(conversation_id: str, new_name: str) -> dict:
    """重命名对话"""
    try:
        response = requests.patch(
            f"{API_BASE_URL}/v1/conversations/{conversation_id}",
            json={"conversation_name": new_name},
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            st.warning("对话不存在")
        else:
            st.error(f"重命名对话失败: {str(e)}")
        return None
    except Exception as e:
        st.error(f"重命名对话失败: {str(e)}")
        return None


# ============ 初始化会话状态 ============

def init_conversation_state():
    """初始化对话状态"""
    current_user = get_current_user()

    if "conversation_id" not in st.session_state:
        st.session_state.conversation_id = str(uuid.uuid4())

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "is_stream" not in st.session_state:
        st.session_state.is_stream = True

    if "conversations" not in st.session_state:
        st.session_state.conversations = []

    if "editing_conversation_id" not in st.session_state:
        st.session_state.editing_conversation_id = None

    if "pending_message" not in st.session_state:
        st.session_state.pending_message = None

    # 加载对话列表
    if not st.session_state.conversations:
        st.session_state.conversations = get_conversations_api(current_user["user_id"])


init_conversation_state()


# ============ 对话管理函数 ============

def create_new_conversation():
    """创建新对话"""
    current_user = get_current_user()
    new_conv = create_conversation_api(
        user_id=current_user["user_id"],
        username=current_user["username"]
    )
    if new_conv:
        st.session_state.conversation_id = new_conv["id"]
        st.session_state.messages = []
        st.session_state.editing_conversation_id = None
        # 刷新对话列表以获取最新数据
        st.session_state.conversations = get_conversations_api(current_user["user_id"])
        st.rerun()


def switch_conversation(conversation_id: str):
    """切换对话"""
    if conversation_id != st.session_state.conversation_id:
        st.session_state.conversation_id = conversation_id
        st.session_state.messages = []
        st.session_state.editing_conversation_id = None
        st.rerun()


def delete_conversation_handler(conversation_id: str):
    """删除对话处理器"""
    if delete_conversation_api(conversation_id):
        st.session_state.conversations = [
            c for c in st.session_state.conversations if c["id"] != conversation_id
        ]
        # 如果删除的是当前对话，切换到其他对话
        if conversation_id == st.session_state.conversation_id:
            if st.session_state.conversations:
                st.session_state.conversation_id = st.session_state.conversations[0]["id"]
                st.session_state.messages = []
            else:
                # 没有对话了，创建新对话
                create_new_conversation()
        st.rerun()


def save_conversation_name(conversation_id: str, new_name: str):
    """保存对话名称"""
    if new_name.strip():
        result = rename_conversation_api(conversation_id, new_name.strip())
        if result:
            for i, conv in enumerate(st.session_state.conversations):
                if conv["id"] == conversation_id:
                    st.session_state.conversations[i]["conversation_name"] = new_name.strip()
                    break
    st.session_state.editing_conversation_id = None
    # 刷新对话列表以获取最新数据
    current_user = get_current_user()
    st.session_state.conversations = get_conversations_api(current_user["user_id"])
    st.rerun()


def _generate_conversation_name(first_question: str, max_length: int = 20) -> str:
    """
    根据用户第一条问题生成对话名称（归纳至指定字数以内）
    与后端 generate_conversation_name 保持相同逻辑
    """
    # 去除多余空白字符
    question = ' '.join(first_question.split())
    # 如果已经小于等于最大长度，直接返回
    if len(question) <= max_length:
        return question
    # 按字符截断，确保不截断单词
    truncated = question[:max_length]
    if truncated[-1] not in ' \t\n.,!?;:':
        last_space = truncated.rfind(' ')
        if last_space > 0:
            truncated = truncated[:last_space]
    return truncated.strip()


# ============ 聊天功能函数 ============

def format_response(response: str) -> str:
    """格式化响应文本"""
    paragraphs = re.split(r'\n{2,}', response)
    formatted_paragraphs = []
    for para in paragraphs:
        if '```' in para:
            parts = para.split('```')
            for i, part in enumerate(parts):
                if i % 2 == 1:
                    parts[i] = f"\n```\n{part.strip()}\n```\n"
            para = ''.join(parts)
        else:
            para = para.replace('. ', '.\n')
        formatted_paragraphs.append(para.strip())
    return '\n\n'.join(formatted_paragraphs)


def call_chat_api(messages: list, is_stream: bool) -> dict:
    """调用聊天API"""
    current_user = get_current_user()
    payload = {
        "messages": messages,
        "is_stream": is_stream,
        "user_id": current_user["user_id"],
        "conversation_id": st.session_state.conversation_id
    }

    try:
        response = requests.post(
            f"{API_BASE_URL}/v1/chat",
            json=payload,
            stream=is_stream,
            timeout=120
        )
        response.raise_for_status()
        return response
    except requests.exceptions.ConnectionError:
        st.error("无法连接到服务器，请确保 FastAPI 服务已在端口 8012 上启动")
        return None
    except requests.exceptions.Timeout:
        st.error("请求超时，请重试")
        return None
    except Exception as e:
        st.error(f"请求失败: {str(e)}")
        return None


def handle_stream_response(response):
    """处理流式响应 - 打字机效果"""
    message_placeholder = st.empty()
    full_response = ""

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

            for char in decoded:
                full_response += char
                message_placeholder.markdown(full_response + "▌")
                time.sleep(0.01)

    message_placeholder.markdown(full_response)
    return full_response


def handle_non_stream_response(response):
    """处理非流式响应"""
    result = response.json()
    return result.get("content", "")


# ============ 侧边栏 - 对话管理 ============

with st.sidebar:
    st.title("对话历史")

    current_user = get_current_user()
    st.caption(f"用户: {current_user['username']}")

    # 创建新对话按钮
    if st.button("➕ 新建对话", use_container_width=True):
        create_new_conversation()

    # 对话列表
    st.markdown("**对话列表**")

    if not st.session_state.conversations:
        st.caption("暂无对话记录")
    else:
        for conv in st.session_state.conversations[:10]:  # 最多显示10条
            conv_id = conv["id"]
            conv_name = conv.get("conversation_name") or "未命名"
            is_active = conv_id == st.session_state.conversation_id

            # 显示对话项：指示符 + 名称 + 操作按钮
            col1, col2, col3, col4 = st.columns([1, 4, 1, 1])
            with col1:
                if is_active:
                    st.markdown("**▶**")
            with col2:
                if is_active:
                    st.markdown(f"**{conv_name}**")
                else:
                    if st.button(conv_name, key=f"conv_{conv_id}"):
                        switch_conversation(conv_id)
            with col3:
                if st.button("✏️", key=f"rename_{conv_id}", help="重命名"):
                    st.session_state.editing_conversation_id = conv_id
                    st.rerun()
            with col4:
                if st.button("🗑️", key=f"del_{conv_id}", help="删除"):
                    delete_conversation_handler(conv_id)


# ============ 主聊天区域 ============

# 显示当前对话名称
current_conv = next(
    (c for c in st.session_state.conversations if c["id"] == st.session_state.conversation_id),
    None
)
current_conv_name = current_conv.get("conversation_name") if current_conv else ""
if current_conv_name:
    st.markdown(f"**当前对话: {current_conv_name}**")
else:
    st.markdown("**当前对话: 未命名**")

# 显示聊天历史
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ============ 处理待发送的消息 ============
# 用于在对话创建后，第二次运行时发送消息
if st.session_state.get("pending_message"):
    pending = st.session_state.pending_message
    st.session_state.pending_message = None  # 清除待处理状态

    # 发送消息
    st.session_state.messages.append({"role": "user", "content": pending})
    with st.chat_message("user"):
        st.markdown(pending)

    with st.chat_message("assistant"):
        with st.spinner("思考中..."):
            response = call_chat_api(
                messages=st.session_state.messages,
                is_stream=st.session_state.is_stream
            )

            if response is None:
                st.session_state.messages.pop()
            elif st.session_state.is_stream:
                assistant_response = handle_stream_response(response)
                st.session_state.messages.append({"role": "assistant", "content": assistant_response})
            else:
                assistant_response = handle_non_stream_response(response)
                st.markdown(format_response(assistant_response))
                st.session_state.messages.append({"role": "assistant", "content": assistant_response})

    # 刷新对话列表以更新自动生成的名称
    try:
        st.session_state.conversations = get_conversations_api(current_user["user_id"])
    except Exception:
        pass


# ============ 用户输入 ============
if prompt := st.chat_input("请输入您的问题..."):
    # 检查当前对话是否存在于列表中
    current_conv_exists = any(
        c["id"] == st.session_state.conversation_id
        for c in st.session_state.conversations
    )

    # 如果对话不存在，先创建对话记录
    if not current_conv_exists:
        # 立即生成对话名称
        auto_name = _generate_conversation_name(prompt)
        new_conv = create_conversation_api(
            user_id=current_user["user_id"],
            username=current_user["username"],
            conversation_name=auto_name
        )
        if new_conv:
            st.session_state.conversations.insert(0, new_conv)
            # 设置待发送消息，在下次运行时发送
            st.session_state.pending_message = prompt
            st.rerun()
        # 如果创建失败，静默继续（LangGraph 会话独立管理）
    else:
        # 对话已存在，直接发送消息
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("思考中..."):
                response = call_chat_api(
                    messages=st.session_state.messages,
                    is_stream=st.session_state.is_stream
                )

                if response is None:
                    st.session_state.messages.pop()
                elif st.session_state.is_stream:
                    assistant_response = handle_stream_response(response)
                    st.session_state.messages.append({"role": "assistant", "content": assistant_response})
                else:
                    assistant_response = handle_non_stream_response(response)
                    st.markdown(format_response(assistant_response))
                    st.session_state.messages.append({"role": "assistant", "content": assistant_response})

        # 刷新对话列表
        try:
            st.session_state.conversations = get_conversations_api(current_user["user_id"])
        except Exception:
            pass
        pass  # 静默失败，使用缓存的对话列表
