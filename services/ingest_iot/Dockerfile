FROM python:3.12-slim
WORKDIR /app
COPY ingest_iot/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY ingest_iot/ingest.py /app/ingest.py
COPY ingest_iot/topic_matcher.py /app/topic_matcher.py
COPY shared /app/shared
ENV PYTHONUNBUFFERED=1
CMD ["python", "/app/ingest.py"]
