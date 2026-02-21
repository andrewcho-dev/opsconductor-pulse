# Prompt 005 — Verification Checklist

Work through each item in order and confirm it passes before marking done.

## Migration
- [ ] `ls db/migrations/ | sort` shows the new alert_digest_settings migration with a sequential number
- [ ] Migration SQL contains the frequency CHECK constraint

## Backend
- [ ] `GET /customer/alert-digest-settings` returns 200 with frequency and email fields
- [ ] `PUT /customer/alert-digest-settings` with valid body returns 200
- [ ] `PUT /customer/alert-digest-settings` with invalid frequency value returns 422
- [ ] `send_alert_digest()` function exists in subscription_worker
- [ ] Worker loop calls `send_alert_digest` on a timed interval

## Frontend
- [ ] `frontend/src/features/alerts/DigestSettingsCard.tsx` exists
- [ ] Frequency selector renders Daily, Weekly, Disabled options
- [ ] Email input is present
- [ ] Save button triggers PUT request
- [ ] `npm run build` completes without errors

## Unit Tests
- [ ] `tests/unit/test_alert_digest.py` exists
- [ ] All 5 test functions present
- [ ] `pytest -m unit tests/unit/test_alert_digest.py -v` — all 5 pass

## Final
- [ ] No regressions: `pytest -m unit -v` full suite still green
