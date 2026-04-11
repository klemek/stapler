FROM python:3.14-alpine

WORKDIR /app

VOLUME [ "/app/data" ]

RUN PIP_ROOT_USER_ACTION=ignore python3 -m pip install uv

COPY uv.lock pyproject.toml ./

RUN uv sync --no-dev

COPY main.py ./
COPY src ./src/

ENTRYPOINT [ "uv", "run", "--no-sync", "main.py" ]