"""Agent 自动化测试报告（Task 8.2）。"""

from __future__ import annotations

import json
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from pathlib import Path


@dataclass
class AgentCaseResult:
    agent: str
    user_request: str
    success: bool
    flow_checks: dict[str, bool] = field(default_factory=dict)
    tool_checks: dict[str, bool] = field(default_factory=dict)
    workflow_checks: dict[str, bool] = field(default_factory=dict)
    format_checks: dict[str, bool] = field(default_factory=dict)
    notes: str = ""


@dataclass
class AgentTestReport:
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )
    mock_llm: bool = True
    cases: list[AgentCaseResult] = field(default_factory=list)

    def add(self, case: AgentCaseResult) -> None:
        self.cases.append(case)

    @property
    def all_passed(self) -> bool:
        if not self.cases:
            return False
        return all(self._case_passed(case) for case in self.cases)

    @staticmethod
    def _case_passed(case: AgentCaseResult) -> bool:
        groups = (
            case.flow_checks,
            case.tool_checks,
            case.workflow_checks,
            case.format_checks,
        )
        return case.success and all(
            value for group in groups for value in group.values()
        )

    def to_dict(self) -> dict:
        return {
            "generated_at": self.generated_at,
            "mock_llm": self.mock_llm,
            "all_passed": self.all_passed,
            "cases": [asdict(case) for case in self.cases],
        }

    def to_markdown(self) -> str:
        lines = [
            "# Agent Test Report (Task 8.2)",
            "",
            f"- **Generated**: {self.generated_at}",
            f"- **Mock LLM**: {self.mock_llm}",
            f"- **Overall**: {'PASS' if self.all_passed else 'FAIL'}",
            "",
            "## Summary",
            "",
            "| Agent | Success | Flow | Tools | Workflow | Format |",
            "|-------|---------|------|-------|----------|--------|",
        ]

        for case in self.cases:
            lines.append(
                "| {agent} | {ok} | {flow} | {tools} | {wf} | {fmt} |".format(
                    agent=case.agent,
                    ok="✅" if case.success else "❌",
                    flow=_check_col(case.flow_checks),
                    tools=_check_col(case.tool_checks),
                    wf=_check_col(case.workflow_checks),
                    fmt=_check_col(case.format_checks),
                )
            )

        lines.append("")

        for case in self.cases:
            lines.extend(
                [
                    f"## {case.agent}",
                    "",
                    f"**User Request**: {case.user_request}",
                    "",
                    f"**Notes**: {case.notes or '—'}",
                    "",
                    "### Checks",
                    "",
                    _checks_block("Flow", case.flow_checks),
                    _checks_block("Tools", case.tool_checks),
                    _checks_block("Workflow", case.workflow_checks),
                    _checks_block("Format", case.format_checks),
                    "",
                ]
            )

        lines.extend(
            [
                "## JSON",
                "",
                "```json",
                json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
                "```",
                "",
            ]
        )

        return "\n".join(lines)

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_markdown(), encoding="utf-8")


def _check_col(checks: dict[str, bool]) -> str:
    if not checks:
        return "—"
    passed = sum(1 for value in checks.values() if value)
    total = len(checks)
    return f"{passed}/{total}"


def _checks_block(title: str, checks: dict[str, bool]) -> str:
    if not checks:
        return f"- **{title}**: (none)"
    lines = [f"**{title}**:"]
    for name, ok in checks.items():
        mark = "pass" if ok else "FAIL"
        lines.append(f"- `{name}`: {mark}")
    return "\n".join(lines)
