# syntax=docker/dockerfile:1
FROM python:3.11-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --upgrade pip --no-cache-dir \
    && pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.11-slim
RUN addgroup --system appgroup \
    && adduser --system --ingroup appgroup --no-create-home appuser
WORKDIR /app
COPY --from=builder /install /usr/local
COPY . .
USER appuser
HEALTHCHECK --interval=20s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "\
import redis, os; \
r = redis.Redis(\
    host=os.getenv('REDIS_HOST','redis'), \
    port=int(os.getenv('REDIS_PORT', 6379)), \
    password=os.getenv('REDIS_PASSWORD') or None, \
    socket_connect_timeout=3, \
    socket_timeout=3\
); \
r.ping()" || exit 1

CMD ["python3", "worker.py"]