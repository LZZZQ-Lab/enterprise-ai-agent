"""
Task 4.7：Agent Worker 进程（Redis 就绪探针 + 预留任务队列）。

与 API 容器分离部署，便于企业环境水平扩展 Agent 算力。
"""

from __future__ import annotations

import logging
import os
import signal
import sys
import time

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger("enterprise.agent.worker")

_running = True


def _handle_stop(_signum, _frame) -> None:

    global _running
    _running = False


def _ping_redis(redis_url: str) -> None:

    import redis

    client = redis.from_url(
        redis_url,
        decode_responses=True,
    )

    client.ping()
    client.set(
        "agent:worker:ready",
        str(int(time.time())),
        ex=60,
    )


def main() -> None:

    signal.signal(signal.SIGTERM, _handle_stop)
    signal.signal(signal.SIGINT, _handle_stop)

    redis_url = os.getenv(
        "REDIS_URL",
        "redis://redis:6379/0",
    )

    log.info("Agent worker starting redis=%s", redis_url)

    while _running:

        try:

            _ping_redis(redis_url)
            log.info("Agent worker heartbeat ok")

        except Exception as error:

            log.warning("Redis not ready: %s", error)

        for _ in range(10):

            if not _running:

                break

            time.sleep(1)

    log.info("Agent worker stopped")


if __name__ == "__main__":

    main()
    sys.exit(0)
