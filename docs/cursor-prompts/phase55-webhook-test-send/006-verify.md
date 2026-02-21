# Prompt 006 — Verify Phase 55

## Step 1: Unit Tests

```bash
pytest -m unit -v 2>&1 | tail -40
```

## Step 2: TypeScript Build

```bash
cd frontend && npm run build 2>&1 | tail -10
```

## Step 3: Checklist

### Backend
- [ ] POST /customer/integrations/{id}/test-send exists
- [ ] SSRF validation in test-send
- [ ] GET /customer/delivery-jobs with status/integration_id filters
- [ ] GET /customer/delivery-jobs/{id}/attempts exists

### Frontend
- [ ] "Send Test" button on webhook integration detail
- [ ] Result shows HTTP status + latency
- [ ] DeliveryLogPage.tsx at /delivery-log
- [ ] Status filter on delivery log
- [ ] Expandable attempt history
- [ ] "Delivery Log" in nav

### Unit Tests
- [ ] test_webhook_test_send.py with 11 tests

## Report

Output PASS / FAIL per criterion.
