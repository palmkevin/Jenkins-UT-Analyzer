# Single image, two roles (web / poller) — role selected by the compose `command`.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install deps first for layer caching.
COPY pyproject.toml ./
COPY src ./src
RUN pip install --upgrade pip && pip install .

# tzdata so ZoneInfo("Europe/Luxembourg") resolves inside the slim image.
RUN apt-get update && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

EXPOSE 8000

# Default role = web. The poller service overrides `command` in docker-compose.yml.
CMD ["sh", "-c", "uta init-db && uvicorn uta.web.app:app --host 0.0.0.0 --port 8000"]
