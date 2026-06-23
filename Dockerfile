FROM node:24.16.0@sha256:9c1d881a5b3354362cd134d15b6eee789313833caa720c3cb6ea8862925d6eb8 AS node
ENV NODE_ENV=production
RUN apt-get update && apt-get install libelf1 -y
COPY . /src
WORKDIR /src
RUN yarn install --frozen-lockfile --ignore-engines --prefer-offline && \
    yarn build && \
    node node_modules/webpack/bin/webpack.js --config  webpack.config.prod.js --bail

FROM python:3.13.6-bullseye@sha256:f58f33e0563f2ba81c7afe6259cd912f0c33413da93c75cc3a70a941c17afa8c AS base
# Add package files, install updated node and pip
WORKDIR /tmp

# Install packages
COPY apt.txt /tmp/apt.txt
RUN apt-get update && \
    apt-get install -y $(grep -vE "^\s*#" apt.txt  | tr "\n" " ") && \
    apt-get update && \
    apt-get install libpq-dev postgresql-client -y && \
    apt-get clean && \
    apt-get purge

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest@sha256:99ea34acedc870ba4ad11a1f540a1c04267c9f30aadc465a94406f52dfda2c36 /uv /uvx /usr/local/bin/

# Add, and run as, non-root user.
RUN mkdir /src
RUN adduser --disabled-password --gecos "" mitodl
RUN mkdir /var/media && chown -R mitodl:mitodl /var/media

ENV UV_PROJECT_ENVIRONMENT="/opt/venv"
ENV PATH="/opt/venv/bin:$PATH"

# Install project packages
COPY pyproject.toml /src
COPY uv.lock /src
WORKDIR /src
RUN uv sync --frozen --no-install-project --no-dev

# Add project
COPY . /src
RUN chown -R mitodl:mitodl /src
USER mitodl

EXPOSE 8089
ENV PORT 8089
CMD uwsgi uwsgi.ini

FROM base AS production
LABEL maintainer "ODL DevOps <mitx-devops@mit.edu>"
ENV DEBUG=False PYTHONUNBUFFERED=true
COPY --from=node --chown=mitodl:mitodl /src/static /src/static
COPY --from=node --chown=mitodl:mitodl /src/webpack-stats.json /src
USER mitodl

# Second stage build installs reqs needed only for development envs
FROM base AS development
USER root
RUN uv sync --frozen
USER mitodl
