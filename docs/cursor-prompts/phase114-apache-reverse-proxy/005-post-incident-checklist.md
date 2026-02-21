# 005 — Post-Incident Checklist (Audit Trail Template)

Use this template immediately after service restoration. Keep entries short and factual.

---

## Incident Metadata

- Incident ID:
- Date (UTC):
- Start time (UTC):
- End time (UTC):
- Duration:
- Severity (SEV-1/2/3):
- Reported by:
- Incident commander:
- Responders:

---

## Impact Summary

- Public URL impacted: `https://pulse.enabledconsultants.com` (yes/no)
- Login impacted (yes/no):
- MQTT ingest impacted (yes/no):
- Provisioning API impacted (yes/no):
- Approx users/devices affected:
- Business impact summary (1-3 lines):

---

## Timeline (UTC)

| Time | Event | Owner | Evidence |
|------|-------|-------|----------|
|      |       |       |          |
|      |       |       |          |
|      |       |       |          |

Notes:
- Record command outputs, screenshots, and log snippets in a ticket or incident folder.
- Link evidence locations in the table.

---

## Detection and Diagnosis

- Detection source (monitoring, user report, manual check):
- Primary symptom:
- Confirmed failing layer(s):
  - [ ] DNS
  - [ ] Apache edge proxy (`192.168.50.99`)
  - [ ] Docker host firewall (`192.168.50.53`)
  - [ ] Caddy
  - [ ] UI / Keycloak auth
  - [ ] MQTT broker
  - [ ] Other:
- Root cause (technical):
- Root cause category (config drift / cert / network / app bug / dependency / unknown):

---

## Actions Taken

### Mitigation actions

- [ ] Ran break-glass checks from `004-break-glass.md`
- [ ] Restored traffic via temporary workaround
- [ ] Captured before/after config snapshots

Commands / changes applied:

```text
# Paste exact commands or PR/commit links here
```

### Recovery actions

- [ ] Service restored and user validation completed
- [ ] Rolled back temporary workaround (if any)
- [ ] Re-applied hardened settings

---

## Security and Hardening Validation

### Port exposure (Docker host `192.168.50.53`)

- [ ] `5432`, `6432`, `8081`, `9999` bound to `127.0.0.1`
- [ ] `80/443` reachable only from Apache host `192.168.50.99`
- [ ] Public `80/443` path works via Apache edge only
- [ ] MQTT policy validated (`8883/9001` open only if required)

### Auth/public host alignment

- [ ] `KEYCLOAK_URL` matches public host
- [ ] `UI_BASE_URL` matches public host
- [ ] `KC_HOSTNAME` matches public host
- [ ] OIDC issuer matches public host

---

## Verification Evidence

- `curl -I https://pulse.enabledconsultants.com` result:
- Browser login test result:
- `docker compose ps` result summary:
- Firewall status output attached:
- Any remaining warnings/errors:

---

## Follow-Up Work

### Immediate (24h)

- [ ] Remove temporary permissive firewall rules
- [ ] Confirm cert renewal status
- [ ] Confirm monitoring alerts are green

### Short-term (7 days)

- [ ] Permanent fix reviewed by second engineer
- [ ] Runbook updated (`phase114` docs)
- [ ] Test break-glass procedure in staging/lab

### Preventive actions

1.
2.
3.

Owner(s):
Due date(s):

---

## Sign-Off

- Incident commander sign-off:
- Platform owner sign-off:
- Date closed (UTC):

