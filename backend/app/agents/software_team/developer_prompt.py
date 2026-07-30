"""
Task 5.4：Developer Prompt 组装。
"""

from __future__ import annotations

import json

from app.agents.software_team.prd_prompt import format_prompt_template
from app.prompts.manager import DEVELOPER_PROMPT_ID
from app.prompts.manager import get_default_prompt_manager

HISTORY_RELATIVE_PATH = ".software_team/code_change_history.jsonl"


def render_developer_template(
    *,
    architecture_excerpt: str,
    task_list_excerpt: str,
    dev_instruction: str,
) -> str:

    manager = get_default_prompt_manager()
    template = manager.render(DEVELOPER_PROMPT_ID)

    return format_prompt_template(
        template,
        {
            "architecture_excerpt": architecture_excerpt.strip()
            or "（未提供，请先 filesystem read docs/architecture.md）",
            "task_list_excerpt": task_list_excerpt.strip()
            or "（未提供任务列表）",
            "dev_instruction": dev_instruction.strip() or "实现 MVP 代码",
        },
    )


def format_task_list_for_prompt(tasks: object) -> str:

    if isinstance(tasks, str):

        return tasks

    if isinstance(tasks, list):

        lines = []

        for index, item in enumerate(tasks, start=1):

            if isinstance(item, dict):

                title = item.get("title", item.get("id", f"task-{index}"))
                agent = item.get("agent", "")
                desc = item.get("description", "")

                lines.append(f"{index}. [{agent}] {title} — {desc}")

            else:

                lines.append(f"{index}. {item}")

        return "\n".join(lines)

    return json.dumps(tasks, ensure_ascii=False, indent=2)
