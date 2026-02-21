# 139-002: Grafana Deployment

## Task
Add Grafana service to docker-compose with Prometheus as the default datasource.

## Files to Create

### 1. compose/grafana/provisioning/datasources/prometheus.yml

```yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false
    jsonData:
      timeInterval: "15s"
      httpMethod: POST
```

### 2. compose/grafana/provisioning/dashboards/dashboards.yml

```yaml
apiVersion: 1

providers:
  - name: "OpsConductor Pulse"
    orgId: 1
    folder: "OpsConductor Pulse"
    type: file
    disableDeletion: false
    editable: true
    updateIntervalSeconds: 30
    allowUiUpdates: true
    options:
      path: /var/lib/grafana/dashboards
      foldersFromFilesStructure: false
```

### 3. compose/docker-compose.yml — Add grafana service

```yaml
  grafana:
    image: grafana/grafana:10.4.1
    container_name: pulse-grafana
    volumes:
      - ./grafana/provisioning:/etc/grafana/provisioning:ro
      - ./grafana/dashboards:/var/lib/grafana/dashboards:ro
      - grafana_data:/var/lib/grafana
    environment:
      GF_SECURITY_ADMIN_USER: ${GRAFANA_ADMIN_USER:-admin}
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_ADMIN_PASSWORD:-admin}
      GF_USERS_ALLOW_SIGN_UP: "false"
      GF_SERVER_HTTP_PORT: "3001"
      GF_SERVER_ROOT_URL: "http://localhost:3001"
      GF_DASHBOARDS_DEFAULT_HOME_DASHBOARD_PATH: /var/lib/grafana/dashboards/api-overview.json
    ports:
      - "${GRAFANA_PORT:-3001}:3001"
    depends_on:
      - prometheus
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:3001/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
    networks:
      - default
```

**Note**: Use port 3001 to avoid conflict with the frontend dev server (usually 3000) or any other service on 3000.

### 4. Create Dashboard Directory
Create `compose/grafana/dashboards/` directory. Dashboard JSON files will be added in 139-003.

### 5. Update .env.example
Add to `compose/.env.example`:
```
# Observability
PROMETHEUS_PORT=9090
GRAFANA_PORT=3001
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=admin
```

## Directory Structure After
```
compose/
├── grafana/
│   ├── provisioning/
│   │   ├── datasources/
│   │   │   └── prometheus.yml
│   │   └── dashboards/
│   │       └── dashboards.yml
│   └── dashboards/
│       └── (JSON files added in 139-003)
├── prometheus/
│   ├── prometheus.yml
│   └── alert_rules.yml
└── docker-compose.yml
```

## Verification
```bash
docker compose up -d grafana prometheus
# Wait for startup
curl http://localhost:3001/api/health
# Should return: {"commit":"...","database":"ok","version":"10.4.1"}
```

Open http://localhost:3001 in browser:
- Login with admin/admin (or configured credentials)
- Go to Connections → Data Sources → Prometheus should be listed and working
- Click "Test" on Prometheus datasource → should show "Data source is working"
