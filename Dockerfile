FROM python:3.14-alpine

WORKDIR /app

VOLUME [ "/data" ]

ENV HOST=localhost
ENV PORT=8080
ENV BIND=0.0.0.0
ENV DATA_DIR=/data
ENV MAX_SIZE=2000000

RUN PIP_ROOT_USER_ACTION=ignore python3 -m pip install uv

COPY uv.lock pyproject.toml ./

RUN uv sync --no-dev

COPY main.py ./
COPY src ./src/

ENTRYPOINT [ "uv", "run", "--no-sync", "main.py" ]