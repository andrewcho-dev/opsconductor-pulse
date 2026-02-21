# Phase 197 — Authorization Hardening

## Goal

Fix three authorization-related security issues: the `pulse_operator` database role has BYPASSRLS and blanket DML on all tables (over-privileged), the admin key comparison is vulnerable to timing attacks, and the MQTT password setup passes credentials as a subprocess argument (visible in process listings).

## Current State (problem)

1. **pulse_operator role** (`db/migrations/004_enable_rls.sql`): `BYPASSRLS` + `GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES`. Any code path using `operator_connection()` bypasses all tenant isolation with full write access to every table.
2. **Admin key comparison** (`provision_api/app.py:177-180`): Plain `!=` string comparison is vulnerable to timing attacks. No rate limiting on admin endpoints.
3. **Subprocess password** (`provision_api/app.py:90-96`): MQTT password is passed as a CLI argument to `mosquitto_passwd`, making it visible in `/proc/<pid>/cmdline`.

## Target State

- `pulse_operator` split into two roles: `pulse_operator_read` (SELECT only, BYPASSRLS) and `pulse_operator_write` (narrowly scoped DML, no BYPASSRLS except where required).
- Admin key comparison uses `secrets.compare_digest()` with rate limiting.
- MQTT password management uses a library or temp-file approach, never a CLI argument.

## Execution Order

| Step | File | What | Depends On |
|------|------|------|------------|
| 1 | `001-operator-role-granularity.md` | Create granular DB roles, update migrations | — |
| 2 | `002-operator-connection-update.md` | Update `operator_connection()` to use new roles | Step 1 |
| 3 | `003-admin-key-timing-safe.md` | Fix admin key comparison + add rate limiting | — |
| 4 | `004-subprocess-password.md` | Fix MQTT password subprocess exposure | — |
| 5 | `005-update-documentation.md` | Update affected docs | Steps 1–4 |

## Verification

```bash
# No blanket BYPASSRLS + full DML grant in migrations
grep -A5 'BYPASSRLS' db/migrations/
# Should show scoped grants, not schema-wide

# Timing-safe comparison used
grep -n 'compare_digest\|secrets.compare' services/provision_api/app.py
# Must show timing-safe comparison

# No password in subprocess args
grep -n 'subprocess.*password\|Popen.*password' services/provision_api/app.py
# Must return zero results
```

## Documentation Impact

- `docs/architecture/tenant-isolation.md` — Update operator role description
- `docs/operations/security.md` — Document role separation
