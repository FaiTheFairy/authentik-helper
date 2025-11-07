# syntax=docker/dockerfile:1

# builder: create a project-local venv with uv
FROM python:3.11-slim AS builder
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/app/.venv
WORKDIR /app

# uv lives in the global interpreter
RUN python -m pip install --no-cache-dir --upgrade pip uv

# 1) lockfile + metadata first (cacheable)
COPY pyproject.toml uv.lock ./

# 2) resolve & build the venv WITHOUT installing the local project (and no dev)
RUN uv sync --frozen --no-dev --no-install-project

# 3) bring in the application code
COPY tools ./tools
COPY app.py ./
COPY core ./core
COPY routers ./routers
COPY services ./services
COPY web ./web
COPY README.md ./README.md

# 4) now install the local project into the existing venv (still no dev extras)
#    Note: use uv again, *not* pip-in-venv (pip isn’t present in the uv venv).
RUN uv sync --frozen --no-dev

# runtime: distroless, nonroot 
FROM gcr.io/distroless/python3-debian12:nonroot AS runtime
WORKDIR /app

# copy app + venv
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/app.py /app/
COPY --from=builder /app/tools /app/tools
COPY --from=builder /app/core /app/core
COPY --from=builder /app/routers /app/routers
COPY --from=builder /app/services /app/services
COPY --from=builder /app/web /app/web
COPY --from=builder /app/README.md /app/README.md

# build metadata (version/commit/date)
ARG BUILD_VERSION=0unknown
ARG BUILD_COMMIT=unknown
ARG BUILD_DATE
ENV BUILD_VERSION=${BUILD_VERSION} \
    BUILD_COMMIT=${BUILD_COMMIT} \
    BUILD_DATE=${BUILD_DATE}

# point python at deps in the venv
ENV PYTHONPATH="/app/.venv/lib/python3.11/site-packages" \
    BIND_HOST=0.0.0.0 \
    BIND_PORT=8000 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000
ENTRYPOINT ["/usr/bin/python3"]
CMD ["-m", "uvicorn", "app:app", "--host","0.0.0.0","--port","8000"]
