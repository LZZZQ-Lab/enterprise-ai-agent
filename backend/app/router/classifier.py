"""
从 Prompt 推断任务类型（与显式 Task 互补）。
"""

from __future__ import annotations

import re

from app.router.types import TaskKind

_CODE_PATTERNS = (
    re.compile(r"\b(def|class|import|function|async|await)\b", re.I),
    re.compile(r"\b(python|javascript|typescript|java|golang|rust)\b", re.I),
    re.compile(r"\b(bug|debug|refactor|implement|api|sql)\b", re.I),
    re.compile(r"```", re.I),
    re.compile(r"代码|编程|函数|接口|调试"),
)

_MATH_PATTERNS = (
    re.compile(r"\b(integral|derivative|matrix|equation|proof)\b", re.I),
    re.compile(r"\b(calculate|solve|compute)\b", re.I),
    re.compile(r"[∫∑√±×÷=]", re.I),
    re.compile(r"数学|方程|证明|微积分|线性代数|概率"),
)

_LONG_CONTEXT_CHAR_THRESHOLD = 6000


def classify_task_from_prompt(
    prompt: str,
    *,
    long_context_threshold: int = _LONG_CONTEXT_CHAR_THRESHOLD,
) -> tuple[TaskKind, dict[str, object]]:
    """
    返回推断任务类型与信号（供 Routing Report）。
    """

    text = (prompt or "").strip()
    signals: dict[str, object] = {
        "prompt_chars": len(text),
        "long_context_threshold": long_context_threshold,
    }

    if len(text) >= long_context_threshold:
        signals["long_context"] = True
        return TaskKind.LONG_CONTEXT, signals

    code_hits = sum(1 for p in _CODE_PATTERNS if p.search(text))
    math_hits = sum(1 for p in _MATH_PATTERNS if p.search(text))
    signals["code_pattern_hits"] = code_hits
    signals["math_pattern_hits"] = math_hits

    if code_hits >= 2 or (code_hits >= 1 and "```" in text):
        return TaskKind.CODE, signals

    if math_hits >= 1:
        return TaskKind.MATH, signals

    return TaskKind.CHAT, signals


def resolve_task_kind(
    prompt: str,
    explicit_task: TaskKind | str | None,
    *,
    long_context_threshold: int = _LONG_CONTEXT_CHAR_THRESHOLD,
) -> tuple[TaskKind, dict[str, object], str]:
    """
    显式 Task 优先，否则按 Prompt 分类。

    第三个返回值为来源：``explicit`` | ``prompt``.
    """

    if explicit_task is not None:
        if isinstance(explicit_task, TaskKind):
            kind = explicit_task
        else:
            kind = TaskKind(explicit_task.strip().lower())
        return kind, {"source": "explicit"}, "explicit"

    kind, signals = classify_task_from_prompt(
        prompt,
        long_context_threshold=long_context_threshold,
    )
    signals["source"] = "prompt"
    return kind, signals, "prompt"
