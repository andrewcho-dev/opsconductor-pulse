# Task 3: Horizontal Pod Autoscaler Configuration

## Files to Create

- `helm/pulse/templates/ingest-hpa.yaml`
- `helm/pulse/templates/route-delivery-hpa.yaml`

## What to Do

Configure HPA for the two horizontally scalable services: ingest workers and route delivery workers.

### Ingest Workers HPA

```yaml
{{- if .Values.ingest.autoscaling.enabled }}
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {{ include "pulse.fullname" . }}-ingest
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {{ include "pulse.fullname" . }}-ingest
  minReplicas: {{ .Values.ingest.autoscaling.minReplicas }}
  maxReplicas: {{ .Values.ingest.autoscaling.maxReplicas }}
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: {{ .Values.ingest.autoscaling.targetCPUUtilizationPercentage }}
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
        - type: Pods
          value: 2
          periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Pods
          value: 1
          periodSeconds: 120
{{- end }}
```

### Route Delivery HPA

Same pattern, with different thresholds (route delivery is less CPU-intensive, more I/O-bound):

```yaml
minReplicas: 1
maxReplicas: 5
targetCPUUtilizationPercentage: 60
```

### Custom Metrics (Advanced — For Later)

For more precise scaling, use NATS consumer lag as a custom metric:
- Install Prometheus Adapter or KEDA
- Scrape NATS monitoring endpoint (`/jsz?consumers=true`)
- Scale on `pending_messages` per consumer

This is a Phase 164+ optimization.

## Important Notes

- **Ingest workers are stateless** — caches rebuild from DB on startup. Safe to scale up/down.
- **Scale-up is aggressive** (60s window, +2 pods). Scale-down is conservative (300s window, -1 pod). This prevents flapping.
- **Resource requests must be set** for HPA to work. Ensure `resources.requests.cpu` is defined in values.yaml.
- **Don't autoscale evaluator or ops-worker** — these are singleton-like services. Running multiple evaluator instances could cause duplicate alerts.
