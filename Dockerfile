FROM node:22-slim AS web-build
WORKDIR /web
COPY web/package.json ./
RUN npm install
COPY web ./
RUN npm run build

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY quantmind ./quantmind
COPY --from=web-build /web/dist ./web-dist

EXPOSE 10000
CMD ["sh", "-c", "uv run uvicorn quantmind.app:app --host 0.0.0.0 --port ${PORT:-10000}"]
