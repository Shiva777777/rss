# ─── Base image ───────────────────────────────────────────
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# ─── Dependencies ─────────────────────────────────────────
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# ─── Application ──────────────────────────────────────────
COPY . .

# Create non-root user
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
USER appuser

EXPOSE 8000

# Wait for DB, seed admin, then start the server
CMD ["sh", "-c", "python -m app.wait_for_db && python -m app.seed && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
