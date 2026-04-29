FROM python:3.12-slim

WORKDIR /app

# Install uv for fast dependency resolution
RUN pip install uv

# Copy dependency files
COPY pyproject.toml .
COPY src/ src/
COPY config/ config/
COPY scripts/ scripts/

# Install dependencies
RUN uv pip install --system -e ".[dev]"

# Create data directory
RUN mkdir -p data/aegis

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/v1/health || exit 1

CMD ["uvicorn", "aegis.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
