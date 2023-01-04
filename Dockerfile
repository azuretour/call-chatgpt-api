# syntax=docker/dockerfile:1.3-labs
###########
# BASE #
###########
FROM python:3.11-slim-bullseye as base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN pip install --upgrade --no-cache-dir pip

###########
# BUILDER #
###########
FROM base as builder
WORKDIR /app
COPY ./app/requirements.txt .

RUN --mount=type=cache,target=/root/.cache \
  pip install --no-warn-script-location -r requirements.txt

#########
# FINAL #
#########
FROM base as final

ENV PYTHONPATH=/usr/local/lib/python3.11/site-packages \
    PATH="/usr/local/bin:${PATH}" \
    HOME=/home/app

RUN <<EOF
    mkdir -p /home/app
    addgroup --system app && adduser --system --group app \
EOF

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
  --mount=type=cache,target=/var/lib/apt,sharing=locked \
    <<EOF
    apt-get -y update --allow-releaseinfo-change && apt-get install -y --no-install-recommends build-essential g++ unixodbc-dev gnupg curl
    curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
    curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list
    apt-get update && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 mssql-tools18
    apt-get clean
    rm -rf /var/lib/apt/lists/*
    echo "export PATH='$PATH:/opt/mssql-tools18/bin'" >> ~/.bashrc && . ~/.bashrc
EOF

WORKDIR $HOME

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY ./app ./app

RUN chmod 755 ./app/entrypoint.sh

USER app

EXPOSE 8000

CMD ["./app/entrypoint.sh"]