FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY foresight ./foresight

EXPOSE 10000
CMD ["sh", "-c", "uv run uvicorn foresight.app:app --host 0.0.0.0 --port ${PORT:-10000}"]
