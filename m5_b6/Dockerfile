# syntax=docker/dockerfile:1.7

# ========== STAGE 1: BUILDER ==========
FROM python:3.13-slim-bookworm AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

COPY --from=ghcr.io/astral-sh/uv:0.11.14 /uv /uvx /bin/

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

COPY app/ ./app/
COPY bot/ ./bot/
COPY migrations/ ./migrations/
COPY alembic.ini pyproject.toml uv.lock ./

ARG PHOENIX_ENABLED=false
RUN --mount=type=cache,target=/root/.cache/uv \
    if [ "$PHOENIX_ENABLED" = "true" ]; then \
        uv sync --frozen --no-dev --extra tracing; \
    else \
        uv sync --frozen --no-dev; \
    fi

# ========== STAGE 2: RUNTIME ==========
FROM python:3.13-slim-bookworm

RUN useradd --create-home --uid 1000 appuser

WORKDIR /app

COPY --from=builder --chown=appuser:appuser /app /app
COPY --chown=appuser:appuser data/rag-block-03/ ./data/rag-block-03/

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER appuser
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request,sys; \
sys.exit(0) if urllib.request.urlopen('http://localhost:8000/ready', timeout=3).status == 200 else sys.exit(1)" \
    || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
