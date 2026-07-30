"""
Task 5.6：pytest 输出解析与 Test Report。
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class TestReport:
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    success: bool = False
    command: str = ""
    raw_output: str = ""
    unit_tests: list[str] | None = None
    api_tests: list[str] | None = None

    def to_dict(self) -> dict:

        return {
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "errors": self.errors,
            "success": self.success,
            "command": self.command,
            "unit_tests": self.unit_tests or [],
            "api_tests": self.api_tests or [],
        }

    def to_markdown(self) -> str:

        status = "通过" if self.success else "失败"

        lines = [
            "# Test Report",
            "",
            "## 摘要",
            f"- **结果**: {status}",
            f"- **通过**: {self.passed}",
            f"- **失败**: {self.failed}",
            f"- **跳过**: {self.skipped}",
            f"- **错误**: {self.errors}",
            "",
            "## 测试范围",
            "",
            "### Unit Test",
            "",
        ]

        if self.unit_tests:

            for item in self.unit_tests:

                lines.append(f"- {item}")

        else:

            lines.append("- （见 pytest 输出）")

        lines.extend(
            [
                "",
                "### API Test",
                "",
            ]
        )

        if self.api_tests:

            for item in self.api_tests:

                lines.append(f"- {item}")

        else:

            lines.append("- （见 pytest 输出）")

        lines.extend(
            [
                "",
                "## 执行命令",
                "",
                f"```bash\n{self.command or 'pytest'}\n```",
                "",
                "## pytest 输出",
                "",
                "```text",
                (self.raw_output or "(无输出)")[:12000],
                "```",
                "",
            ]
        )

        return "\n".join(lines)


_RESULT_RE = re.compile(
    r"(?:(\d+) failed)|(?:(\d+) passed)|(?:(\d+) skipped)|(?:(\d+) error)",
    re.I,
)


def parse_pytest_output(
    output: str,
    *,
    command: str = "",
) -> TestReport:

    text = output or ""
    passed = failed = skipped = errors = 0

    summary_line = ""

    for line in reversed(text.splitlines()):

        lower = line.lower()

        if "passed" in lower or "failed" in lower or "error" in lower:

            summary_line = line
            break

    if summary_line:

        failed_m = re.search(r"(\d+)\s+failed", summary_line, re.I)
        passed_m = re.search(r"(\d+)\s+passed", summary_line, re.I)
        skipped_m = re.search(r"(\d+)\s+skipped", summary_line, re.I)
        errors_m = re.search(r"(\d+)\s+error", summary_line, re.I)

        if failed_m:

            failed = int(failed_m.group(1))

        if passed_m:

            passed = int(passed_m.group(1))

        if skipped_m:

            skipped = int(skipped_m.group(1))

        if errors_m:

            errors = int(errors_m.group(1))

    success = failed == 0 and errors == 0 and passed > 0

    if "no tests ran" in text.lower():

        success = False

    return TestReport(
        passed=passed,
        failed=failed,
        skipped=skipped,
        errors=errors,
        success=success,
        command=command,
        raw_output=text,
        unit_tests=_collect_test_files(text, "test_unit"),
        api_tests=_collect_test_files(text, "test_api"),
    )


def _collect_test_files(output: str, prefix: str) -> list[str]:

    found: list[str] = []

    for line in output.splitlines():

        if prefix in line and ".py" in line:

            found.append(line.strip()[:120])

    return found[:20]
