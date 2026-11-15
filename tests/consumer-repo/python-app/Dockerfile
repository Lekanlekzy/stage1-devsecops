FROM python:3.12-slim

RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    PORT=8080

ARG APP_REVISION=local
ENV APP_REVISION=$APP_REVISION

WORKDIR /app
COPY src ./src

USER 10001:10001
EXPOSE 8080
CMD ["python", "-m", "regression_consumer.server"]
