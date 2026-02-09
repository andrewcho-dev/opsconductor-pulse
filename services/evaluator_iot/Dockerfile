FROM python:3.12-slim
WORKDIR /app
COPY evaluator_iot/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY evaluator_iot/evaluator.py .
COPY shared/ ./shared/
ENV PYTHONUNBUFFERED=1
CMD ["python", "/app/evaluator.py"]
