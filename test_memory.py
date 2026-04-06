"""
测试 /v1/chat 接口的上下文记忆、短期记忆、长期记忆功能

测试说明：
1. 上下文记忆：在同一 conversation_id 中传递历史消息，AI 能基于之前的对话上下文回复
2. 短期记忆：使用 PostgresSaver，即使不传递历史消息，只要 conversation_id 相同，就能记住之前的对话
3. 长期记忆：使用 PostgresStore，跨 conversation_id 记住用户的关键信息
"""
import requests
import time
import sys
import json

url = "http://localhost:8012/v1/chat"

def print_section(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def debug_response(response):
    """打印响应详情用于调试"""
    print(f"状态码: {response.status_code}")
    print(f"响应头: {dict(response.headers)}")
    print(f"原始响应: {response.text[:1000] if response.text else 'Empty'}")


def make_request_with_retry(payload, max_retries=3, retry_delay=3):
    """带重试的请求"""
    last_error = None
    for attempt in range(max_retries):
        try:
            response = requests.post(url, json=payload, timeout=60)
            if response.status_code == 200:
                try:
                    json_data = response.json()
                    if json_data.get('content'):
                        return response
                except:
                    pass
            last_error = response
            if attempt < max_retries - 1:
                print(f"  请求返回 {response.status_code}，第 {attempt + 1} 次重试...")
                time.sleep(retry_delay)
        except requests.exceptions.ConnectionError as e:
            last_error = e
            if attempt < max_retries - 1:
                print(f"  连接错误，第 {attempt + 1} 次重试...")
                time.sleep(retry_delay)
    return last_error


def test_context_memory():
    """测试1: 上下文记忆 - 在同一 conversation_id 中传递历史消息"""
    print_section("测试1: 上下文记忆（基于传入的历史消息）")

    conversation_id = f"ctx-test-{int(time.time())}"

    # 第一轮对话
    payload1 = {
        "messages": [{"role": "user", "content": "我叫张三"}],
        "is_stream": False,
        "user_id": "user_1",
        "conversation_id": conversation_id
    }

    print("第一轮: 告诉AI我叫张三")
    response1 = make_request_with_retry(payload1)

    if response1 is None or not hasattr(response1, 'status_code'):
        print(f"  请求失败: {response1}")
        return False

    if response1.status_code != 200:
        debug_response(response1)
        return False

    resp1_json = response1.json()
    print(f"状态码: {response1.status_code}")
    print(f"AI回复: {resp1_json.get('content', '')}")

    # 等待一下确保数据处理完成
    time.sleep(3)

    # 第二轮对话 - 传递历史消息上下文
    payload2 = {
        "messages": [
            {"role": "user", "content": "我叫张三"},
            {"role": "assistant", "content": resp1_json.get('content', '')},
            {"role": "user", "content": "我叫什么名字？"}
        ],
        "is_stream": False,
        "user_id": "user_1",
        "conversation_id": conversation_id
    }

    print("\n第二轮: 问AI我叫什么名字（传递历史消息）")
    response2 = make_request_with_retry(payload2)

    if response2 is None or not hasattr(response2, 'status_code'):
        print(f"  请求失败: {response2}")
        return False

    if response2.status_code != 200:
        debug_response(response2)
        return False

    resp2_json = response2.json()
    print(f"状态码: {response2.status_code}")
    print(f"AI回复: {resp2_json.get('content', '')}")

    # 验证：AI 应该记住用户叫张三
    content = resp2_json.get('content', '')
    if '张三' in content:
        print("\n✓ 上下文记忆测试通过：AI记住了用户的名字")
        return True
    else:
        print("\n✗ 上下文记忆测试失败：AI没有记住用户的名字")
        return False


def test_short_term_memory():
    """测试2: 短期记忆 - 使用 PostgresSaver，不传历史消息但同 conversation_id"""
    print_section("测试2: 短期记忆（基于 PostgresSaver，跨请求保持对话状态）")

    conversation_id = f"short-term-{int(time.time())}"

    # 第一轮对话
    payload1 = {
        "messages": [{"role": "user", "content": "我喜欢吃苹果"}],
        "is_stream": False,
        "user_id": "user_1",
        "conversation_id": conversation_id
    }

    print("第一轮: 告诉AI我喜欢吃苹果")
    response1 = make_request_with_retry(payload1)

    if response1 is None or not hasattr(response1, 'status_code'):
        print(f"  请求失败: {response1}")
        return False

    if response1.status_code != 200:
        debug_response(response1)
        return False
    print(f"状态码: {response1.status_code}")
    print(f"AI回复: {response1.json().get('content', '')}")

    # 等待一下确保数据写入
    time.sleep(3)

    # 第二轮对话 - 不传递历史消息，只使用相同的 conversation_id
    payload2 = {
        "messages": [{"role": "user", "content": "我喜欢吃什么水果？"}],
        "is_stream": False,
        "user_id": "user_1",
        "conversation_id": conversation_id
    }

    print("\n第二轮: 问AI我喜欢吃什么水果（不传历史消息，只用相同conversation_id）")
    response2 = make_request_with_retry(payload2)

    if response2 is None or not hasattr(response2, 'status_code'):
        print(f"  请求失败: {response2}")
        return False

    if response2.status_code != 200:
        debug_response(response2)
        return False
    resp2_json = response2.json()
    print(f"状态码: {response2.status_code}")
    print(f"AI回复: {resp2_json.get('content', '')}")

    content = resp2_json.get('content', '')
    if '苹果' in content:
        print("\n✓ 短期记忆测试通过：AI通过PostgresSaver记住了用户的喜好")
        return True
    else:
        print("\n✗ 短期记忆测试失败：AI没有通过PostgresSaver记住用户的喜好")
        return False


def test_long_term_memory():
    """测试3: 长期记忆 - 使用 PostgresStore，跨 conversation_id"""
    print_section("测试3: 长期记忆（基于 PostgresStore，跨对话记住用户信息）")

    user_id = f"user_1"
    conv_id_1 = f"long-term-1-{int(time.time())}"
    conv_id_2 = f"long-term-2-{int(time.time())}"

    # 第一条对话
    payload1 = {
        "messages": [{"role": "user", "content": "记住我叫李四，今年30岁，职业是软件工程师"}],
        "is_stream": False,
        "user_id": user_id,
        "conversation_id": conv_id_1
    }

    print("第一轮: 告诉AI我叫李四，30岁，软件工程师")
    response1 = make_request_with_retry(payload1)

    if response1 is None or not hasattr(response1, 'status_code'):
        print(f"  请求失败: {response1}")
        return False

    if response1.status_code != 200:
        debug_response(response1)
        return False
    print(f"状态码: {response1.status_code}")
    print(f"AI回复: {response1.json().get('content', '')}")

    time.sleep(3)

    # 第二条不同 conversation_id 的对话
    payload2 = {
        "messages": [{"role": "user", "content": "我叫什么名字？"}],
        "is_stream": False,
        "user_id": user_id,
        "conversation_id": conv_id_2
    }

    print("\n第二轮: 用新的conversation_id问AI我叫什么名字")
    response2 = make_request_with_retry(payload2)

    if response2 is None or not hasattr(response2, 'status_code'):
        print(f"  请求失败: {response2}")
        return False

    if response2.status_code != 200:
        debug_response(response2)
        return False
    resp2_json = response2.json()
    print(f"状态码: {response2.status_code}")
    print(f"AI回复: {resp2_json.get('content', '')}")

    content = resp2_json.get('content', '')
    if '李四' in content:
        print("\n✓ 长期记忆测试通过：AI通过PostgresStore记住了用户信息")
        return True
    else:
        print("\n✗ 长期记忆测试失败：AI没有通过PostgresStore记住用户信息")
        return False


def test_no_memory_different_conversation():
    """测试4: 验证不同 conversation_id 不会共享短期记忆"""
    print_section("测试4: 验证不同conversation_id不共享短期记忆")

    conv_id_1 = f"no-share-1-{int(time.time())}"
    conv_id_2 = f"no-share-2-{int(time.time())}"

    # 对话1
    payload1 = {
        "messages": [{"role": "user", "content": "我喜欢吃香蕉"}],
        "is_stream": False,
        "user_id": "user_1",
        "conversation_id": conv_id_1
    }

    print("对话1: 告诉AI我喜欢吃香蕉")
    response1 = make_request_with_retry(payload1)

    if response1 is None or not hasattr(response1, 'status_code'):
        print(f"  请求失败: {response1}")
        return False

    if response1.status_code != 200:
        debug_response(response1)
        return False
    print(f"状态码: {response1.status_code}")

    time.sleep(3)

    # 对话2 - 不同 conversation_id
    payload2 = {
        "messages": [{"role": "user", "content": "我喜欢吃什么？"}],
        "is_stream": False,
        "user_id": "user_1",
        "conversation_id": conv_id_2
    }

    print("对话2: 用不同conversation_id问同样的问题")
    response2 = make_request_with_retry(payload2)

    if response2 is None or not hasattr(response2, 'status_code'):
        print(f"  请求失败: {response2}")
        return False

    if response2.status_code != 200:
        debug_response(response2)
        return False
    resp2_json = response2.json()
    print(f"状态码: {response2.status_code}")
    print(f"AI回复: {resp2_json.get('content', '')}")

    content = resp2_json.get('content', '')
    if '香蕉' not in content:
        print("\n✓ 隔离测试通过：不同conversation_id的短期记忆是隔离的")
        return True
    else:
        print("\n✗ 隔离测试失败：AI错误地记住了另一对话的信息")
        return False


if __name__ == "__main__":
    print("开始测试对话接口的记忆功能")
    print("确保服务器已在 http://localhost:8012 上运行")
    print("注意: 500错误通常表示服务器启动失败，请检查服务器日志")

    results = []
    results.append(("上下文记忆", test_context_memory()))
    results.append(("短期记忆", test_short_term_memory()))
    results.append(("长期记忆", test_long_term_memory()))
    results.append(("记忆隔离", test_no_memory_different_conversation()))

    print("\n" + "=" * 60)
    print("  测试结果汇总")
    print("=" * 60)
    for name, passed in results:
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"  {name}: {status}")

    all_passed = all(passed for _, passed in results)
    print("\n" + ("全部测试通过！" if all_passed else "存在测试失败！"))
