"""Locust load shapes for fixed-request scenarios."""

from __future__ import annotations

import os

from locust import LoadTestShape


class StopAfterRequests(LoadTestShape):
    """Stop the test once total requests reach LOCUST_MAX_REQUESTS."""

    def tick(self):
        limit = int(os.getenv("LOCUST_MAX_REQUESTS", "1000"))
        users = int(os.getenv("LOCUST_SHAPE_USERS", "50"))
        spawn_rate = int(os.getenv("LOCUST_SHAPE_SPAWN_RATE", "10"))

        if self.runner.stats.total.num_requests >= limit:
            return None
        return users, spawn_rate
