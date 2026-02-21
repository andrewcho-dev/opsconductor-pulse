# Prompt 006 — Verify Phase 58

## Step 1: Unit Tests

```bash
pytest -m unit -v 2>&1 | tail -40
```

## Step 2: TypeScript Build

```bash
cd frontend && npm run build 2>&1 | tail -10
```

## Step 3: Import Check

```bash
cd services && python -c "from shared.metrics import ingest_messages_total, fleet_active_alerts; print('OK')"
```

## Step 4: Checklist

- [ ] `prometheus_client` in ui_iot, ingest_iot, evaluator_iot requirements.txt
- [ ] `services/shared/metrics.py` exists with all metric objects
- [ ] GET /metrics on ui_iot returns Prometheus text format
- [ ] `pulse_fleet_active_alerts` and `pulse_fleet_devices_by_status` in ui_iot /metrics
- [ ] `ingest_messages_total` incremented in ingest_iot
- [ ] `ingest_queue_depth` gauge updated
- [ ] GET /metrics on ingest_iot exists
- [ ] `evaluator_rules_evaluated_total` incremented in evaluator_iot
- [ ] GET /metrics on evaluator_iot exists
- [ ] 6 unit tests in test_prometheus_metrics.py

## Report

Output PASS / FAIL per criterion.
