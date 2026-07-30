"""Task 8.4 stress test report builder tests."""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from loadtest.report_builder import CATEGORY_API  # noqa: E402
from loadtest.report_builder import CATEGORY_GATEWAY  # noqa: E402
from loadtest.report_builder import CATEGORY_WORKFLOW  # noqa: E402
from loadtest.report_builder import build_stress_report  # noqa: E402
from loadtest.report_builder import parse_locust_stats_csv  # noqa: E402
from loadtest.report_builder import summarize_scenario  # noqa: E402
from loadtest.scenarios import StressScenario  # noqa: E402


SAMPLE_CSV = """Type,Name,Request Count,Failure Count,Median Response Time,Average Response Time,Min Response Time,Max Response Time,Average Content Size,Requests/s,Failures/s,50%,66%,75%,80%,90%,95%,98%,99%,99.9%,99.99%,100%
GET,API GET /health,120,0,12,15.5,8,45,32,2.0,0.0,12,14,15,16,20,25,30,35,40,45,45
POST,API POST /api/v1/chat,40,2,850,920.0,600,1500,256,0.67,0.03,850,900,950,1000,1200,1400,1500,1500,1500,1500,1500
POST,Workflow POST /api/v1/dashboard/projects,30,0,200,210.0,150,400,128,0.5,0.0,200,210,220,230,300,350,400,400,400,400,400
GET,Workflow GET /api/v1/dashboard/workflow/{id},60,1,80,85.0,50,200,64,1.0,0.02,80,82,85,88,100,120,200,200,200,200,200
POST,Gateway POST /api/v1/inference/chat/completions,50,0,300,320.0,200,600,512,0.83,0.0,300,310,320,330,400,500,600,600,600,600,600
GET,Gateway GET /api/v1/inference/stats,20,0,10,12.0,5,25,48,0.33,0.0,10,11,12,13,15,20,25,25,25,25,25
,Aggregated,320,3,95,180.0,5,1500,200,5.33,0.05,80,120,200,300,850,920,1200,1400,1500,1500,1500
"""


def test_parse_locust_stats_csv(tmp_path: Path) -> None:
    csv_file = tmp_path / "stats.csv"
    csv_file.write_text(SAMPLE_CSV, encoding="utf-8")

    rows = parse_locust_stats_csv(csv_file)
    names = {r.name for r in rows}
    assert "API GET /health" in names
    assert "Aggregated" not in names
    assert len(rows) == 6

    api_rows = [r for r in rows if r.category == CATEGORY_API]
    assert len(api_rows) == 2
    assert api_rows[0].request_count == 120


def test_summarize_scenario(tmp_path: Path) -> None:
    csv_file = tmp_path / "stress_10_users_stats.csv"
    csv_file.write_text(SAMPLE_CSV, encoding="utf-8")
    scenario = StressScenario(
        id="10_users",
        label="10 并发用户",
        users=10,
        spawn_rate=2,
        run_time="60s",
    )
    summary = summarize_scenario(scenario, csv_file)
    assert summary.total_requests == 320
    assert summary.total_failures == 3
    assert summary.error_rate_pct > 0
    assert len(summary.endpoints) == 6


def test_build_stress_report_contains_categories() -> None:
    scenario = StressScenario(
        id="10_users",
        label="10 并发用户",
        users=10,
        spawn_rate=2,
        run_time="60s",
    )
    from loadtest.report_builder import EndpointStats
    from loadtest.report_builder import ScenarioSummary

    summary = ScenarioSummary(
        scenario=scenario,
        total_requests=100,
        total_failures=1,
        avg_latency_ms=50.0,
        qps=10.0,
        error_rate_pct=1.0,
        endpoints=[
            EndpointStats("API GET /health", CATEGORY_API, 50, 0, 10.0, 5.0, 0.0),
            EndpointStats(
                "Workflow POST /api/v1/dashboard/projects",
                CATEGORY_WORKFLOW,
                30,
                1,
                200.0,
                3.0,
                3.33,
            ),
            EndpointStats(
                "Gateway POST /api/v1/inference/chat/completions",
                CATEGORY_GATEWAY,
                20,
                0,
                300.0,
                2.0,
                0.0,
            ),
        ],
    )
    md = build_stress_report(
        [summary],
        host="http://127.0.0.1:8001",
        mock_mode=True,
        generated_at="2026-07-30T00:00:00+08:00",
    )
    assert "Task 8.4" in md
    assert CATEGORY_API in md
    assert CATEGORY_WORKFLOW in md
    assert CATEGORY_GATEWAY in md
    assert "QPS" in md
    assert "错误率" in md
