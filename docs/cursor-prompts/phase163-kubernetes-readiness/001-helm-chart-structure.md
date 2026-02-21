# Task 1: Helm Chart Structure

## Files to Create

```
helm/pulse/
├── Chart.yaml
├── values.yaml
├── templates/
│   ├── _helpers.tpl
│   ├── ingest-deployment.yaml
│   ├── ingest-service.yaml
│   ├── ui-deployment.yaml
│   ├── ui-service.yaml
│   ├── evaluator-deployment.yaml
│   ├── ops-worker-deployment.yaml
│   ├── route-delivery-deployment.yaml
│   ├── subscription-worker-deployment.yaml
│   ├── provision-api-deployment.yaml
│   ├── provision-api-service.yaml
│   ├── caddy-deployment.yaml
│   ├── caddy-service.yaml
│   ├── caddy-configmap.yaml
│   ├── keycloak-deployment.yaml
│   ├── keycloak-service.yaml
│   ├── migrator-job.yaml
│   ├── nats-init-job.yaml
│   ├── configmap.yaml
│   ├── secrets.yaml
│   └── ingress.yaml
├── charts/           # Dependency subcharts
│   └── (auto-downloaded by helm dependency update)
└── ci/
    └── test-values.yaml
```

## What to Do

### Chart.yaml

```yaml
apiVersion: v2
name: pulse
description: OpsConductor-Pulse IoT Platform
type: application
version: 0.1.0
appVersion: "1.0.0"

dependencies:
  - name: emqx
    version: "5.8.*"
    repository: https://repos.emqx.io/charts
    condition: emqx.enabled
  - name: nats
    version: "1.2.*"
    repository: https://nats-io.github.io/k8s/helm/charts/
    condition: nats.enabled
  - name: postgresql
    version: "15.*"
    repository: https://charts.bitnami.com/bitnami
    condition: postgresql.enabled
    # Set to false when using managed PG (RDS, Cloud SQL)
```

### values.yaml

Create with all configurable parameters. Key sections:

```yaml
# Global settings
global:
  imageRegistry: ""  # Override for private registries
  imagePullSecrets: []

# ─── Database ──────────────────────────────────────────
postgresql:
  enabled: true  # Set false for managed PG (RDS, etc.)
  auth:
    database: iotcloud
    username: iot
    existingSecret: pulse-db-secret

externalDatabase:
  enabled: false
  host: ""
  port: 5432
  database: iotcloud
  username: iot
  existingSecret: pulse-db-secret

# ─── EMQX ─────────────────────────────────────────────
emqx:
  enabled: true
  replicaCount: 1  # Increase for HA
  persistence:
    enabled: true
    size: 1Gi

# ─── NATS ──────────────────────────────────────────────
nats:
  enabled: true
  nats:
    jetstream:
      enabled: true
      memStorage:
        enabled: true
        size: 256Mi
      fileStorage:
        enabled: true
        size: 2Gi

# ─── Ingest Workers ───────────────────────────────────
ingest:
  replicaCount: 2
  image:
    repository: pulse/ingest-iot
    tag: latest
  resources:
    requests:
      cpu: 250m
      memory: 256Mi
    limits:
      cpu: "1"
      memory: 512Mi
  env:
    BATCH_SIZE: "1000"
    FLUSH_INTERVAL_MS: "500"
    INGEST_WORKER_COUNT: "4"
    PG_POOL_MAX: "10"
  autoscaling:
    enabled: true
    minReplicas: 2
    maxReplicas: 10
    targetCPUUtilizationPercentage: 70

# ─── UI / API ─────────────────────────────────────────
ui:
  replicaCount: 2
  image:
    repository: pulse/ui-iot
    tag: latest
  resources:
    requests:
      cpu: 250m
      memory: 256Mi
    limits:
      cpu: "1"
      memory: 512Mi

# ─── Route Delivery ───────────────────────────────────
routeDelivery:
  replicaCount: 1
  image:
    repository: pulse/route-delivery
    tag: latest
  resources:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      cpu: 500m
      memory: 256Mi

# ─── Evaluator ────────────────────────────────────────
evaluator:
  replicaCount: 1
  image:
    repository: pulse/evaluator-iot
    tag: latest

# ─── Ops Worker ───────────────────────────────────────
opsWorker:
  replicaCount: 1
  image:
    repository: pulse/ops-worker
    tag: latest

# ─── Keycloak ─────────────────────────────────────────
keycloak:
  replicaCount: 1
  image:
    repository: quay.io/keycloak/keycloak
    tag: "26.0"

# ─── Caddy (Ingress alternative) ─────────────────────
caddy:
  enabled: false  # Use K8s Ingress instead when available

# ─── Ingress ──────────────────────────────────────────
ingress:
  enabled: true
  className: nginx
  annotations: {}
  hosts:
    - host: pulse.example.com
      paths:
        - path: /
          pathType: Prefix
  tls: []
```

### Template Examples

**ingest-deployment.yaml:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "pulse.fullname" . }}-ingest
spec:
  replicas: {{ .Values.ingest.replicaCount }}
  selector:
    matchLabels:
      app.kubernetes.io/component: ingest
  template:
    metadata:
      labels:
        app.kubernetes.io/component: ingest
    spec:
      containers:
        - name: ingest
          image: "{{ .Values.ingest.image.repository }}:{{ .Values.ingest.image.tag }}"
          env:
            - name: NATS_URL
              value: "nats://{{ .Release.Name }}-nats:4222"
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: pulse-db-secret
                  key: url
            {{- range $key, $val := .Values.ingest.env }}
            - name: {{ $key }}
              value: {{ $val | quote }}
            {{- end }}
          resources:
            {{- toYaml .Values.ingest.resources | nindent 12 }}
          livenessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 10
            periodSeconds: 30
          readinessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 10
```

**migrator-job.yaml:**
```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: {{ include "pulse.fullname" . }}-migrator
  annotations:
    "helm.sh/hook": pre-install,pre-upgrade
    "helm.sh/hook-weight": "-5"
    "helm.sh/hook-delete-policy": hook-succeeded
spec:
  template:
    spec:
      restartPolicy: OnFailure
      containers:
        - name: migrator
          image: "{{ .Values.migrator.image.repository }}:{{ .Values.migrator.image.tag }}"
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: pulse-db-secret
                  key: url
```

## Important Notes

- **Don't delete docker-compose.yml** — it remains the local dev environment. Helm is for staging/production.
- **Subchart versions:** Pin to specific minor versions to avoid breaking changes.
- **Secrets management:** Use `existingSecret` references rather than putting passwords in values.yaml. For production, use Sealed Secrets, External Secrets, or cloud-native secret managers (AWS Secrets Manager, Azure Key Vault).
- **Container registry:** Services need to be built and pushed to a container registry (ECR, ACR, GCR, Docker Hub) before deploying to K8s. Add CI/CD pipeline for image builds.
- **Start simple:** Deploy with all `replicaCount: 1` first, verify everything works, then scale up.
