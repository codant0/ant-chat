import logging
import time
import uuid
from typing import List

from anthropic import Anthropic
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, MessagesState
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PORT = 8012
graph = None
model = "MiniMax-M2.7"

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    is_stream: bool = False
    user_id: str
    conversation_id: str

class ChatResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"ant-chat-{uuid.uuid4().hex}")
    object: str = "ant-chat"
    created: int = Field(default_factory=lambda: int(time.time()))

def chatbot(state: MessagesState, client: Anthropic) -> dict:
    return {"messages": [client.messages.create(
        model=model,
        max_tokens=1024,
        # TODO 验证anthropic API当前调用正确
        messages=[{"role": "user", "content": "Hello!"}]
    )]}

def create_graph(agent: Anthropic) -> StateGraph:
    try:
        graph = StateGraph(MessagesState)

        graph.add_node("chatbot", chatbot)
        graph.set_entry_point("chatbot")
        graph.set_finish_point("chatbot")

        checkpointer = MemorySaver()
        return graph.compile(checkpointer=checkpointer)

    except Exception as e:
        logger.error(f"Failed to create graph: {str(e)}")
        raise

# 将构建的graph可视化保存为 PNG 文件
def save_graph_visualization(graph: StateGraph, filename: str = "graph.png") -> None:
    try:
        with open(filename, "wb") as f:
            f.write(graph.get_graph().draw_mermaid_png())
        logger.info(f"Graph visualization saved as {filename}")
    except IOError as e:
        logger.info(f"Warning: Failed to save graph visualization: {str(e)}")

# 格式化响应，对输入的文本进行段落分隔、添加适当的换行符，以及在代码块中增加标记，以便生成更具可读性的输出
def format_response(response):
    # 使用正则表达式 \n{2, }将输入的response按照两个或更多的连续换行符进行分割。这样可以将文本分割成多个段落，每个段落由连续的非空行组成
    paragraphs = re.split(r'\n{2,}', response)
    # 空列表，用于存储格式化后的段落
    formatted_paragraphs = []
    # 遍历每个段落进行处理
    for para in paragraphs:
        # 检查段落中是否包含代码块标记
        if '```' in para:
            # 将段落按照```分割成多个部分，代码块和普通文本交替出现
            parts = para.split('```')
            for i, part in enumerate(parts):
                # 检查当前部分的索引是否为奇数，奇数部分代表代码块
                if i % 2 == 1:  # 这是代码块
                    # 将代码块部分用换行符和```包围，并去除多余的空白字符
                    parts[i] = f"\n```\n{part.strip()}\n```\n"
            # 将分割后的部分重新组合成一个字符串
            para = ''.join(parts)
        else:
            # 否则，将句子中的句点后面的空格替换为换行符，以便句子之间有明确的分隔
            para = para.replace('. ', '.\n')
        # 将格式化后的段落添加到formatted_paragraphs列表
        # strip()方法用于移除字符串开头和结尾的空白字符（包括空格、制表符 \t、换行符 \n等）
        formatted_paragraphs.append(para.strip())
    # 将所有格式化后的段落用两个换行符连接起来，以形成一个具有清晰段落分隔的文本
    return '\n\n'.join(formatted_paragraphs)

