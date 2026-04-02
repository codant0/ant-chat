"""
启动 Ant Chat Web UI
"""
import subprocess
import sys

if __name__ == "__main__":
    subprocess.run([sys.executable, "-m", "streamlit", "run", "chatbot_ui.py"])
