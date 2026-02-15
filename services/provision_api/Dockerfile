FROM python:3.12-slim

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends mosquitto && rm -rf /var/lib/apt/lists/*
COPY provision_api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY provision_api/app.py /app/app.py
COPY shared/ /app/shared/

EXPOSE 8081
ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8081"]
