# 139-001: Prometheus Deployment

## Task
Add Prometheus service to docker-compose and create scrape configuration.

## Files to Create

### 1. compose/prometheus/prometheus.yml

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - /etc/prometheus/alert_rules.yml

scrape_configs:
  - job_name: "ui_iot"
    static_configs:
      - targets: ["ui:8081"]
    metrics_path: /metrics
    scrape_interval: 15s

  - job_name: "ingest_iot"
    static_configs:
      - targets: ["ingest:8082"]
    metrics_path: /metrics
    scrape_interval: 15s

  - job_name: "evaluator_iot"
    static_configs:
      - targets: ["evaluator:8083"]
    metrics_path: /metrics
    scrape_interval: 15s

  - job_name: "ops_worker"
    static_configs:
      - targets: ["ops_worker:8080"]
    metrics_path: /metrics
    scrape_interval: 15s

  - job_name: "subscription_worker"
    static_configs:
      - targets: ["subscription-worker:8080"]
    metrics_path: /metrics
    scrape_interval: 30s

  - job_name: "prometheus"
    static_configs:
      - targets: ["localhost:9090"]
```

**Important**: Verify the actual service names and ports by reading `compose/docker-compose.yml`. The service names in `static_configs.targets` must match the docker-compose service names (which become hostnames in the Docker network). Check each service's exposed metrics port:
- `ui` service may expose metrics on a different port than the main API
- `ingest` service uses aiohttp on a specific port
- `evaluator` service exposes metrics on its own port
- `ops_worker` uses `prometheus_client.start_http_server(8080)`

### 2. compose/docker-compose.yml — Add prometheus service

Add after the existing services (before or after the `seed` service):

```yaml
  prometheus:
    image: prom/prometheus:v2.51.0
    container_name: pulse-prometheus
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - ./prometheus/alert_rules.yml:/etc/prometheus/alert_rules.yml:ro
      - prometheus_data:/prometheus
    command:
      - "--config.file=/etc/prometheus/prometheus.yml"
      - "--storage.tsdb.retention.time=15d"
      - "--web.enable-lifecycle"
      - "--web.console.libraries=/etc/prometheus/console_libraries"
      - "--web.console.templates=/etc/prometheus/consoles"
    ports:
      - "${PROMETHEUS_PORT:-9090}:9090"
    depends_on:
      - ui
      - ingest
      - evaluator
      - ops_worker
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:9090/-/healthy"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
    networks:
      - default
```

Also add the volume at the bottom of the compose file in the `volumes:` section:
```yaml
volumes:
  # ... existing volumes
  prometheus_data:
  grafana_data:
```

### 3. Create placeholder alert_rules.yml
Create `compose/prometheus/alert_rules.yml` with an empty groups list (will be populated in 139-004):
```yaml
groups: []
```

## Port Verification
Before finalizing the scrape config, verify each service's metrics port by reading:
1. `compose/docker-compose.yml` — check each service's exposed ports
2. `services/ui_iot/app.py` — look for prometheus metrics handler mount
3. `services/ingest_iot/ingest.py` — look for the aiohttp web server port for metrics
4. `services/evaluator_iot/evaluator.py` — look for metrics handler
5. `services/ops_worker/main.py` — line 105: `start_http_server(8080)`

Update the scrape config targets with the correct ports.

## Verification
```bash
docker compose up -d prometheus
curl http://localhost:9090/api/v1/targets | python3 -m json.tool
# All targets should show state: "up"
curl http://localhost:9090/-/healthy
# Should return "Prometheus Server is Healthy."
```
