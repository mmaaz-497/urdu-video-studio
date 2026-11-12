# syntax=docker/dockerfile:1
# Production image for the API, the RQ worker and the stale-job scheduler (same image,
# different `command:` in infra/docker-compose.prod.yml). Built on the dev machine by
# infra/deploy.sh and shipped to the VPS with `docker save | podman load` (T091).

ARG PYTHON_IMAGE=python:3.12-slim-bookworm

# ---- build: resolve dependencies into an isolated virtualenv ------------------------
FROM ${PYTHON_IMAGE} AS build
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH
WORKDIR /src
COPY pyproject.toml ./
# Install only the runtime dependencies listed in pyproject.toml (no dev extras); the
# app itself runs from source in the final stage, which keeps alembic/ next to it.
RUN python -c "import tomllib; print('\n'.join(tomllib.load(open('pyproject.toml','rb'))['project']['dependencies']))" > requirements.txt \
 && pip install -r requirements.txt

# ---- runtime -------------------------------------------------------------------------
FROM ${PYTHON_IMAGE} AS runtime
# ffmpeg lives in the final stage: the worker shells out to ffmpeg/ffprobe. tzdata for
# zoneinfo("Asia/Karachi") (daily-limit reset) and TZ-correct logs.
RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg tzdata \
 && rm -rf /var/lib/apt/lists/* \
 && groupadd --system --gid 10001 app \
 && useradd --system --uid 10001 --gid app --home-dir /app --shell /usr/sbin/nologin app

ENV PATH=/opt/venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Uvicorn: trust X-Forwarded-Proto/For from the proxy (Apache, or the Next.js
    # rewrite). Safe as "*" only because the API port is published on 127.0.0.1 and
    # the internal network is private to this stack — see infra/docker-compose.prod.yml.
    FORWARDED_ALLOW_IPS="*"

COPY --from=build /opt/venv /opt/venv
WORKDIR /app
COPY --chown=app:app alembic.ini ./
COPY --chown=app:app alembic ./alembic
COPY --chown=app:app app ./app

USER app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--proxy-headers", "--workers", "1", "--timeout-keep-alive", "75", "--no-server-header"]
