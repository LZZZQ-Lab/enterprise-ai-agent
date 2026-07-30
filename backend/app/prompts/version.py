"""
Prompt 版本模型（Task 6.5）。
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from dataclasses import field
from typing import Any


_VERSION_RE = re.compile(
    r"^(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9.]+))?$"
)


@dataclass(frozen=True)
class PromptVersion:
    """
    单个 Prompt 版本定义。
    """

    prompt_id: str
    version: str
    content: str
    role: str = ""
    parent_id: str | None = None
    parent_version: str | None = None
    description: str = ""
    variables: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def semver_key(self) -> tuple[int, int, int, str]:
        match = _VERSION_RE.match(self.version.strip())

        if not match:
            return (0, 0, 0, self.version)

        major, minor, patch, suffix = match.groups()
        return (int(major), int(minor), int(patch), suffix or "")


def compare_versions(left: str, right: str) -> int:
    """
    比较语义化版本；无法解析时按字符串比较。
    """

    left_key = PromptVersion(
        prompt_id="_",
        version=left,
        content="",
    ).semver_key()
    right_key = PromptVersion(
        prompt_id="_",
        version=right,
        content="",
    ).semver_key()

    if left_key[:3] != right_key[:3]:
        if left_key[:3] < right_key[:3]:
            return -1
        if left_key[:3] > right_key[:3]:
            return 1

    if left_key[3] < right_key[3]:
        return -1

    if left_key[3] > right_key[3]:
        return 1

    return 0


def latest_version(versions: list[str]) -> str:
    if not versions:
        raise ValueError("no versions")

    return sorted(versions, key=lambda item: PromptVersion(
        prompt_id="_",
        version=item,
        content="",
    ).semver_key())[-1]


def extract_variables(template: str) -> tuple[str, ...]:
    """
    从 ``{var}`` 占位符提取变量名（忽略 ``{{`` 转义）。
    """

    names: list[str] = []
    index = 0

    while index < len(template):
        start = template.find("{", index)

        if start < 0:
            break

        if start + 1 < len(template) and template[start + 1] == "{":
            index = start + 2
            continue

        end = template.find("}", start + 1)

        if end < 0:
            break

        name = template[start + 1:end].strip()

        if name and re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", name):
            names.append(name)

        index = end + 1

    return tuple(dict.fromkeys(names))
