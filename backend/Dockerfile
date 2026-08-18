FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY backend ./backend
ENV UV_HTTP_TIMEOUT=180
RUN uv sync --project backend --frozen --no-dev

# Hugging Face Spaces runs containers as a non-root user with no writable
# $HOME, so point the HF cache (model downloads) somewhere the app can write.
ENV HF_HOME=/app/.cache/huggingface
RUN mkdir -p /app/.cache/huggingface && chmod -R 777 /app/.cache

EXPOSE 7860
CMD ["uv", "run", "--no-sync", "--project", "backend", "uvicorn", "vaaani.main:app", "--host", "0.0.0.0", "--port", "7860"]
