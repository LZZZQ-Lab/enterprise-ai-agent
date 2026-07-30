"""
Task 5.5：Diff 启发式审查（无 LLM 时的 fallback）。
"""

from __future__ import annotations

import re

from app.agents.software_team.review_report import ReviewFinding
from app.agents.software_team.review_report import ReviewReport


def analyze_diff_heuristics(
    git_diff: str,
    *,
    architecture_excerpt: str = "",
) -> ReviewReport:

    findings: list[ReviewFinding] = []
    lines = git_diff.splitlines()

    added = [line for line in lines if line.startswith("+") and not line.startswith("+++")]

    for index, line in enumerate(added):

        loc = f"diff:+L{index + 1}"

        if re.search(r"\beval\s*\(|\bexec\s*\(", line):

            findings.append(
                ReviewFinding(
                    category="security",
                    severity="critical",
                    location=loc,
                    issue="使用 eval/exec，存在代码注入风险",
                    suggestion="移除 eval/exec，改用安全解析或白名单 API",
                )
            )

        if re.search(
            r"password\s*=\s*['\"]|api[_-]?key\s*=\s*['\"]",
            line,
            re.I,
        ):

            findings.append(
                ReviewFinding(
                    category="security",
                    severity="critical",
                    location=loc,
                    issue="疑似硬编码密钥或密码",
                    suggestion="改为环境变量或密钥管理服务，勿提交明文",
                )
            )

        if "pickle.loads" in line or "yaml.load(" in line:

            findings.append(
                ReviewFinding(
                    category="security",
                    severity="major",
                    location=loc,
                    issue="不安全的反序列化调用",
                    suggestion="使用 json 或 yaml.safe_load，并校验输入来源",
                )
            )

        if re.search(r"SELECT\s+\*\s+FROM", line, re.I):

            findings.append(
                ReviewFinding(
                    category="performance",
                    severity="minor",
                    location=loc,
                    issue="SELECT * 可能拉取多余列",
                    suggestion="仅查询必要字段并确保有合适索引",
                )
            )

        if "time.sleep(" in line and "test" not in line.lower():

            findings.append(
                ReviewFinding(
                    category="performance",
                    severity="minor",
                    location=loc,
                    issue="生产路径中使用 sleep 阻塞",
                    suggestion="改用异步等待、重试退避或队列调度",
                )
            )

        if re.search(r"\bprint\s*\(", line) and ".py" in git_diff:

            findings.append(
                ReviewFinding(
                    category="standards",
                    severity="info",
                    location=loc,
                    issue="使用 print 调试输出",
                    suggestion="改用 structured logging（logger.info 等）",
                )
            )

    if len(added) > 200 and "test" not in git_diff.lower():

        findings.append(
            ReviewFinding(
                category="standards",
                severity="major",
                location="diff",
                issue="大量代码变更但 Diff 中未见测试文件",
                suggestion="补充单元测试或集成测试覆盖核心变更",
            )
        )

    if architecture_excerpt and "FastAPI" in architecture_excerpt:

        if any("flask" in line.lower() for line in added):

            findings.append(
                ReviewFinding(
                    category="architecture",
                    severity="major",
                    location="diff",
                    issue="架构文档指定 FastAPI，Diff 出现 Flask 相关代码",
                    suggestion="与 architecture.md 对齐，统一 Web 框架",
                )
            )

    stats = (
        f"- 变更行（近似）: +{len(added)} / 总 diff 行 {len(lines)}"
    )

    critical = sum(1 for item in findings if item.severity == "critical")
    major = sum(1 for item in findings if item.severity == "major")

    if critical:

        verdict = "需修改（存在 critical 问题）"

    elif major:

        verdict = "有条件通过（存在 major 问题）"

    elif findings:

        verdict = "有条件通过（存在 minor/info 问题）"

    else:

        verdict = "通过"

    summary = (
        f"启发式审查完成：{verdict}；共 {len(findings)} 条发现。"
    )

    return ReviewReport(
        summary=summary,
        findings=findings,
        diff_stats=stats,
    )


REQUIRED_REPORT_MARKERS = (
    "代码规范",
    "安全问题",
    "性能问题",
    "架构问题",
    "修改建议",
)


def llm_report_has_sections(markdown: str) -> bool:

    for marker in REQUIRED_REPORT_MARKERS:

        if marker not in markdown:

            return False

    return True
