# Phase 101 — Verify Pulse Envelope v1

## Step 1: Confirm migration 073 applied

```bash
docker exec iot-postgres psql -U iot iotcloud -c \
  "\d quarantine_events" | grep envelope_version
```

Expected: `envelope_version | text | ... | '1'::text`

## Step 2: Confirm version validation in ingest_core.py

```bash
grep -n "unsupported_envelope_version\|SUPPORTED_VERSIONS" \
  services/shared/ingest_core.py
```

Expected: both strings present.

## Step 3: Test rejection of unknown version via HTTP

```bash
curl -s -X POST \
  "http://localhost:8000/ingest/v1/tenant/test-tenant/device/dev-001/telemetry" \
  -H "Content-Type: application/json" \
  -H "X-Provision-Token: tok-test" \
  -d '{"version": "99", "ts": '"$(date +%s)"'.0, "provision_token": "tok-test"}' \
  | python3 -m json.tool
```

Expected: HTTP 4xx or a quarantine entry with rejection_reason `unsupported_envelope_version:99`.

## Step 4: Confirm spec file exists

```bash
ls -lh docs/PULSE_ENVELOPE_V1.md
```

Expected: file present, > 2 KB.

## Step 5: Confirm ARCHITECTURE.md link

```bash
grep "PULSE_ENVELOPE_V1" docs/ARCHITECTURE.md
```

Expected: one matching line containing the link.

## Step 6: Commit

```bash
git add \
  services/shared/ingest_core.py \
  db/migrations/073_envelope_version.sql \
  docs/PULSE_ENVELOPE_V1.md \
  docs/ARCHITECTURE.md

git commit -m "feat: Pulse Envelope v1 — version field, rejection rules, spec doc

- ingest_core.validate_and_prepare(): accept version field (default '1'),
  reject unknown versions with unsupported_envelope_version:{v}
- Migration 073: quarantine_events.envelope_version column
- docs/PULSE_ENVELOPE_V1.md: canonical ingest envelope specification
- ARCHITECTURE.md: link to spec under Ingestion section"

git push origin main
git log --oneline -3
```

## Definition of Done

- [ ] Migration 073 applied: `quarantine_events.envelope_version` column exists
- [ ] `ingest_core.py` rejects `version != "1"` with correct reason
- [ ] `docs/PULSE_ENVELOPE_V1.md` committed
- [ ] Link in `docs/ARCHITECTURE.md` under Ingestion section
- [ ] Commit pushed to main
