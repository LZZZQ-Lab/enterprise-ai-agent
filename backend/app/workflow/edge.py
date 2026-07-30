"""
Workflow 边（含条件分支标签）。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WorkflowEdge:
    """
    from_id → to_id。

    condition:
    - None：无条件后继（普通 DAG）
    - "true" / "false"：Conditional 节点分支
    - 其他字符串：自定义分支名（写入 shared __branch__）
    """

    from_id: str
    to_id: str
    condition: str | None = None

    def matches_branch(self, branch: str | None) -> bool:

        if self.condition is None:

            return branch is None

        return self.condition == branch
