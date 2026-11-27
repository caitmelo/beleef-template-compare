FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TEMPLATE_COMPARE_ORIGINAL=/app/original \
    PORT=8000

COPY pyproject.toml README.md ./
COPY template_compare ./template_compare
COPY original ./original

RUN pip install --no-cache-dir .

EXPOSE 8000

# Render, and any other host that sets PORT, must be bound on all interfaces.
CMD ["sh", "-c", "uvicorn template_compare.api:app --host 0.0.0.0 --port ${PORT:-8000}"]
