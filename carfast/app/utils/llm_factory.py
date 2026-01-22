# app/utils/llm_factory.py
import os
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain_core.callbacks import StdOutCallbackHandler
from dotenv import load_dotenv
from app.config import settings

load_dotenv(override=True)

class LLMFactory:
    @staticmethod
    def get_callbacks():
        # 这里可以扩展 Token 统计回调
        return [StdOutCallbackHandler()]

    @staticmethod
    def get_llm(temperature=0.7, streaming=False):
        """
        获取 LLM 实例
        :param temperature: 温度系数
        :param streaming: 是否开启流式输出 (WebSocket 场景必须为 True)
        """
        # 优先读取环境变量，其次读取 settings
        api_key = os.getenv("DEEPSEEK_API_KEY") or getattr(settings, "DEEPSEEK_API_KEY", "")
        base_url = os.getenv("DEEPSEEK_API_BASE") or "https://api.deepseek.com"

        callbacks = LLMFactory.get_callbacks()

        if api_key:
            return ChatOpenAI(
                model="deepseek-chat",
                openai_api_key=api_key,
                openai_api_base=base_url,
                temperature=temperature,
                streaming=streaming,  # ✅ 关键：显式开启流式
                callbacks=callbacks,
                verbose=True
            )

        print("⚠️ [LLM] Using Local Ollama (deepseek-r1:7b)...")
        return ChatOllama(
            model="deepseek-r1:7b",
            base_url="http://localhost:11434",
            temperature=temperature,
            callbacks=callbacks
        )