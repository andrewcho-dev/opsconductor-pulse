FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py /app/app.py
COPY metrics_collector.py /app/metrics_collector.py
COPY ws_manager.py /app/ws_manager.py
COPY middleware /app/middleware
COPY db /app/db
COPY routes /app/routes
COPY schemas /app/schemas
COPY services /app/services
COPY utils /app/utils

EXPOSE 8080
ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
