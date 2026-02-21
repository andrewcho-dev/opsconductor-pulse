# Phase 102 — Verify Observability

## Step 1: Confirm shared/log.py exists

```bash
ls -lh services/shared/log.py
```

## Step 2: Restart services and tail logs

```bash
docker compose -f compose/docker-compose.yml restart iot-ui iot-ingest iot-evaluator
sleep 3
docker logs iot-ui --tail=20
```

Expected: each line is valid JSON with `ts`, `level`, `service`, `logger`, `msg` fields.

## Step 3: Confirm trace_id in HTTP logs

```bash
curl -s http://localhost:8000/health
docker logs iot-ui --tail=5
```

Expected: a log line like:
```json
{"ts": "...", "level": "INFO", "service": "ui_iot", "logger": "pulse.http",
 "msg": "http_request", "trace_id": "xxxxxxxx-...", "method": "GET",
 "path": "/health", "status": 200, "elapsed_ms": 1.2}
```

## Step 4: Confirm X-Trace-ID response header

```bash
curl -si http://localhost:8000/health | grep -i x-trace-id
```

Expected: `X-Trace-ID: <uuid>`

## Step 5: Confirm trace_id propagation

```bash
curl -s -H "X-Trace-ID: test-trace-123" http://localhost:8000/health
docker logs iot-ui --tail=3 | python3 -c "import sys,json; [print(json.loads(l).get('trace_id')) for l in sys.stdin]"
```

Expected: `test-trace-123` appears in the log output.

## Step 6: Confirm evaluator tick logs are JSON

```bash
docker logs iot-evaluator --tail=10
```

Expected: JSON lines with `"msg": "tick_start"` / `"msg": "tick_done"` and a `trace_id`.

## Step 7: Commit

```bash
git add \
  services/shared/log.py \
  services/ui_iot/middleware/trace.py \
  services/ui_iot/app.py \
  services/ingest_iot/ingest.py \
  services/evaluator/evaluator.py \
  services/ops_worker/worker.py \
  services/delivery_worker/worker.py \
  compose/docker-compose.yml

git commit -m "feat: structured JSON logging with trace_id across all services

- services/shared/log.py: JSON formatter + trace_id_var ContextVar
- ui_iot/middleware/trace.py: TraceMiddleware generates/propagates X-Trace-ID
- All services call configure_root_logger() at startup
- Evaluator + ops_worker + delivery_worker ticks set trace_id per run
- docker-compose.yml: SERVICE_NAME env var per container"

git push origin main
git log --oneline -3
```

## Definition of Done

- [ ] All service log output is valid JSON
- [ ] Every HTTP response carries X-Trace-ID header
- [ ] trace_id flows from request header into log lines
- [ ] Evaluator tick logs carry trace_id
- [ ] No plain-text log lines from pulse services (uvicorn access logs are OK)
