# Performance Baselines

Generated: 2026-02-04
Environment: Linux 5.15.0-168-generic, Intel Xeon Gold 5120, Docker Compose

## API Response Times (p95)
| Endpoint | Baseline | Threshold |
|----------|----------|-----------|
| GET /customer/devices | 4.51ms | 200ms |
| GET /customer/devices/{device_id} | 4.77ms | 150ms |
| GET /customer/alerts | 5.86ms | 200ms |
| GET /customer/integrations | 5.04ms | 150ms |
| GET /api/auth/status | 1.29ms | 100ms |
| GET /debug/auth | 129.11ms | 2000ms |
| GET /operator/devices | 17.10ms | 300ms |

## Database Query Times (p95)
| Query | Baseline | Threshold |
|-------|----------|-----------|
| devices by tenant | 0.79ms | 50ms |
| alerts by tenant | 3.17ms | 100ms |
| integrations by tenant | 0.69ms | 50ms |
| delivery jobs pending | 0.54ms | 100ms |
| cross-tenant devices | 1.55ms | 200ms |
| RLS overhead (p95) | 0.54ms (1.09ms with RLS, 0.55ms without) | n/a |

## Page Load Times
| Page | Baseline | Threshold |
|------|----------|-----------|
| Customer Dashboard | 45.67ms | 3000ms |
| Customer Devices | 98.76ms | 3000ms |
| Customer Webhooks | 63.84ms | 3000ms |
| Customer SNMP | 58.07ms | 3000ms |
| Customer Email | 56.07ms | 3000ms |

Update baselines by running:
pytest -m benchmark -v --benchmark-json=benchmark_results.json
