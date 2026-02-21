# Add Docker Healthchecks to Backend Services

Add healthcheck definitions to docker-compose.yml for automatic health monitoring and restart.

## File to Modify

`compose/docker-compose.yml`

## Services to Add Healthchecks

For each of these services, add a healthcheck block:

### 1. evaluator service

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 10s
```

### 2. dispatcher service

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 10s
```

### 3. delivery_worker service

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 10s
```

## Verification

After adding healthchecks, each service needs a `/health` endpoint. Check if the services already have one:
- If yes, the healthcheck will work
- If no, a simple `/health` endpoint returning 200 OK needs to be added to each service

## Notes

- The `restart: unless-stopped` policy already exists, so Docker will restart unhealthy containers
- `start_period` gives the service time to initialize before health checks begin
- 3 retries with 30s interval means a service must fail for ~90s before being marked unhealthy
