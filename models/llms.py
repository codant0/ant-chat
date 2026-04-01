# 设置日志模版
import logging
import os

import anthropic
from anthropic import Anthropic

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

MODEL_CONFIGS = {
    "minimax": {
        "base_url": "https://api.minimaxi.com/anthropic",
        "api_key": os.getenv("MINIMAX_API_KEY"),
        "model": "MiniMax-M2.7"
    },
    "glm": {
        "base_url": "https://open.bigmodel.cn/api/anthropic",
        "api_key": os.getenv("GLM_API_KEY"),
        "model": "glm-4.7"
    },
    # TODO
    "ollama": {

    }
}

DEFAULT_LLM_TYPE = "minimax"
DEFAULT_TEMPERATURE = 0.7

class LLMInitializationError(Exception):
    """自定义LLM初始化异常类"""
    pass

def init_llm(llm_type: str = DEFAULT_LLM_TYPE) -> Anthropic:
    try:
        if llm_type not in MODEL_CONFIGS.keys():
            logger.error(f"llm type {llm_type} not supported")
            raise LLMInitializationError("llm type not supported")
        config = MODEL_CONFIGS[llm_type]
        client = anthropic.Anthropic(base_url=config["base_url"], api_key=config["api_key"])
        logger.info(f"success to initialize llm {llm_type}")
        return client

    except LLMInitializationError as e:
        logger.error(f"failed to initialize llm of type: {llm_type}")
        # 若非默认模型，尝试使用默认模型进行初始化
        if llm_type != DEFAULT_LLM_TYPE:
            default_config = MODEL_CONFIGS[DEFAULT_LLM_TYPE]
            client = anthropic.Anthropic(base_url=default_config["base_url"], api_key=default_config["api_key"])
            return client
        raise