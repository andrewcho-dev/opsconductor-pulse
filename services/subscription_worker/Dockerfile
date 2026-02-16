FROM python:3.11-slim

WORKDIR /app

COPY subscription_worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY subscription_worker/*.py ./
COPY shared/ ./shared/

CMD ["python", "/app/worker.py"]
