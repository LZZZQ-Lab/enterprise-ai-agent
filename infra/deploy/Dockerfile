# Production API + Agent worker image (Task 4.7)
# Build context: repository root
#   docker build -f infra/deploy/Dockerfile .

FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DEFAULT_TIMEOUT=300

ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt \
     backend/requirements-knowledge.txt \
     /tmp/

RUN pip install --no-cache-dir --default-timeout=300 \
    -i "${PIP_INDEX_URL}" \
    -r /tmp/requirements.txt \
    -r /tmp/requirements-knowledge.txt \
    "redis>=5.0.0"

COPY backend/app /app/app
COPY backend/applications /app/applications
COPY apps /app/apps
COPY core /app/core
COPY llm /app/llm
COPY knowledge /app/knowledge
COPY infra/__init__.py /app/infra/__init__.py
COPY infra/monitoring /app/infra/monitoring

ENV PYTHONPATH=/app

RUN test -f /app/applications/dashboard/dashboard_service.py

EXPOSE 8001

HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8001/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
