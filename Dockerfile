FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc build-essential && rm -rf /var/lib/apt/lists/*

RUN pip install poetry

RUN mkdir -p /config

COPY pyproject.toml poetry.lock* README.md ./
COPY nutalert/ nutalert/

RUN poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi

EXPOSE 3493

ENV CONFIG_PATH=/config/config.yaml

CMD ["python", "-m", "nutalert.processor"]
