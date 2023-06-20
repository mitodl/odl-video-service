FROM node:16.15.0 as node
ENV NODE_ENV=production
RUN apt-get update && apt-get install libelf1 -y
COPY . /src
WORKDIR /src
RUN yarn install --frozen-lockfile --ignore-engines --prefer-offline && \
    node node_modules/webpack/bin/webpack.js --config  webpack.config.prod.js --bail

FROM python:3.9-bullseye AS base
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

# Install pip
RUN curl --silent --location https://bootstrap.pypa.io/get-pip.py | python3 -


# Add, and run as, non-root user.
RUN mkdir /src
RUN adduser --disabled-password --gecos "" mitodl
RUN mkdir /var/media && chown -R mitodl:mitodl /var/media

# Add project
COPY . /src
WORKDIR /src


# Install poetry
ENV POETRY_VERSION=1.5.1
ENV POETRY_HOME=/opt/poetry
ENV POETRY_VENV=/opt/poetry-venv

# Tell Poetry where to place its cache and virtual environment
ENV POETRY_CACHE_DIR=/opt/.cache

# Creating a virtual environment just for poetry and install it with pip
RUN python3 -m venv $POETRY_VENV \
    && $POETRY_VENV/bin/pip install -U pip setuptools \
    && $POETRY_VENV/bin/pip install poetry==${POETRY_VERSION}


# Add Poetry to PATH
ENV PATH="${PATH}:${POETRY_VENV}/bin"

# Install project packages
RUN poetry install --no-dev


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

# Second stage build installs reqs needed only for develoment envs
# Invoke 'requirements.txt' again because 'test_requirements.txt' doesn't
# like to run alone for some reasont
FROM base AS development
USER root
RUN poetry install

