"""
Task 5.7：Deployment Report。
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field


@dataclass
class DeploymentReport:
    success: bool = False
    artifacts: list[str] = field(default_factory=list)
    environment_files: list[str] = field(default_factory=list)
    build_command: str = ""
    build_output: str = ""
    deploy_command: str = ""
    deploy_output: str = ""
    notes: str = ""

    def to_dict(self) -> dict:

        return {
            "success": self.success,
            "artifacts": self.artifacts,
            "environment_files": self.environment_files,
            "build_command": self.build_command,
            "deploy_command": self.deploy_command,
            "notes": self.notes,
        }

    def to_markdown(self) -> str:

        status = "成功" if self.success else "失败或未完全执行"

        lines = [
            "# Deployment Report",
            "",
            "## 摘要",
            f"- **状态**: {status}",
            "",
            "## 生成产物",
            "",
        ]

        if self.artifacts:

            for item in self.artifacts:

                lines.append(f"- `{item}`")

        else:

            lines.append("- （无）")

        lines.extend(
            [
                "",
                "## Environment",
                "",
            ]
        )

        if self.environment_files:

            for item in self.environment_files:

                lines.append(f"- `{item}`")

        else:

            lines.append("- （无）")

        lines.extend(
            [
                "",
                "## Build",
                "",
                f"```bash\n{self.build_command or '(skipped)'}\n```",
                "",
                "```text",
                (self.build_output or "(无)")[:8000],
                "```",
                "",
                "## Deploy",
                "",
                f"```bash\n{self.deploy_command or '(skipped)'}\n```",
                "",
                "```text",
                (self.deploy_output or "(无)")[:8000],
                "```",
                "",
            ]
        )

        if self.notes:

            lines.extend(
                [
                    "## 备注",
                    "",
                    self.notes,
                    "",
                ]
            )

        return "\n".join(lines)
