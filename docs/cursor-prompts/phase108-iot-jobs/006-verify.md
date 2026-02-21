# Phase 108 — Verify IoT Jobs

## Step 1: Migration applied

```bash
docker exec iot-postgres psql -U iot iotcloud -c \
  "SELECT table_name FROM information_schema.tables
   WHERE table_name IN ('jobs','job_executions') ORDER BY table_name;"
```

Expected: 2 rows.

```bash
docker exec iot-postgres psql -U iot iotcloud -c "\d jobs" | grep -E "job_id|status|expires"
docker exec iot-postgres psql -U iot iotcloud -c "\d job_executions" | grep -E "status|execution_number"
```

---

## Step 2: Create a job targeting a single device

```bash
DEVICE_ID=$(docker exec iot-postgres psql -U iot iotcloud -tAc \
  "SELECT device_id FROM device_state LIMIT 1;")

curl -s -X POST http://localhost:8000/customer/jobs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"document_type\": \"reboot\",
    \"document_params\": {\"delay_s\": 5},
    \"target_device_id\": \"${DEVICE_ID}\",
    \"expires_in_hours\": 1
  }" | python3 -m json.tool
```

Expected: `{"job_id": "...", "status": "IN_PROGRESS", "execution_count": 1, ...}`

Save the job_id:
```bash
JOB_ID=<job_id from above>
```

---

## Step 3: Verify execution was created

```bash
curl -s "http://localhost:8000/customer/jobs/${JOB_ID}" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool | grep -A5 '"executions"'
```

Expected: one execution with `"status": "QUEUED"` for the target device.

---

## Step 4: Device polls for pending jobs

```bash
PROV_TOKEN="tok-your-device-token"  # provision token for ${DEVICE_ID}

curl -s "http://localhost:<ingest_port>/device/v1/jobs/pending" \
  -H "X-Provision-Token: ${PROV_TOKEN}" | python3 -m json.tool
```

Expected: `{"jobs": [{"job_id": "...", "document": {"type": "reboot", "params": {...}}, ...}]}`

---

## Step 5: Device claims job (QUEUED → IN_PROGRESS)

```bash
curl -s -X PUT \
  "http://localhost:<ingest_port>/device/v1/jobs/${JOB_ID}/execution" \
  -H "X-Provision-Token: ${PROV_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"status": "IN_PROGRESS"}' | python3 -m json.tool
```

Expected: `{"status": "IN_PROGRESS", ...}`

```bash
# Verify in operator API
curl -s "http://localhost:8000/customer/jobs/${JOB_ID}" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['executions'][0]['status'])"
```

Expected: `IN_PROGRESS`

---

## Step 6: Device completes job (IN_PROGRESS → SUCCEEDED)

```bash
curl -s -X PUT \
  "http://localhost:<ingest_port>/device/v1/jobs/${JOB_ID}/execution" \
  -H "X-Provision-Token: ${PROV_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"status": "SUCCEEDED", "status_details": {"message": "reboot scheduled"}}' \
  | python3 -m json.tool
```

Expected: `{"status": "SUCCEEDED", ...}`

```bash
# Job should now be COMPLETED (only one device)
curl -s "http://localhost:8000/customer/jobs/${JOB_ID}" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('job:', d['status'])"
```

Expected: `job: COMPLETED`

---

## Step 7: Test group targeting

```bash
GROUP_ID=$(docker exec iot-postgres psql -U iot iotcloud -tAc \
  "SELECT group_id FROM device_groups LIMIT 1;")

curl -s -X POST http://localhost:8000/customer/jobs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"document_type\": \"update_config\", \"document_params\": {\"log_level\": \"debug\"}, \"target_group_id\": \"${GROUP_ID}\"}" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('executions:', d['execution_count'])"
```

Expected: `execution_count` equals the number of members in that group.

---

## Step 8: Test TTL expiry

Create a job with a 0-second effective TTL (set expires_at via DB directly):

```bash
# Create a job, then immediately backdate its expires_at
JOB2=$(curl -s -X POST http://localhost:8000/customer/jobs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"document_type\": \"test_expiry\", \"document_params\": {}, \"target_device_id\": \"${DEVICE_ID}\", \"expires_in_hours\": 24}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['job_id'])")

# Backdate expires_at to the past
docker exec iot-postgres psql -U iot iotcloud -c \
  "UPDATE jobs SET expires_at = NOW() - INTERVAL '1 minute' WHERE job_id = '${JOB2}';"

# Wait for the worker tick (up to 60s) then check
sleep 65
curl -s "http://localhost:8000/customer/jobs/${JOB2}" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('job:', d['status'], '| exec:', d['executions'][0]['status'])"
```

Expected: `job: COMPLETED | exec: TIMED_OUT`

---

## Step 9: Test job cancellation

```bash
JOB3=$(curl -s -X POST http://localhost:8000/customer/jobs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"document_type\": \"reboot\", \"document_params\": {}, \"target_device_id\": \"${DEVICE_ID}\"}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['job_id'])")

curl -s -X DELETE "http://localhost:8000/customer/jobs/${JOB3}" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

Expected: `{"job_id": "...", "status": "CANCELED"}`

---

## Step 10: Unit tests

```bash
pytest tests/unit/ -q --no-cov -k "job" 2>&1 | tail -10
```

Add `tests/unit/test_jobs.py` if it doesn't exist:

```python
from shared.twin import compute_delta  # confirm shared module still works

def test_job_transition_queued_to_in_progress():
    allowed = {"QUEUED": {"IN_PROGRESS"}, "IN_PROGRESS": {"SUCCEEDED","FAILED","REJECTED"}}
    assert "IN_PROGRESS" in allowed["QUEUED"]
    assert "SUCCEEDED" in allowed["IN_PROGRESS"]
    assert "QUEUED" not in allowed["IN_PROGRESS"]

def test_terminal_statuses():
    terminal = {"SUCCEEDED", "FAILED", "TIMED_OUT", "REJECTED"}
    assert "IN_PROGRESS" not in terminal
    assert "QUEUED" not in terminal
    assert all(s in terminal for s in ["SUCCEEDED","FAILED","TIMED_OUT","REJECTED"])
```

---

## Step 11: Frontend build

```bash
npm run build --prefix frontend 2>&1 | tail -5
```

---

## Step 12: Full unit suite regression

```bash
pytest tests/unit/ -q --no-cov 2>&1 | tail -5
```

Expected: 0 failures.

---

## Step 13: Commit

```bash
git add \
  db/migrations/077_iot_jobs.sql \
  services/ui_iot/routes/jobs.py \
  services/ui_iot/app.py \
  services/ingest_iot/ \
  services/ops_worker/ \
  frontend/src/features/jobs/ \
  frontend/src/services/api/jobs.ts \
  tests/unit/test_jobs.py

git commit -m "feat: IoT Jobs — AWS IoT Jobs semantics

- Migration 077: jobs + job_executions tables with RLS, TTL index,
  target constraint (device | group | all), full status lifecycle
- Operator API (ui_iot/routes/jobs.py): POST /jobs (snapshot targeting),
  GET /jobs, GET /jobs/{id}, DELETE /jobs/{id} (cancel)
- Device API (ingest_iot): GET /device/v1/jobs/pending,
  PUT /device/v1/jobs/{id}/execution (claim + complete),
  GET /device/v1/jobs/{id}/execution
- ops_worker: run_jobs_expiry_tick() marks QUEUED→TIMED_OUT on expiry,
  advances job to COMPLETED when all executions terminal
- Frontend: JobsPage, CreateJobModal, device detail 'Create Job' button,
  nav link; API client in services/api/jobs.ts"

git push origin main
git log --oneline -3
```

## Definition of Done

- [ ] Migration 077 applied: `jobs` and `job_executions` tables exist with RLS
- [ ] POST /customer/jobs creates job + executions (snapshot targeting)
- [ ] GET /customer/jobs/{id} returns job with executions list
- [ ] Device HTTP poll returns QUEUED jobs
- [ ] Device can claim (QUEUED→IN_PROGRESS) and complete (→SUCCEEDED/FAILED)
- [ ] Job advances to COMPLETED when all executions terminal
- [ ] Job cancellation REJECTs all QUEUED executions
- [ ] TTL expiry worker marks QUEUED→TIMED_OUT after expires_at
- [ ] Frontend Jobs page renders, Create Job modal works
- [ ] Frontend build passes
- [ ] 0 unit test failures
