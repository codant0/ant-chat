"""
对话历史模块
支持对话的创建、查询、逻辑删除和名称更新
"""

import logging
import os
import uuid
from datetime import datetime
from typing import List, Optional

import psycopg
from psycopg.rows import dict_row
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

logger = logging.getLogger(__name__)


class ConversationBase(BaseModel):
    """对话基础模型"""
    user_id: str
    username: str
    conversation_name: str = ""


class ConversationCreate(ConversationBase):
    """创建对话请求模型"""
    pass


class ConversationUpdate(BaseModel):
    """更新对话请求模型"""
    conversation_name: str


class ConversationResponse(ConversationBase):
    """对话响应模型"""
    id: str
    is_deleted: bool = False
    created_at: datetime
    updated_at: datetime


class ConversationListResponse(BaseModel):
    """对话列表响应模型"""
    conversations: List[ConversationResponse]


def get_db_connection():
    """获取数据库连接"""
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT")
    dbname = os.getenv("DB_NAME")
    db_uri = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
    return psycopg.connect(db_uri, row_factory=dict_row)


def init_conversations_table():
    """初始化 conversations 表"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS conversations (
                        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        user_id         VARCHAR(64) NOT NULL,
                        username        VARCHAR(128) NOT NULL,
                        conversation_name VARCHAR(64) NOT NULL DEFAULT '',
                        is_deleted      BOOLEAN DEFAULT FALSE,
                        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_conversations_user_id
                    ON conversations(user_id);
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_conversations_created_at
                    ON conversations(created_at DESC);
                """)
            conn.commit()
        logger.info("Conversations table initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize conversations table: {str(e)}", exc_info=True)
        raise


def create_conversation(conversation: ConversationCreate) -> ConversationResponse:
    """
    创建新对话

    Args:
        conversation: 对话创建请求

    Returns:
        创建的对话响应
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO conversations (user_id, username, conversation_name)
                    VALUES (%s, %s, %s)
                    RETURNING id, user_id, username, conversation_name, is_deleted, created_at, updated_at
                """, (conversation.user_id, conversation.username, conversation.conversation_name))
                row = cur.fetchone()
            conn.commit()

        if row is None:
            logger.error("Failed to create conversation: fetchone returned None")
            raise Exception("Failed to create conversation: fetchone returned None")

        # 转换 UUID 为字符串
        row['id'] = str(row['id'])

        logger.info(f"Created conversation: {row['id']} for user: {conversation.user_id}")
        return ConversationResponse(**row)
    except Exception as e:
        logger.error(f"Failed to create conversation: {str(e)}", exc_info=True)
        raise


def get_conversation_by_id(conversation_id: str) -> Optional[ConversationResponse]:
    """
    根据 ID 获取对话

    Args:
        conversation_id: 对话 ID

    Returns:
        对话响应或 None
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, user_id, username, conversation_name, is_deleted, created_at, updated_at
                    FROM conversations
                    WHERE id = %s AND is_deleted = FALSE
                """, (conversation_id,))
                row = cur.fetchone()

        if row:
            row['id'] = str(row['id'])
            return ConversationResponse(**row)
        return None
    except Exception as e:
        logger.error(f"Failed to get conversation {conversation_id}: {str(e)}", exc_info=True)
        raise


def get_conversations_by_user_id(user_id: str) -> List[ConversationResponse]:
    """
    获取用户的所有对话列表（按创建时间倒序）

    Args:
        user_id: 用户 ID

    Returns:
        对话列表
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, user_id, username, conversation_name, is_deleted, created_at, updated_at
                    FROM conversations
                    WHERE user_id = %s AND is_deleted = FALSE
                    ORDER BY created_at DESC
                """, (user_id,))
                rows = cur.fetchall()

        conversations = []
        for row in rows:
            row['id'] = str(row['id'])
            conversations.append(ConversationResponse(**row))
        logger.info(f"Retrieved {len(conversations)} conversations for user: {user_id}")
        return conversations
    except Exception as e:
        logger.error(f"Failed to get conversations for user {user_id}: {str(e)}", exc_info=True)
        raise


def update_conversation_name(conversation_id: str, conversation_name: str) -> Optional[ConversationResponse]:
    """
    更新对话名称

    Args:
        conversation_id: 对话 ID
        conversation_name: 新的对话名称

    Returns:
        更新后的对话响应或 None
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE conversations
                    SET conversation_name = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND is_deleted = FALSE
                    RETURNING id, user_id, username, conversation_name, is_deleted, created_at, updated_at
                """, (conversation_name, conversation_id))
                row = cur.fetchone()
            conn.commit()

        if row:
            row['id'] = str(row['id'])
            logger.info(f"Updated conversation name: {conversation_id} -> {conversation_name}")
            return ConversationResponse(**row)
        return None
    except Exception as e:
        logger.error(f"Failed to update conversation {conversation_id}: {str(e)}", exc_info=True)
        raise


def delete_conversation(conversation_id: str) -> bool:
    """
    逻辑删除对话

    Args:
        conversation_id: 对话 ID

    Returns:
        是否删除成功
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE conversations
                    SET is_deleted = TRUE, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND is_deleted = FALSE
                    RETURNING id
                """, (conversation_id,))
                row = cur.fetchone()
            conn.commit()

        if row:
            logger.info(f"Deleted conversation: {conversation_id}")
            return True
        logger.warning(f"Conversation not found or already deleted: {conversation_id}")
        return False
    except Exception as e:
        logger.error(f"Failed to delete conversation {conversation_id}: {str(e)}", exc_info=True)
        raise


def generate_conversation_name(first_question: str, max_length: int = 20) -> str:
    """
    根据用户第一条问题自动生成对话名称（归纳至指定字数以内）

    Args:
        first_question: 用户的第一条问题
        max_length: 最大长度

    Returns:
        归纳后的对话名称
    """
    # 去除多余空白字符
    question = ' '.join(first_question.split())

    # 如果已经小于等于最大长度，直接返回
    if len(question) <= max_length:
        return question

    # 按字符截断，确保不截断单词
    truncated = question[:max_length]
    # 如果截断位置不是空格，往前找到最后一个完整单词
    if truncated[-1] not in ' \t\n.,!?;:':
        last_space = truncated.rfind(' ')
        if last_space > 0:
            truncated = truncated[:last_space]

    # 去除尾部空白
    return truncated.strip()
