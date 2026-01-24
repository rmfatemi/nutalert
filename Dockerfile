FROM python:3.11-alpine AS builder

RUN apk add --no-cache build-base

WORKDIR /app

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY nutalert/ nutalert/
COPY assets/ assets/
COPY README.md pyproject.toml ./

FROM python:3.11-alpine

WORKDIR /app

RUN apk add --no-cache curl

RUN addgroup -S appgroup && adduser -S appuser -G appgroup

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /app/nutalert ./nutalert
COPY --from=builder /app/assets ./assets
COPY --from=builder /app/README.md .
COPY --from=builder /app/pyproject.toml .

RUN mkdir /config && chown appuser:appgroup /config
VOLUME /config

EXPOSE 3493
EXPOSE 8087

ENV CONFIG_PATH=/config/config.yaml

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD curl -s http://localhost:8087/health | grep -qE '"status":\s*"(healthy|degraded)"' || exit 1

CMD ["python", "-m", "nutalert.app"]
