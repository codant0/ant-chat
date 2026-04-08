"""
极简用户模块
通过用户名标识用户，相同用户名的用户被认为是同一用户
"""

import streamlit as st
import hashlib


def get_user_id(username: str) -> str:
    """
    根据用户名生成用户ID
    相同用户名生成相同的用户ID
    """
    return hashlib.md5(username.encode()).hexdigest()[:12]


def init_user_state():
    """初始化用户状态"""
    if "user_initialized" not in st.session_state:
        st.session_state.user_initialized = False
        st.session_state.username = ""
        st.session_state.user_id = ""


def render_username_modal() -> bool:
    """
    渲染用户名输入弹窗
    使用自定义 HTML/CSS 实现居中弹窗
    """
    init_user_state()

    # 已初始化
    if st.session_state.user_initialized:
        return True

    # CSS - 隐藏默认页面元素
    st.markdown("""
    <style>
    #MainMenu {visibility: hidden !important;}
    header {visibility: hidden !important;}
    </style>
    """, unsafe_allow_html=True)

    # 居中布局
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("<h2 style='text-align: center;'>欢迎使用 Ant Chat</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #666;'>请输入用户名以便开始聊天</p>", unsafe_allow_html=True)

        with st.form("username_form", clear_on_submit=True):
            username = st.text_input(
                "用户名",
                placeholder="请输入用户名",
                max_chars=20,
                label_visibility="collapsed"
            )
            submitted = st.form_submit_button("进入聊天", use_container_width=True)

        if submitted:
            if username:
                st.session_state.username = username
                st.session_state.user_id = get_user_id(username)
                st.session_state.user_initialized = True
                st.rerun()
            else:
                st.error("请输入用户名")
                # 不 stop，让用户可以重试

    # 只有未提交时才 stop
    st.stop()


def get_current_user() -> dict:
    """
    获取当前用户信息
    """
    return {
        "username": st.session_state.get("username", ""),
        "user_id": st.session_state.get("user_id", "")
    }