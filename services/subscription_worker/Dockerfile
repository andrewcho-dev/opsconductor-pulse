FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir asyncpg httpx

COPY worker.py .

CMD ["python", "worker.py"]
FROM python:3.11-slim

WORKDIR /app

RUN pip install asyncpg

COPY worker.py .

CMD ["python", "worker.py"]
