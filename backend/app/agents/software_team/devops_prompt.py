"""
Task 5.7：DevOps Prompt。
"""

from __future__ import annotations

from app.agents.software_team.prd_prompt import format_prompt_template
from app.prompts.context import load_template

DEVOPS_TEMPLATE_NAME = "software_team_devops.txt"
DEPLOYMENT_REPORT_FILENAME = "DEPLOYMENT_REPORT.md"

DEFAULT_BUILD_CMD = "docker compose build"
DEFAULT_DEPLOY_CMD = "docker compose up -d"


def render_devops_template(
    *,
    architecture_excerpt: str,
    deploy_instruction: str,
) -> str:

    template = load_template(DEVOPS_TEMPLATE_NAME)

    if not template:

        raise FileNotFoundError(
            f"Missing prompt template: {DEVOPS_TEMPLATE_NAME}"
        )

    return format_prompt_template(
        template,
        {
            "architecture_excerpt": architecture_excerpt.strip()
            or "（未提供架构，按通用 Web 服务部署）",
            "deploy_instruction": deploy_instruction.strip()
            or "生成 Dockerfile 与 docker-compose，配置环境并 build/deploy",
        },
    )
