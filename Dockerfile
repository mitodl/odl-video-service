FROM python:3.9.13 AS production
LABEL maintainer "ODL DevOps <mitx-devops@mit.edu>"

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

# Install project packages
COPY requirements.txt /tmp/requirements.txt
RUN pip install -r requirements.txt

# Add project
COPY . /src
WORKDIR /src
RUN chown -R mitodl:mitodl /src

USER mitodl

# Set pip cache folder, as it is breaking pip when it is on a shared volume
ENV XDG_CACHE_HOME /tmp/.cache

EXPOSE 8089
ENV PORT 8089
CMD uwsgi uwsgi.ini

# Second stage build installs reqs needed only for develoment envs
# Invoke 'requirements.txt' again because 'test_requirements.txt' doesn't 
# like to run alone for some reason
FROM production AS development
COPY test_requirements.txt /tmp/test_requirements.txt
RUN pip install -r requirements.txt -r test_requirements.txt
