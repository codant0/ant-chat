"""
Ant Chat 启动脚本
同时启动后端 (main.py) 和前端 (Reflex)
"""

import subprocess
import sys
import time
import os
import signal

# 进程列表
processes = []

def start_backend():
    """启动后端服务 (FastAPI on port 8012)"""
    print("[Backend] 启动后端服务...")
    proc = subprocess.Popen(
        [sys.executable, "main.py"],
        cwd=os.path.dirname(os.path.abspath(__file__)),
    )
    processes.append(proc)
    return proc

def start_frontend():
    """启动前端服务 (Reflex)"""
    print("[Frontend] 启动前端服务...")
    # Windows 使用 shell=True
    proc = subprocess.Popen(
        "reflex run",
        cwd=os.path.dirname(os.path.abspath(__file__)),
        shell=True,
    )
    processes.append(proc)
    return proc

def cleanup(signum=None, frame=None):
    """清理所有进程"""
    print("\n正在停止所有服务...")
    for proc in processes:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
    print("所有服务已停止")
    sys.exit(0)

def main():
    # 注册信号处理
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    print("=" * 50)
    print("Ant Chat 启动中...")
    print("=" * 50)

    # 启动后端
    start_backend()
    time.sleep(2)  # 等待后端启动

    # 启动前端
    start_frontend()

    print("\n" + "=" * 50)
    print("服务已启动:")
    print("  - 后端 API: http://localhost:8012")
    print("  - 前端界面: http://localhost:3000")
    print("=" * 50)
    print("\n按 Ctrl+C 停止所有服务\n")

    # 等待进程结束
    try:
        while True:
            # 检查进程状态
            for i, proc in enumerate(processes):
                if proc.poll() is not None:
                    print(f"进程 {i} 已退出，退出码: {proc.returncode}")
            time.sleep(1)
    except KeyboardInterrupt:
        cleanup()

if __name__ == "__main__":
    main()
