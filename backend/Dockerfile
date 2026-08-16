FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY backend/pyproject.toml backend/uv.lock ./backend/
RUN uv sync --project backend --frozen --no-dev
COPY backend ./backend
EXPOSE 8000
CMD ["uv", "run", "--project", "backend", "uvicorn", "vaaani.main:app", "--host", "0.0.0.0", "--port", "8000"]
