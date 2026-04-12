FROM python:3.14-alpine

WORKDIR /app

VOLUME [ "/data", "/etc/letsencrypt" ]

ENV PORT=8080
ENV HOST=localhost:8080
ENV DATA_DIR=/data
ENV MAX_SIZE=2000000
ENV BIND=0.0.0.0
ENV CERTBOT_CONF=/etc/letsencrypt
ENV CERTBOT_WWW=/data/.certbot
ENV SELF_SIGNED_PATH=/data/.certificates

RUN apk add --no-cache \
    openssl \
    certbot

RUN PIP_ROOT_USER_ACTION=ignore python3 -m pip install uv

COPY uv.lock pyproject.toml ./

RUN uv sync --no-dev

COPY main.py favicon.ico ./
COPY src ./src/

ENTRYPOINT [ "uv", "run", "--no-sync", "main.py"]