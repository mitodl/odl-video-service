# syntax=docker/dockerfile:1
# hadolint global ignore=DL3008

# ─── Node / frontend asset build ─────────────────────────────────────────────
FROM node:24.14.0 AS node
ENV NODE_ENV=production
RUN apt-get update && apt-get install libelf1 -y --no-install-recommends
COPY . /src
WORKDIR /src
RUN yarn install --frozen-lockfile --ignore-engines --prefer-offline && \
    yarn build && \
    node node_modules/webpack/bin/webpack.js --config webpack.config.prod.js --bail

# ─── Python base ─────────────────────────────────────────────────────────────
FROM mitodl/ol-python-base:3.13 AS base
LABEL maintainer="ODL DevOps <mitx-devops@mit.edu>"

# odl-video-service has no app-specific apt extras; all required packages
# (including libpq-dev and postgresql-client) are in mitodl/ol-python-base:3.13.

# ─── Dependency install ───────────────────────────────────────────────────────
FROM base AS deps

COPY pyproject.toml uv.lock /src/
RUN chown mitodl:mitodl /src/pyproject.toml /src/uv.lock

USER mitodl
WORKDIR /src
# BuildKit cache mount keeps the uv download cache across builds.
RUN --mount=type=cache,target=/opt/uv-cache,uid=1000,gid=1000 \
    uv sync --frozen --no-install-project --no-dev

# ─── Runtime base ─────────────────────────────────────────────────────────────
FROM deps AS production
LABEL maintainer="ODL DevOps <mitx-devops@mit.edu>"
ENV DEBUG=False PYTHONUNBUFFERED=true

USER root
COPY . /src
RUN chown -R mitodl:mitodl /src

# Copy built frontend assets from the node stage.
COPY --from=node --chown=mitodl:mitodl /src/static /src/static
COPY --from=node --chown=mitodl:mitodl /src/webpack-stats.json /src

USER mitodl

EXPOSE 8089
ENV PORT=8089
CMD ["granian", "--interface", "wsgi", "--host", "0.0.0.0", "--port", "8089", "--workers", "2", "odl_video.wsgi:application"]

# ─── Development target ───────────────────────────────────────────────────────
FROM deps AS development

USER root
RUN --mount=type=cache,target=/opt/uv-cache,uid=1000,gid=1000 \
    uv sync --frozen
USER mitodl
