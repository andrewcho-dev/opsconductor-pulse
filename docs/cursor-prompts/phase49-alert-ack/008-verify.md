# Prompt 008 — Verify Phase 49

Run the full verification suite and confirm all acceptance criteria pass.

## Step 1: Unit Tests

```bash
pytest -m unit -v 2>&1 | tail -40
```

All tests must pass. If any fail, fix them before proceeding.

## Step 2: Migration Check

Confirm migration 057 file exists:
```bash
ls db/migrations/057_alert_ack_fields.sql
```

Check that migration 058 (index update) was written as part of 004 or exists separately.

## Step 3: TypeScript Build

```bash
cd frontend && npm run build 2>&1 | tail -20
```

Must complete with no errors.

## Step 4: Checklist

Verify each acceptance criterion from prompts 001–007:

### Migration (001)
- [ ] `db/migrations/057_alert_ack_fields.sql` exists
- [ ] Adds `silenced_until`, `acknowledged_by`, `acknowledged_at`
- [ ] Adds `idx_fleet_alert_silenced` index

### Unique Index Update (004)
- [ ] Migration exists (in 057 or separate 058) that updates `fleet_alert_open_uq` to cover `status IN ('OPEN', 'ACKNOWLEDGED')`

### Backend Actions (002)
- [ ] PATCH /customer/alerts/{id}/acknowledge endpoint exists in customer.py
- [ ] PATCH /customer/alerts/{id}/close endpoint exists
- [ ] PATCH /customer/alerts/{id}/silence endpoint with SilenceRequest body exists

### Backend List Filter (003)
- [ ] list_alerts accepts `status` query param
- [ ] Response includes `total`, `status_filter`, new fields

### Evaluator (004)
- [ ] `is_silenced()` helper added to evaluator.py
- [ ] `open_or_update_alert()` ON CONFLICT covers OPEN+ACKNOWLEDGED
- [ ] Silence check before open_or_update_alert() in evaluation loop

### Frontend Actions (005)
- [ ] Acknowledge/Close/Silence buttons exist in AlertListPage and DeviceAlertsSection
- [ ] ACKNOWLEDGED alerts visually de-emphasized

### Frontend History (006)
- [ ] Status filter tabs exist in AlertListPage
- [ ] Total count displayed

### Unit Tests (007)
- [ ] test_alert_actions.py exists with 10 tests
- [ ] test_evaluator_ack_silence.py exists with 5 tests

## Report

Output a summary: PASS / FAIL per criterion.
