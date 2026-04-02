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
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from pydantic import BaseModel, Field

from models.llms import init_llm

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PORT = 8012
graph : CompiledStateGraph
client : Anthropic
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

def chatbot(state: MessagesState) -> dict:
    global client
    # 将 LangChain 消息对象转换为 Anthropic API 格式的字典
    messages = []
    for msg in state["messages"]:
        if hasattr(msg, "type"):
            # LangChain 消息对象
            role = "user" if msg.type == "human" else ("assistant" if msg.type == "ai" else msg.type)
            content = msg.content if hasattr(msg, "content") else str(msg)
        else:
            # 已经是字典
            role = msg.get("role")
            content = msg.get("content")
        messages.append({"role": role, "content": content})

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=messages
    )
    # 从响应中提取文本内容
    response_text = ""
    for block in response.content:
        if hasattr(block, 'text') and block.text:
            response_text += block.text
        elif hasattr(block, 'type') and block.type == 'text':
            response_text += block.text
    # 将 Anthropic 响应转换为 LangChain AIMessage
    return {"messages": [AIMessage(content=response_text)]}

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
    global graph, client

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
        # 转换消息格式
        input_messages = []
        for msg in request.messages:
            if msg.role == "user":
                input_messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                input_messages.append(AIMessage(content=msg.content))
            elif msg.role == "system":
                input_messages.append(SystemMessage(content=msg.content))

        # 设置用户线程信息
        config = {"configurable": {
            "thread_id": USER_ID + request.conversation_id
        }}

        # 设置短期记忆
        checkpointer = InMemorySaver()

        # 流式输出
        if request.is_stream:
            def generate_stream():
                global client
                # 将 LangChain 消息对象转换为 Anthropic API 格式的字典
                api_messages = []
                for msg in input_messages:
                    if hasattr(msg, "type"):
                        role = "user" if msg.type == "human" else ("assistant" if msg.type == "ai" else msg.type)
                        content = msg.content if hasattr(msg, "content") else str(msg)
                    else:
                        role = msg.get("role")
                        content = msg.get("content")
                    api_messages.append({"role": role, "content": content})

                # 使用 LLM 的流式模式
                with client.messages.stream(
                    model=MODEL,
                    max_tokens=1024,
                    messages=api_messages
                ) as stream:
                    for event in stream:
                        if hasattr(event, 'type'):
                            if event.type == "content_block_delta":
                                if hasattr(event, 'delta') and hasattr(event.delta, 'text'):
                                    # 对文本进行base64编码，避免data:冲突
                                    import base64
                                    encoded = base64.b64encode(event.delta.text.encode('utf-8')).decode('ascii')
                                    yield f"data: {encoded}\n\n"
                            elif event.type == "message_delta":
                                pass
                # 流式输出结束信号
                yield "data: [DONE]\n\n"
            # 返回fastapi.responses中StreamingResponse对象
            return StreamingResponse(generate_stream(), media_type="text/event-stream")

        # 非流式输出
        result = graph.invoke(input={"messages": input_messages}, checkpointer=checkpointer, config=config)
        # 从结果中提取最后一条助手消息的内容
        assistant_message = result.get("messages", [])[-1] if result.get("messages") else ""
        response_text = assistant_message.content if hasattr(assistant_message, 'content') else str(assistant_message)
        response = ChatResponse(
            content=format_response(response_text),
        )
        return JSONResponse(response.model_dump())
    except Exception as e:
        raise

if __name__ == "__main__":
    logger.info(f"在端口 {PORT} 上启动服务器")
    # uvicorn是一个用于运行ASGI应用的轻量级、超快速的ASGI服务器实现
    # 用于部署基于FastAPI框架的异步PythonWeb应用程序
    uvicorn.run(app, host="0.0.0.0", port=PORT)