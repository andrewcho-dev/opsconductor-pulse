# 138-001: Remove Deprecated Services

## Task
Remove the `dispatcher` and `delivery_worker` services that were deprecated in Phase 129 (2026-02-16). The notification routing engine (`senders.py`) handles all delivery now.

## Files to Modify

### 1. compose/docker-compose.yml
Remove these service blocks:
- **dispatcher** (lines ~161-198): The entire service definition including image, build, environment, volumes, ports, healthcheck, labels, depends_on
- **delivery_worker** (lines ~200-241): The entire service definition

Both services are already labeled:
```yaml
labels:
  com.opsconductor.deprecated: "true"
  com.opsconductor.deprecated.since: "2026-02-16"
  com.opsconductor.deprecated.removal: "phase129"
```

**Be careful**: Don't remove any other services. Check that no other service has `depends_on: dispatcher` or `depends_on: delivery_worker`. If any do, remove those dependency references too.

### 2. services/dispatcher/ directory
Delete the entire directory:
- `services/dispatcher/dispatcher.py` (16.4 KB)
- `services/dispatcher/Dockerfile` (236 bytes)
- `services/dispatcher/.env.example`
- `services/dispatcher/requirements.txt`
- `services/dispatcher/__pycache__/`

### 3. services/delivery_worker/ directory
Delete the entire directory:
- `services/delivery_worker/worker.py` (34.6 KB)
- `services/delivery_worker/Dockerfile`
- `services/delivery_worker/.env.example`
- `services/delivery_worker/email_sender.py`
- `services/delivery_worker/mqtt_sender.py`
- `services/delivery_worker/snmp_sender.py`
- `services/delivery_worker/requirements.txt`
- `services/delivery_worker/__pycache__/`

### 4. Search for References
Search the entire codebase for references to these services:
```bash
grep -r "dispatcher" --include="*.py" --include="*.yml" --include="*.yaml" --include="*.md" --include="*.tsx" --include="*.ts" .
grep -r "delivery_worker" --include="*.py" --include="*.yml" --include="*.yaml" --include="*.md" --include="*.tsx" --include="*.ts" .
```

**Expected references to update**:
- CI config (`.github/workflows/test.yml`) — currently lists `--cov=services/dispatcher --cov=services/delivery_worker` in coverage. Remove these coverage paths.
- Documentation — remove references to these services in any docs
- Test files — if any tests specifically test dispatcher/delivery_worker, remove them

**References to KEEP**:
- `shared/metrics.py` — has `pulse_delivery_jobs_failed_total` counter. Keep this (it may be used by the routing engine now)
- Any migration files referencing dispatch/delivery tables — leave migrations intact (they're historical)

### 5. Verify Notification Delivery Still Works
The routing engine in `services/ui_iot/routes/notifications.py` (or `services/ops_worker/notifications/senders.py`) should handle all delivery. Check that:
- The notification test endpoint (`POST /api/v1/customer/notification-channels/{id}/test`) still works
- Escalation worker in ops_worker still triggers notifications via the routing engine
- No code imports from `services/dispatcher/` or `services/delivery_worker/`

## Verification
```bash
docker compose config --quiet     # validates compose file structure
docker compose up -d              # all remaining services start without errors
docker compose ps                 # no dispatcher or delivery_worker listed
```

Check that notifications still work:
- Create/test a notification channel → should deliver via routing engine
- Trigger an alert → notification should be sent
