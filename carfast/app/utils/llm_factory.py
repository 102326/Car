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
        return [StdOutCallbackHandler()]

    @staticmethod
    def get_llm(temperature=0.7):
        # 优先读取环境变量，其次读取 settings
        api_key = os.getenv("DEEPSEEK_API_KEY") or getattr(settings, "DEEPSEEK_API_KEY", "")

        callbacks = LLMFactory.get_callbacks()

        if api_key:
            return ChatOpenAI(
                model="deepseek-chat",
                openai_api_key=api_key,
                openai_api_base="https://api.deepseek.com",
                temperature=temperature,
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