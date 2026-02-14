FROM python:3.12-slim
WORKDIR /app
COPY ops_worker/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY ops_worker/main.py /app/main.py
COPY ops_worker/health_monitor.py /app/health_monitor.py
COPY ops_worker/metrics_collector.py /app/metrics_collector.py
COPY ops_worker/workers /app/workers
COPY ops_worker/oncall /app/oncall
COPY ops_worker/notifications /app/notifications
COPY ops_worker/reports /app/reports
COPY ops_worker/db /app/db
COPY shared /app/shared
ENV PYTHONUNBUFFERED=1
CMD ["python", "/app/main.py"]
