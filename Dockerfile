FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc build-essential && rm -rf /var/lib/apt/lists/*

RUN pip install poetry

COPY pyproject.toml poetry.lock* config.yaml README.md ./
COPY nutalert/ nutalert/

RUN poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi

EXPOSE 3493

CMD ["python", "nutalert/processor.py"]
