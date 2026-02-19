FROM python:3.12-slim
WORKDIR /app
COPY route_delivery/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY route_delivery/ .
CMD ["python", "delivery.py"]

