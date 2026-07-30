from __future__ import annotations

from app.llm.types import Message


def messages_to_chat_dicts(
    messages: list[Message],
) -> list[dict[str, str]]:
    """
    将平台 Message 转为 Qwen Chat Template 所需格式。

    支持 system / user / assistant；tool 消息折叠为 user 上下文。
    """

    chat_messages: list[dict[str, str]] = []

    for message in messages:

        role = message.role
        content = (message.content or "").strip()

        if not content and role != "assistant":

            continue

        if role == "tool":

            tool_name = message.name or "tool"
            content = f"[Tool Result:{tool_name}]\n{content}"
            role = "user"

        elif role not in {"system", "user", "assistant"}:

            content = f"[{role}]\n{content}"
            role = "user"

        chat_messages.append(
            {
                "role": role,
                "content": content,
            }
        )

    return chat_messages


def build_qwen_prompt(
    tokenizer,
    messages: list[Message],
) -> str:
    """
    使用 Qwen2.5-Instruct Chat Template 构建推理 Prompt。
    """

    chat_messages = messages_to_chat_dicts(messages)

    if not chat_messages:

        raise ValueError("No valid messages for local inference.")

    if not hasattr(tokenizer, "apply_chat_template"):

        raise RuntimeError(
            "Tokenizer does not support apply_chat_template; "
            "expected a Qwen2.5-Instruct tokenizer."
        )

    return tokenizer.apply_chat_template(
        chat_messages,
        tokenize=False,
        add_generation_prompt=True,
    )
