# Backend API image (FastAPI). Build context: repository root.
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DEFAULT_TIMEOUT=300

# 国内构建易超时，默认清华源；海外可 --build-arg PIP_INDEX_URL=https://pypi.org/simple
ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --default-timeout=300 \
    -i "${PIP_INDEX_URL}" \
    -r /tmp/requirements.txt

COPY backend/app /app/app
COPY backend/applications /app/applications
COPY backend/security /app/security
COPY backend/observability /app/observability
COPY apps /app/apps
COPY core /app/core
COPY llm /app/llm
COPY knowledge /app/knowledge
COPY infra/__init__.py /app/infra/__init__.py
COPY infra/monitoring /app/infra/monitoring

ENV PYTHONPATH=/app

# 构建期校验（避免仅 COPY app 导致运行时 ModuleNotFoundError）
RUN test -f /app/applications/dashboard/dashboard_service.py \
    && test -f /app/security/auth.py \
    && python -c "import app.main"

EXPOSE 8001

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8001/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
