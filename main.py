import logging
import re
import time
import uuid
from contextlib import asynccontextmanager
from typing import List

import uvicorn
from anthropic import Anthropic
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from langgraph.checkpoint.memory import MemorySaver, InMemorySaver
from langgraph.graph import StateGraph, MessagesState
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel, Field

from models.llms import init_llm

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PORT = 8012
graph : CompiledStateGraph
LLM_TYPE = "minimax"
MODEL = "MiniMax-M2.7"
# 无用户系统，固定user_id
USER_ID = "user_1"

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
    content: str

def chatbot(state: MessagesState, client: Anthropic) -> dict:
    return {"messages": [client.messages.create(
        model=MODEL,
        max_tokens=1024,
        # TODO 验证anthropic API当前调用正确
        messages=state["messages"]
    )]}

def create_graph(client: Anthropic) -> StateGraph:
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

@asynccontextmanager
async def lifespan(app: FastAPI):
    global graph

    try:
        logger.info("Initing llm......")
        client = init_llm(llm_type=LLM_TYPE)
        graph = create_graph(client)
        save_graph_visualization(graph)
        logger.info("Success to init llm")
    except Exception as e:
        logger.error(f"Failed to init llm: {str(e)}")
        raise

    # yield 关键字将控制权交还给FastAPI框架，使应用开始运行
    yield
    # 关闭时执行
    logger.info("Closing.........")

app = FastAPI(lifespan=lifespan)

@app.post("/v1/chat")
def chat(request: ChatRequest):
    global graph
    # 初始化未完成
    if not graph:
        logger.error("Init program not finished.")
        raise HTTPException(status_code=400, detail="Init program not finished")

    try:
        # 获取本次提问文本内容
        user_input = request.messages[-1].content

        # 设置用户线程信息
        config = {"configurable": {
            "thread_id": USER_ID + request.conversation_id
        }}

        # 设置短期记忆
        checkpointer = InMemorySaver()

        # 流式输出
        if request.is_stream:
            def generate_stream():
                for chunk in graph.stream(input=user_input, checkpointer=checkpointer, config=config, stream_mode="messages"):
                    # 处理messages mode 的流式输出块
                    yield f"data: {chunk.content}"
                # 流式输出结束信号
                yield "data: __END_SIGNAL__"
            # 返回fastapi.responses中StreamingResponse对象
            return StreamingResponse(generate_stream(), media_type="text/event-stream")

        # 非流式输出
        result = graph.invoke(input=user_input, checkpointer=checkpointer, config=config)
        response = ChatResponse(
            content=format_response(result),
        )
        return JSONResponse(response)
    except Exception as e:
        raise

if __name__ == "__main__":
    logger.info(f"在端口 {PORT} 上启动服务器")
    # uvicorn是一个用于运行ASGI应用的轻量级、超快速的ASGI服务器实现
    # 用于部署基于FastAPI框架的异步PythonWeb应用程序
    uvicorn.run(app, host="0.0.0.0", port=PORT)