"""Task 8.4: build stress_test_report.md from Locust CSV stats."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from loadtest.scenarios import StressScenario

LOADTEST_ROOT = Path(__file__).resolve().parent
BACKEND_ROOT = LOADTEST_ROOT.parent
ARTIFACTS_DIR = BACKEND_ROOT / "artifacts"
STRESS_REPORT = ARTIFACTS_DIR / "stress_test_report.md"
RESULTS_DIR = LOADTEST_ROOT / "results"

CATEGORY_API = "API"
CATEGORY_WORKFLOW = "Agent Workflow"
CATEGORY_GATEWAY = "Inference Gateway"

CATEGORY_PREFIXES: tuple[tuple[str, str], ...] = (
    ("API ", CATEGORY_API),
    ("Workflow ", CATEGORY_WORKFLOW),
    ("Gateway ", CATEGORY_GATEWAY),
)


@dataclass
class EndpointStats:
    name: str
    category: str
    request_count: int
    failure_count: int
    avg_latency_ms: float
    qps: float
    error_rate_pct: float


@dataclass
class ScenarioSummary:
    scenario: StressScenario
    total_requests: int
    total_failures: int
    avg_latency_ms: float
    qps: float
    error_rate_pct: float
    endpoints: list[EndpointStats]


def _category_for_name(name: str) -> str:
    for prefix, category in CATEGORY_PREFIXES:
        if name.startswith(prefix):
            return category
    if "/health" in name or "/api/v1/chat" in name:
        return CATEGORY_API
    if "dashboard" in name or "workflow" in name.lower():
        return CATEGORY_WORKFLOW
    if "inference" in name.lower():
        return CATEGORY_GATEWAY
    return "Other"


def _parse_float(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _parse_int(value: str) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def parse_locust_stats_csv(path: Path, *, include_aggregated: bool = False) -> list[EndpointStats]:
    if not path.is_file():
        return []

    rows: list[EndpointStats] = []
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            name = (row.get("Name") or row.get("name") or "").strip()
            if not name:
                continue
            if name == "Aggregated" and not include_aggregated:
                continue

            req_count = _parse_int(row.get("Request Count") or row.get("request_count") or "0")
            fail_count = _parse_int(row.get("Failure Count") or row.get("failure_count") or "0")
            avg_ms = _parse_float(
                row.get("Average Response Time") or row.get("average_response_time") or "0"
            )
            qps = _parse_float(row.get("Requests/s") or row.get("requests_per_s") or "0")
            error_rate = (fail_count / req_count * 100.0) if req_count else 0.0

            rows.append(
                EndpointStats(
                    name=name,
                    category=_category_for_name(name),
                    request_count=req_count,
                    failure_count=fail_count,
                    avg_latency_ms=avg_ms,
                    qps=qps,
                    error_rate_pct=error_rate,
                )
            )
    return rows


def parse_aggregated_row(path: Path) -> EndpointStats | None:
    for row in parse_locust_stats_csv(path, include_aggregated=True):
        if row.name == "Aggregated":
            return row
    return None


def summarize_scenario(
    scenario: StressScenario,
    csv_path: Path,
) -> ScenarioSummary:
    endpoints = parse_locust_stats_csv(csv_path)
    agg = parse_aggregated_row(csv_path)
    if agg:
        total_req = agg.request_count
        total_fail = agg.failure_count
        avg_lat = agg.avg_latency_ms
        qps = agg.qps
    else:
        total_req = sum(e.request_count for e in endpoints)
        total_fail = sum(e.failure_count for e in endpoints)
        if total_req:
            avg_lat = sum(e.avg_latency_ms * e.request_count for e in endpoints) / total_req
            qps = sum(e.qps for e in endpoints)
        else:
            avg_lat = 0.0
            qps = 0.0

    error_rate = (total_fail / total_req * 100.0) if total_req else 0.0

    return ScenarioSummary(
        scenario=scenario,
        total_requests=total_req,
        total_failures=total_fail,
        avg_latency_ms=avg_lat,
        qps=qps,
        error_rate_pct=error_rate,
        endpoints=endpoints,
    )


def _category_table(rows: list[EndpointStats]) -> list[str]:
    by_cat: dict[str, list[EndpointStats]] = {}
    for row in rows:
        by_cat.setdefault(row.category, []).append(row)

    lines: list[str] = []
    for category in (CATEGORY_API, CATEGORY_WORKFLOW, CATEGORY_GATEWAY):
        items = by_cat.get(category, [])
        if not items:
            continue
        total_req = sum(i.request_count for i in items)
        total_fail = sum(i.failure_count for i in items)
        if total_req:
            avg_lat = sum(i.avg_latency_ms * i.request_count for i in items) / total_req
            qps = sum(i.qps for i in items)
            err = total_fail / total_req * 100.0
        else:
            avg_lat = qps = err = 0.0
        lines.append(
            f"| {category} | {total_req} | {qps:.2f} | {avg_lat:.1f} | {err:.2f}% |"
        )
    return lines


def build_stress_report(
    summaries: list[ScenarioSummary],
    *,
    host: str,
    mock_mode: bool,
    generated_at: str,
) -> str:
    lines = [
        "# 压力测试报告（Task 8.4 · Locust）",
        "",
        f"生成时间：{generated_at}",
        f"目标 Host：`{host}`",
        "",
        "## 测试范围",
        "",
        "| 类别 | 端点 |",
        "| --- | --- |",
        f"| {CATEGORY_API} | `GET /health`, `POST /api/v1/chat` |",
        f"| {CATEGORY_WORKFLOW} | `POST /api/v1/dashboard/projects`, `GET /api/v1/dashboard/workflow/{{id}}` |",
        f"| {CATEGORY_GATEWAY} | `POST /api/v1/inference/chat/completions`, `GET /api/v1/inference/stats` |",
        "",
        "## 场景汇总",
        "",
        "指标：**QPS**、**平均延迟 (ms)**、**错误率**",
        "",
        "| 场景 | 总请求 | QPS | 平均延迟 (ms) | 错误率 |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]

    for summary in summaries:
        lines.append(
            f"| {summary.scenario.label} | {summary.total_requests} | "
            f"{summary.qps:.2f} | {summary.avg_latency_ms:.1f} | "
            f"{summary.error_rate_pct:.2f}% |"
        )

    for summary in summaries:
        lines.extend(
            [
                "",
                f"### {summary.scenario.label}",
                "",
                "#### 按类别",
                "",
                "| 类别 | 请求数 | QPS | 平均延迟 (ms) | 错误率 |",
                "| --- | ---: | ---: | ---: | ---: |",
            ]
        )
        cat_lines = _category_table(summary.endpoints)
        if cat_lines:
            lines.extend(cat_lines)
        else:
            lines.append("| (无明细) | - | - | - | - |")

        lines.extend(
            [
                "",
                "#### 端点明细",
                "",
                "| 端点 | 请求数 | QPS | 平均延迟 (ms) | 错误率 |",
                "| --- | ---: | ---: | ---: | ---: |",
            ]
        )
        if summary.endpoints:
            for ep in sorted(summary.endpoints, key=lambda e: e.name):
                lines.append(
                    f"| {ep.name} | {ep.request_count} | {ep.qps:.2f} | "
                    f"{ep.avg_latency_ms:.1f} | {ep.error_rate_pct:.2f}% |"
                )
        else:
            lines.append("| (无数据) | - | - | - | - |")

    lines.extend(
        [
            "",
            "## 运行方式",
            "",
            "```bash",
            "cd backend",
            "pip install -r requirements-loadtest.txt",
            "",
            "# Mock（内置轻量 API，无需 LLM）",
            "python -m loadtest.run_stress --mock --quick",
            "",
            "# Live（需 API 运行于 8001）",
            "python -m loadtest.run_stress --host http://127.0.0.1:8001",
            "```",
            "",
            "原始 CSV：`loadtest/results/` · 报告：`artifacts/stress_test_report.md`",
            "",
        ]
    )

    if mock_mode:
        lines.append("> **Note:** 本次使用 Mock API，延迟为合成值，仅供 CI / 布局验证。")
        lines.append("")

    return "\n".join(lines) + "\n"


def csv_path_for_scenario(results_dir: Path, scenario_id: str) -> Path:
    return results_dir / f"stress_{scenario_id}_stats.csv"
