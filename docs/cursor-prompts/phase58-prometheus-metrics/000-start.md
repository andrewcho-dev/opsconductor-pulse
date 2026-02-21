# Phase 58: Prometheus /metrics Endpoint

## What Exists

- Services have in-memory `counters` dicts (messages_received, alerts_created, etc.)
- `/health` endpoints expose these informally as JSON
- No `/metrics` endpoint, no `prometheus_client` library installed

## What This Phase Adds

1. **`prometheus_client` library** added to ui_iot, ingest_iot, evaluator_iot requirements
2. **`services/shared/metrics.py`** — shared metric registry with standard gauges/counters
3. **`GET /metrics`** on ui_iot — Prometheus text format, covers: active alert counts, device counts by status, delivery job failure rate
4. **`GET /metrics`** on ingest_iot — messages_received, messages_rejected, rate_limited count, queue depth
5. **`GET /metrics`** on evaluator_iot — rules_evaluated, alerts_created, evaluation_errors
6. **No auth on /metrics** — standard Prometheus convention (scraper access only); expose on separate internal port or behind IP allowlist note

## Execution Order

| Prompt | Description |
|--------|-------------|
| 001 | shared/metrics.py + requirements updates |
| 002 | ui_iot /metrics endpoint |
| 003 | ingest_iot /metrics endpoint |
| 004 | evaluator_iot /metrics endpoint |
| 005 | Unit tests |
| 006 | Verify |

## Key Files

- `services/shared/metrics.py` — new (prompt 001)
- `services/ui_iot/requirements.txt` — prompt 001
- `services/ingest_iot/requirements.txt` — prompt 001
- `services/evaluator_iot/requirements.txt` — prompt 001
- `services/ui_iot/app.py` — prompt 002
- `services/ingest_iot/ingest.py` — prompt 003
- `services/evaluator_iot/evaluator.py` — prompt 004
