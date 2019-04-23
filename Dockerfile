FROM python:3.6.8-stretch
ENV PYTHONDONTWRITEBYTECODE 1

MAINTAINER Victor Ng <vng@mozilla.com>
EXPOSE 8000

# add a non-privileged user for installing and running
# the application
RUN groupadd --gid 10001 app && \
    useradd --uid 10001 --gid 10001 --home /app --create-home app 

RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential gettext curl \
                                               libopenblas-dev libatlas3-base gfortran && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Upgrade pip
RUN pip install --upgrade pip

# First copy requirements.txt so we can take advantage of docker
# caching.
COPY requirements.txt /app/requirements.txt
COPY prod-requirements.txt /app/prod-requirements.txt
RUN cat requirements.txt prod-requirements.txt > docker-requirements.txt
RUN pip install --no-cache-dir -r docker-requirements.txt

COPY . /app
RUN python setup.py install
USER app


# Using /bin/bash as the entrypoint works around some volume mount issues on Windows
# where volume-mounted files do not have execute bits set.
# https://github.com/docker/compose/issues/2301#issuecomment-154450785 has additional background.
ENTRYPOINT ["/bin/bash", "/app/bin/run"]

# bin/run supports web|web-dev|test options
CMD ["web"]
