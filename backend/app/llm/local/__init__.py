"""
Transformers 本地推理模块。

Task 2.2：Qwen2.5 本地模型加载与推理，仅供 LocalProvider 调用。
Agent 不得直接 import transformers。
"""

from app.llm.local.inference import Inference
from app.llm.local.model_loader import ModelLoader
from app.llm.local.tokenizer import build_qwen_prompt
from app.llm.local.tokenizer import messages_to_chat_dicts

__all__ = [
    "Inference",
    "ModelLoader",
    "build_qwen_prompt",
    "messages_to_chat_dicts",
]
