"""
测试 /v1/chat 接口
"""
import requests

url = "http://localhost:8012/v1/chat"

# 测试1: 单轮对话 (非流式)
payload1 = {
    "messages": [
        {"role": "user", "content": "你好"}
    ],
    "is_stream": False,
    "user_id": "user_1",
    "conversation_id": "test-001"
}

print("=" * 50)
print("测试1: 单轮对话 (非流式)")
print("=" * 50)
try:
    response = requests.post(url, json=payload1, timeout=60)
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.text}")
except Exception as e:
    print(f"错误: {e}")

# 测试2: 多轮对话 (非流式)
payload2 = {
    "messages": [
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "你好！有什么可以帮助你的吗？"},
        {"role": "user", "content": "今天天气怎么样？"}
    ],
    "is_stream": False,
    "user_id": "user_1",
    "conversation_id": "test-002"
}

print("\n" + "=" * 50)
print("测试2: 多轮对话 (非流式)")
print("=" * 50)
try:
    response = requests.post(url, json=payload2, timeout=60)
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.text}")
except Exception as e:
    print(f"错误: {e}")

# 测试3: 流式输出
payload3 = {
    "messages": [
        {"role": "user", "content": "请介绍一下自己"}
    ],
    "is_stream": True,
    "user_id": "user_1",
    "conversation_id": "test-003"
}

print("\n" + "=" * 50)
print("测试3: 流式输出")
print("=" * 50)
try:
    response = requests.post(url, json=payload3, stream=True, timeout=120)
    print(f"状态码: {response.status_code}")
    print("流式响应内容:")
    for line in response.iter_lines(decode_unicode=True):
        if line.startswith("data: "):
            data = line[6:]
            print(f"  {data}")
except Exception as e:
    print(f"错误: {e}")
