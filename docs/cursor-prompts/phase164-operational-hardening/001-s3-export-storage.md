# Task 1: S3/MinIO Export Storage

## Files to Modify

- `services/ops_worker/workers/export_worker.py`
- `services/ui_iot/routes/exports.py` (download endpoint)
- `compose/docker-compose.yml` (add MinIO for local dev)

## What to Do

Replace the local filesystem volume (`/tmp/pulse-exports`) with S3-compatible object storage. Use MinIO for local development and S3/GCS/Azure Blob in production.

### Step 1: Add MinIO to docker-compose (local dev)

```yaml
  minio:
    image: minio/minio:latest
    container_name: iot-minio
    command: server /data --console-address ":9090"
    environment:
      MINIO_ROOT_USER: "${MINIO_ROOT_USER:-minioadmin}"
      MINIO_ROOT_PASSWORD: "${MINIO_ROOT_PASSWORD:-minioadmin}"
    ports:
      - "127.0.0.1:9000:9000"   # S3 API
      - "127.0.0.1:9090:9090"   # Console
    volumes:
      - minio-data:/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 10s
      timeout: 5s
      retries: 3
    restart: unless-stopped
```

Add a bucket init container:

```yaml
  minio-init:
    image: minio/mc:latest
    container_name: iot-minio-init
    entrypoint: >
      /bin/sh -c "
      mc alias set pulse http://iot-minio:9000 minioadmin minioadmin;
      mc mb --ignore-existing pulse/exports;
      mc mb --ignore-existing pulse/reports;
      "
    depends_on:
      minio:
        condition: service_healthy
    restart: "no"
```

### Step 2: Refactor export_worker to use boto3/s3

Replace file writes with S3 uploads:

```python
import boto3
from botocore.config import Config

S3_ENDPOINT = os.getenv("S3_ENDPOINT", "http://iot-minio:9000")
S3_BUCKET = os.getenv("S3_BUCKET", "exports")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "minioadmin")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "minioadmin")
S3_REGION = os.getenv("S3_REGION", "us-east-1")

def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        region_name=S3_REGION,
        config=Config(signature_version="s3v4"),
    )
```

- Upload export file to `s3://{bucket}/{export_id}.{format}`
- Store the S3 key in the export job record (not the local file path)
- Delete the local temp file after upload

### Step 3: Refactor download endpoint to use pre-signed URLs

Instead of `FileResponse(file_path)`, generate a pre-signed S3 URL:

```python
url = s3.generate_presigned_url(
    "get_object",
    Params={"Bucket": S3_BUCKET, "Key": s3_key},
    ExpiresIn=3600,  # 1 hour
)
return RedirectResponse(url)
```

### Step 4: Add env vars to docker-compose

```yaml
  ops_worker:
    environment:
      S3_ENDPOINT: "http://iot-minio:9000"
      S3_BUCKET: "exports"
      S3_ACCESS_KEY: "${MINIO_ROOT_USER:-minioadmin}"
      S3_SECRET_KEY: "${MINIO_ROOT_PASSWORD:-minioadmin}"
  ui:
    environment:
      S3_ENDPOINT: "http://iot-minio:9000"
      S3_BUCKET: "exports"
      S3_ACCESS_KEY: "${MINIO_ROOT_USER:-minioadmin}"
      S3_SECRET_KEY: "${MINIO_ROOT_PASSWORD:-minioadmin}"
```

For production (AWS S3): remove `S3_ENDPOINT` (use default AWS endpoint), set real credentials via IAM role or K8s secret.

### Step 5: Add boto3 to requirements

Add `boto3` to `services/ops_worker/requirements.txt` and `services/ui_iot/requirements.txt`.

## Important Notes

- **MinIO is S3-compatible** — same API, same SDK (boto3). Code works identically with AWS S3, GCS (via S3 compat), or Azure Blob (via S3 compat).
- **Pre-signed URLs** avoid proxying large files through the API server. The client downloads directly from S3/MinIO.
- **Cleanup:** The export cleanup worker should delete from S3 instead of the local filesystem.
- **Remove the `export-data` volume** from docker-compose after migration.
