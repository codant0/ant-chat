"""
个人AI聊天工具 - Streamlit UI
调用 main.py 中定义的 /v1/chat 接口
"""

import requests
import streamlit as st
import uuid
from datetime import datetime

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

# 初始化会话状态
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

if "is_stream" not in st.session_state:
    st.session_state.is_stream = True


def format_response(response: str) -> str:
    """格式化响应文本"""
    import re
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
    import base64
    import time
    message_placeholder = st.empty()
    full_response = ""

    for line in response.iter_lines(decode_unicode=True):
        line = line.strip()
        if line.startswith("data: "):
            data = line[6:]
            if data == "[DONE]":
                break
            try:
                # 解码base64编码的文本
                decoded = base64.b64decode(data.encode('ascii')).decode('utf-8')
            except Exception:
                decoded = data

            # 逐字显示，形成打字机效果
            for char in decoded:
                full_response += char
                message_placeholder.markdown(full_response + "▌")
                time.sleep(0.01)  # 打字速度，可调整

    message_placeholder.markdown(full_response)
    return full_response


def handle_non_stream_response(response):
    """处理非流式响应"""
    result = response.json()
    return result.get("content", "")


# 侧边栏设置
with st.sidebar:
    st.title("设置")

    current_user = get_current_user()
    st.markdown(f"**用户**: {current_user['username']}")

    if st.button("开启新对话"):
        st.session_state.conversation_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()

    st.session_state.is_stream = st.toggle("流式输出", value=st.session_state.is_stream)

    st.divider()
    st.markdown(f"**会话ID**")
    st.caption(st.session_state.conversation_id[:8] + "...")

    if st.button("清空历史消息"):
        st.session_state.messages = []
        st.rerun()

# 显示聊天历史
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 用户输入
if prompt := st.chat_input("请输入您的问题..."):
    # 添加用户消息
    st.session_state.messages.append({
        "role": "user",
        "content": prompt
    })

    with st.chat_message("user"):
        st.markdown(prompt)

    # 调用API
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
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": assistant_response
                })
            else:
                assistant_response = handle_non_stream_response(response)
                st.markdown(format_response(assistant_response))
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": assistant_response
                })
