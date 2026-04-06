"""
测试流式输出
"""
import requests

url = "http://localhost:8012/v1/chat"

payload = {
    "messages": [
        {"role": "user", "content": "请介绍一下自己"}
    ],
    "is_stream": True,
    "user_id": "user_1",
    "conversation_id": "test-stream-001"
}

print("测试流式输出:")
response = requests.post(url, json=payload, stream=True, timeout=120)
print(f"状态码: {response.status_code}")
print(f"Content-Type: {response.headers.get('Content-Type')}")
print("\n响应内容:")
count = 0
for line in response.iter_lines(decode_unicode=True):
    count += 1
    print(f"[{count}] {repr(line)}")
    if count > 20:
        print("...截断...")
        break
