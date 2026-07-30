"""
Task 5.5：Review Report 结构化模型。
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field


@dataclass
class ReviewFinding:
    category: str
    severity: str
    location: str
    issue: str
    suggestion: str

    def to_dict(self) -> dict:

        return {
            "category": self.category,
            "severity": self.severity,
            "location": self.location,
            "issue": self.issue,
            "suggestion": self.suggestion,
        }


@dataclass
class ReviewReport:
    summary: str = ""
    findings: list[ReviewFinding] = field(default_factory=list)
    diff_stats: str = ""

    def to_dict(self) -> dict:

        return {
            "summary": self.summary,
            "diff_stats": self.diff_stats,
            "findings": [item.to_dict() for item in self.findings],
        }

    def to_markdown(self) -> str:

        lines = [
            "# Code Review Report",
            "",
            "## 摘要",
            self.summary or "（无）",
            "",
        ]

        if self.diff_stats:

            lines.extend(
                [
                    "## Diff 概览",
                    self.diff_stats,
                    "",
                ]
            )

        for section, label in _CATEGORY_LABELS.items():

            items = [
                finding
                for finding in self.findings
                if finding.category == section
            ]

            lines.append(f"## {label}")
            lines.append("")

            if not items:

                lines.append("- 未发现明显问题。")
                lines.append("")

                continue

            for finding in items:

                lines.extend(
                    [
                        f"- **[{finding.severity}]** `{finding.location}`",
                        f"  - **问题**：{finding.issue}",
                        f"  - **建议**：{finding.suggestion}",
                    ]
                )

            lines.append("")

        lines.append("## 修改建议汇总")
        lines.append("")

        suggestions = [
            finding.suggestion
            for finding in self.findings
            if finding.suggestion
        ]

        if suggestions:

            for index, suggestion in enumerate(suggestions, start=1):

                lines.append(f"{index}. {suggestion}")

        else:

            lines.append("无需修改。")

        lines.append("")

        return "\n".join(lines)


_CATEGORY_LABELS = {
    "standards": "代码规范",
    "security": "安全问题",
    "performance": "性能问题",
    "architecture": "架构问题",
}
