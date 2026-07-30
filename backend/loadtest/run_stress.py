"""Task 8.4: orchestrate Locust stress scenarios and emit stress_test_report.md."""

from __future__ import annotations

import argparse
import contextlib
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import uvicorn

from loadtest.report_builder import STRESS_REPORT
from loadtest.report_builder import ScenarioSummary
from loadtest.report_builder import build_stress_report
from loadtest.report_builder import csv_path_for_scenario
from loadtest.report_builder import summarize_scenario
from loadtest.scenarios import StressScenario
from loadtest.scenarios import get_scenarios

LOADTEST_ROOT = Path(__file__).resolve().parent
BACKEND_ROOT = LOADTEST_ROOT.parent
RESULTS_DIR = LOADTEST_ROOT / "results"
LOCUSTFILE = LOADTEST_ROOT / "locustfile.py"


def _now_iso() -> str:
    from datetime import datetime
    from datetime import timezone

    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


@contextlib.contextmanager
def _mock_api_server(host: str, port: int):
    config = uvicorn.Config(
        "loadtest.mock_api:app",
        host=host,
        port=port,
        log_level="warning",
        access_log=False,
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    deadline = time.time() + 15
    while not server.started and time.time() < deadline:
        time.sleep(0.05)
    if not server.started:
        raise RuntimeError("Mock API failed to start")
    time.sleep(0.5)

    try:
        yield f"http://{host}:{port}"
    finally:
        server.should_exit = True
        thread.join(timeout=5)


def _run_locust(
    *,
    host: str,
    scenario: StressScenario,
    csv_prefix: Path,
    quick: bool,
) -> int:
    csv_prefix.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["LOCUST_SCENARIO"] = scenario.id
    if scenario.max_requests:
        env["LOCUST_MAX_REQUESTS"] = str(scenario.max_requests)
        env["LOCUST_SHAPE_USERS"] = str(scenario.users)
        env["LOCUST_SHAPE_SPAWN_RATE"] = str(scenario.spawn_rate)

    cmd = [
        sys.executable,
        "-m",
        "locust",
        "-f",
        str(LOCUSTFILE),
        "--headless",
        "--host",
        host,
        "-u",
        str(scenario.users),
        "-r",
        str(scenario.spawn_rate),
        "--csv",
        str(csv_prefix),
        "--only-summary",
    ]
    if scenario.run_time:
        run_time = scenario.run_time if not quick else "8s"
        cmd.extend(["-t", run_time])
    elif not scenario.max_requests:
        cmd.extend(["-t", "30s"])

    print(f"\n>>> Locust [{scenario.id}] {' '.join(cmd[4:])}")
    proc = subprocess.run(
        cmd,
        cwd=str(BACKEND_ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    if proc.stdout:
        print(proc.stdout)
    if proc.returncode != 0 and proc.stderr:
        print(proc.stderr, file=sys.stderr)
    return proc.returncode


def run_all(
    *,
    host: str,
    mock: bool,
    quick: bool,
    results_dir: Path,
    report_path: Path,
) -> int:
    scenarios = get_scenarios(quick=quick)
    summaries: list[ScenarioSummary] = []
    mock_ctx = None

    if mock:
        mock_host = "127.0.0.1"
        mock_port = int(os.getenv("MOCK_API_PORT", "18081"))
        mock_ctx = _mock_api_server(mock_host, mock_port)
        host = mock_ctx.__enter__()

    try:
        for scenario in scenarios:
            csv_prefix = results_dir / f"stress_{scenario.id}"
            rc = _run_locust(
                host=host,
                scenario=scenario,
                csv_prefix=csv_prefix,
                quick=quick,
            )
            if rc != 0:
                print(f"WARNING: Locust exited {rc} for {scenario.id}", file=sys.stderr)

            stats_csv = csv_path_for_scenario(results_dir, scenario.id)
            summaries.append(summarize_scenario(scenario, stats_csv))
    finally:
        if mock_ctx is not None:
            mock_ctx.__exit__(None, None, None)

    report = build_stress_report(
        summaries,
        host=host,
        mock_mode=mock,
        generated_at=_now_iso(),
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    print(f"\nReport: {report_path}")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Task 8.4 Locust stress test runner")
    parser.add_argument(
        "--host",
        default=os.getenv("LOCUST_HOST", "http://127.0.0.1:8001"),
        help="Target API base URL",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Start built-in mock API (no LLM required)",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Short scenarios for CI / smoke",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=RESULTS_DIR,
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=STRESS_REPORT,
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return run_all(
        host=args.host.rstrip("/"),
        mock=args.mock,
        quick=args.quick,
        results_dir=args.results_dir,
        report_path=args.report,
    )


if __name__ == "__main__":
    raise SystemExit(main())
