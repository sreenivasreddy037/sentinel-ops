# syntax=docker/dockerfile:1.7
FROM ghcr.io/astral-sh/uv:0.9.11 AS uv
FROM python:3.12-slim AS builder
COPY --from=uv /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/opt/venv
WORKDIR /build
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev --no-install-project

FROM python:3.12-slim AS runtime
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 libstdc++6 \
    && rm -rf /var/lib/apt/lists/*
RUN groupadd --gid 10001 sentinel && useradd --uid 10001 --gid sentinel --create-home sentinel
WORKDIR /srv/sentinel
COPY --from=builder /opt/venv /opt/venv
COPY --chown=10001:10001 app ./app
COPY --chown=10001:10001 data ./data
RUN mkdir -p /srv/sentinel/.sentinel /srv/sentinel/.cache && chown -R 10001:10001 /srv/sentinel
ENV PATH=/opt/venv/bin:$PATH PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    CHECKPOINT_PATH=/srv/sentinel/.sentinel/checkpoints.sqlite MODEL_CACHE=/srv/sentinel/.cache/models
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=45s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=3)"
# SQLite/local storage supports exactly one worker in this reference deployment.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log"]
