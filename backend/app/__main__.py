"""
应用入口：支持 python -m app.main 启动。

等价于：
    cd backend
    python -m uvicorn app.main:app --host 0.0.0.0 --port 8001
"""

from __future__ import annotations

import os

import uvicorn

from app.config import settings


def main() -> None:

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )


if __name__ == "__main__":

    main()
