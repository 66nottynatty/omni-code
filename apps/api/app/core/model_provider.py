from typing import Optional
from langchain_openai import ChatOpenAI
from app.core.config import get_settings

settings = get_settings()

class ModelProvider:
    @staticmethod
    def get_model(provider: str, model_name: str, temperature: float = 0):
        base_urls = {
            "deepseek": "https://api.deepseek.com/v1",
            "moonshot": "https://api.moonshot.cn/v1",
            "minimax": "https://api.minimax.chat/v1",
            "ollama": "http://localhost:11434/v1",
            "openai": None # Default
        }
        
        provider_lower = provider.lower()
        base_url = base_urls.get(provider_lower)
        
        api_key = settings.openai_api_key
        if provider_lower == "deepseek":
            api_key = settings.deepseek_api_key or settings.openai_api_key
        
        return ChatOpenAI(
            model=model_name,
            temperature=temperature,
            openai_api_key=api_key,
            base_url=base_url
        )

    @staticmethod
    def route_model(task_type: str) -> tuple[str, str]:
        """Auto-routing logic based on task type."""
        if task_type == "coding":
            return "deepseek", "deepseek-coder"
        elif task_type == "analysis":
            return "openai", "gpt-4-turbo"
        else:
            return "openai", "gpt-3.5-turbo"
