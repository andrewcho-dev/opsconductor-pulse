FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY dispatcher.py .
ENV PYTHONUNBUFFERED=1
CMD ["python", "/app/dispatcher.py"]
