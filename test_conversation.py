"""
对话历史模块单元测试
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

# 设置环境变量（测试用）
os.environ.setdefault("DB_HOST", "127.0.0.1")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_NAME", "test_ant_chat")
os.environ.setdefault("DB_USER", "postgres")
os.environ.setdefault("DB_PASSWORD", "postgres")


class TestGenerateConversationName:
    """测试 generate_conversation_name 函数"""

    def test_short_question_unchanged(self):
        """测试：问题短于最大长度，直接返回"""
        from models.conversation import generate_conversation_name

        question = "你好"
        result = generate_conversation_name(question, max_length=20)
        assert result == "你好"

    def test_exact_max_length(self):
        """测试：问题等于最大长度，直接返回"""
        from models.conversation import generate_conversation_name

        question = "a" * 20
        result = generate_conversation_name(question, max_length=20)
        assert result == "a" * 20

    def test_long_question_truncated(self):
        """测试：问题长于最大长度，截断到最大长度"""
        from models.conversation import generate_conversation_name

        question = "这是一个非常长的问题，需要被截断到指定长度"
        result = generate_conversation_name(question, max_length=10)
        assert len(result) <= 10

    def test_long_question_preserves_word(self):
        """测试：长问题在单词边界截断"""
        from models.conversation import generate_conversation_name

        question = "如何用Python写一个快速排序算法"
        result = generate_conversation_name(question, max_length=15)
        assert len(result) <= 15
        # 验证不在单词中间截断
        assert not result.endswith("排序算")

    def test_question_with_extra_spaces(self):
        """测试：问题含多余空格，被合并"""
        from models.conversation import generate_conversation_name

        question = "如何   用Python  写一个   快速排序"
        result = generate_conversation_name(question, max_length=20)
        assert "  " not in result

    def test_default_max_length(self):
        """测试：默认最大长度为20"""
        from models.conversation import generate_conversation_name

        question = "a" * 100
        result = generate_conversation_name(question)
        assert len(result) == 20


class TestConversationModels:
    """测试对话模型"""

    def test_conversation_create_model(self):
        """测试 ConversationCreate 模型"""
        from models.conversation import ConversationCreate

        conv = ConversationCreate(
            user_id="user_123",
            username="张三",
            conversation_name="测试对话"
        )
        assert conv.user_id == "user_123"
        assert conv.username == "张三"
        assert conv.conversation_name == "测试对话"

    def test_conversation_create_default_name(self):
        """测试 ConversationCreate 默认对话名称为空"""
        from models.conversation import ConversationCreate

        conv = ConversationCreate(
            user_id="user_123",
            username="张三"
        )
        assert conv.conversation_name == ""

    def test_conversation_update_model(self):
        """测试 ConversationUpdate 模型"""
        from models.conversation import ConversationUpdate

        update = ConversationUpdate(conversation_name="新名称")
        assert update.conversation_name == "新名称"

    def test_conversation_response_model(self):
        """测试 ConversationResponse 模型"""
        from models.conversation import ConversationResponse

        now = datetime.now()
        resp = ConversationResponse(
            id="uuid-123",
            user_id="user_123",
            username="张三",
            conversation_name="测试对话",
            is_deleted=False,
            created_at=now,
            updated_at=now
        )
        assert resp.id == "uuid-123"
        assert resp.is_deleted is False

    def test_conversation_list_response_model(self):
        """测试 ConversationListResponse 模型"""
        from models.conversation import ConversationListResponse, ConversationResponse

        now = datetime.now()
        conv1 = ConversationResponse(
            id="uuid-1",
            user_id="user_123",
            username="张三",
            conversation_name="对话1",
            is_deleted=False,
            created_at=now,
            updated_at=now
        )
        conv2 = ConversationResponse(
            id="uuid-2",
            user_id="user_123",
            username="张三",
            conversation_name="对话2",
            is_deleted=False,
            created_at=now,
            updated_at=now
        )

        list_resp = ConversationListResponse(conversations=[conv1, conv2])
        assert len(list_resp.conversations) == 2


class TestConversationOperations:
    """测试对话数据库操作（使用 mock）"""

    @patch('models.conversation.get_db_connection')
    def test_create_conversation(self, mock_get_conn):
        """测试创建对话"""
        from models.conversation import create_conversation, ConversationCreate, ConversationResponse

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)

        now = datetime.now()
        mock_cursor.fetchone.return_value = {
            "id": "uuid-new",
            "user_id": "user_123",
            "username": "张三",
            "conversation_name": "新对话",
            "is_deleted": False,
            "created_at": now,
            "updated_at": now
        }

        conv = ConversationCreate(
            user_id="user_123",
            username="张三",
            conversation_name="新对话"
        )
        result = create_conversation(conv)

        assert result.id == "uuid-new"
        assert result.conversation_name == "新对话"
        mock_cursor.execute.assert_called_once()

    @patch('models.conversation.get_db_connection')
    def test_get_conversation_by_id_found(self, mock_get_conn):
        """测试根据 ID 获取对话（存在）"""
        from models.conversation import get_conversation_by_id

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)

        now = datetime.now()
        mock_cursor.fetchone.return_value = {
            "id": "uuid-123",
            "user_id": "user_123",
            "username": "张三",
            "conversation_name": "测试对话",
            "is_deleted": False,
            "created_at": now,
            "updated_at": now
        }

        result = get_conversation_by_id("uuid-123")

        assert result is not None
        assert result.id == "uuid-123"

    @patch('models.conversation.get_db_connection')
    def test_get_conversation_by_id_not_found(self, mock_get_conn):
        """测试根据 ID 获取对话（不存在）"""
        from models.conversation import get_conversation_by_id

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)

        mock_cursor.fetchone.return_value = None

        result = get_conversation_by_id("non-existent-uuid")

        assert result is None

    @patch('models.conversation.get_db_connection')
    def test_get_conversations_by_user_id(self, mock_get_conn):
        """测试获取用户的所有对话"""
        from models.conversation import get_conversations_by_user_id

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)

        now = datetime.now()
        mock_cursor.fetchall.return_value = [
            {
                "id": "uuid-1",
                "user_id": "user_123",
                "username": "张三",
                "conversation_name": "对话1",
                "is_deleted": False,
                "created_at": now,
                "updated_at": now
            },
            {
                "id": "uuid-2",
                "user_id": "user_123",
                "username": "张三",
                "conversation_name": "对话2",
                "is_deleted": False,
                "created_at": now,
                "updated_at": now
            }
        ]

        result = get_conversations_by_user_id("user_123")

        assert len(result) == 2
        assert result[0].id == "uuid-1"
        assert result[1].id == "uuid-2"

    @patch('models.conversation.get_db_connection')
    def test_update_conversation_name_success(self, mock_get_conn):
        """测试更新对话名称（成功）"""
        from models.conversation import update_conversation_name

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)

        now = datetime.now()
        mock_cursor.fetchone.return_value = {
            "id": "uuid-123",
            "user_id": "user_123",
            "username": "张三",
            "conversation_name": "新名称",
            "is_deleted": False,
            "created_at": now,
            "updated_at": now
        }

        result = update_conversation_name("uuid-123", "新名称")

        assert result is not None
        assert result.conversation_name == "新名称"

    @patch('models.conversation.get_db_connection')
    def test_update_conversation_name_not_found(self, mock_get_conn):
        """测试更新对话名称（不存在）"""
        from models.conversation import update_conversation_name

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)

        mock_cursor.fetchone.return_value = None

        result = update_conversation_name("non-existent", "新名称")

        assert result is None

    @patch('models.conversation.get_db_connection')
    def test_delete_conversation_success(self, mock_get_conn):
        """测试删除对话（成功）"""
        from models.conversation import delete_conversation

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)

        mock_cursor.fetchone.return_value = {"id": "uuid-123"}

        result = delete_conversation("uuid-123")

        assert result is True

    @patch('models.conversation.get_db_connection')
    def test_delete_conversation_not_found(self, mock_get_conn):
        """测试删除对话（不存在）"""
        from models.conversation import delete_conversation

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)

        mock_cursor.fetchone.return_value = None

        result = delete_conversation("non-existent")

        assert result is False

    @patch('models.conversation.get_db_connection')
    def test_get_conversations_by_user_id_empty(self, mock_get_conn):
        """测试获取用户的对话列表为空"""
        from models.conversation import get_conversations_by_user_id

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)

        mock_cursor.fetchall.return_value = []

        result = get_conversations_by_user_id("user_with_no_conversations")

        assert result == []

    @patch('models.conversation.get_db_connection')
    def test_get_conversations_by_user_id_database_error(self, mock_get_conn):
        """测试获取对话列表时数据库错误（应抛出异常）"""
        from models.conversation import get_conversations_by_user_id

        mock_get_conn.side_effect = Exception("Database connection failed")

        with pytest.raises(Exception) as exc_info:
            get_conversations_by_user_id("user_123")

        assert "Database connection failed" in str(exc_info.value)

    @patch('models.conversation.get_db_connection')
    def test_create_conversation_database_error(self, mock_get_conn):
        """测试创建对话时数据库错误（应抛出异常）"""
        from models.conversation import create_conversation, ConversationCreate

        mock_get_conn.side_effect = Exception("Database connection failed")
        conv = ConversationCreate(
            user_id="user_123",
            username="张三",
            conversation_name="测试"
        )

        with pytest.raises(Exception) as exc_info:
            create_conversation(conv)

        assert "Database connection failed" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
