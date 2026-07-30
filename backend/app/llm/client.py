"""兼容层：LLMClient 已迁移至 Provider 架构，请优先使用 BaseLLM / OpenAIProvider。"""

from app.llm.openai_provider import OpenAIProvider

LLMClient = OpenAIProvider

__all__ = ["LLMClient", "OpenAIProvider"]
