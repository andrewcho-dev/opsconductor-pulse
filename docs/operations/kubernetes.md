---
last-verified: 2026-02-19
sources:
  - helm/pulse/Chart.yaml
  - helm/pulse/values.yaml
phases: [163]
---

# Kubernetes Deployment

> Helm-based deployment for staging/production clusters. Docker Compose remains the local dev environment.

## Helm Chart

Chart location: `helm/pulse/`

Key dependencies (subcharts):

- EMQX (MQTT broker)
- NATS (JetStream)
- PostgreSQL (optional; disable for managed PG)

## Quick Start (template render)

```bash
helm dependency update helm/pulse
helm template pulse helm/pulse -f helm/pulse/values.yaml > /tmp/pulse.yaml
```

## Install / Upgrade

```bash
helm upgrade --install pulse helm/pulse \
  --namespace pulse --create-namespace \
  -f helm/pulse/values.yaml
```

## Using Managed PostgreSQL

- Set `postgresql.enabled: false`
- Set `externalDatabase.enabled: true`
- Provide DB credentials via `pulse-db-secret`

See `docs/operations/managed-postgres.md`.

