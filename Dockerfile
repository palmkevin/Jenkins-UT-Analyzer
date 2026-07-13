# Single image, two roles (web / poller) — role selected by the compose `command`.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install deps first for layer caching.
COPY pyproject.toml ./
COPY src ./src
# Alembic config + migrations: `uta migrate` (run at container start) resolves alembic.ini as
# the repo root one level above src/ (cli.py `parents[2]`). Ship them and install editable so
# `uta`'s __file__ stays under /app/src, keeping that path valid inside the image.
COPY alembic.ini ./
COPY alembic ./alembic
RUN pip install --upgrade pip && pip install -e .

# tzdata so ZoneInfo("Europe/Luxembourg") resolves inside the slim image; subversion so the owner
# = main-developer lookup (issue #114) can shell out to `svn blame` — without it every blame
# silently returns None (missing binary is swallowed) and Owner never resolves (issue #166).
RUN apt-get update && apt-get install -y --no-install-recommends tzdata subversion \
    && rm -rf /var/lib/apt/lists/*

EXPOSE 8000

# Default role = web. The poller service overrides `command` in docker-compose.yml.
# --proxy-headers/--forwarded-allow-ips: trust Traefik's X-Forwarded-* so request.url_for builds
# the external https:// OIDC callback URL (TLS terminates at the proxy).
CMD ["sh", "-c", "uta init-db && uvicorn uta.web.app:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'"]
