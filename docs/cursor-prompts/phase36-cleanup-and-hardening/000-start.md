# Phase 36: Database Cleanup and Ingest Hardening

## Overview

Clean the test environment and add protection against ingest flooding from unknown/rejected devices.

## Problems Addressed

1. **5+ million log entries** - Old test data consuming disk
2. **Zombie simulators** - Old device simulators still attempting connections
3. **DoS vulnerability** - Rejected devices generate unlimited log entries
4. **No rate limiting** - Ingest endpoint accepts unlimited requests

## Architecture

```
                     ┌─────────────────┐
                     │  Rate Limiter   │
                     │  (per IP/device)│
                     └────────┬────────┘
                              │
     Rejected (silent)        │         Accepted
     ◄────────────────────────┼──────────────────►
                              │
                     ┌────────▼────────┐
                     │  Device Check   │
                     │  (known device?)│
                     └────────┬────────┘
                              │
     Unknown Device           │         Known Device
     (sampled log)            │         (full processing)
     ◄────────────────────────┼──────────────────►
                              │
                     ┌────────▼────────┐
                     │  Ingest Queue   │
                     └─────────────────┘
```

## Execution Order

| # | File | Description |
|---|------|-------------|
| 1 | 001-stop-simulators.md | Find and stop device simulators |
| 2 | 002-database-cleanup.md | Truncate logs, remove test data |
| 3 | 003-rate-limiting.md | Add rate limiting to ingest endpoint |
| 4 | 004-log-sampling.md | Sample rejected request logs |
| 5 | 005-log-retention.md | Automatic log cleanup policies |
| 6 | 006-fresh-seed.md | Seed clean test data |

## Quick Start (Emergency)

If the system is under load right now:

```bash
# 1. Stop all simulators immediately
docker compose stop simulator device-sim  # if containerized
pkill -f "python.*simulat"                # if running as processes
pkill -f "node.*simulat"

# 2. Block unknown devices at nginx (temporary)
# Add to nginx config:
# limit_req_zone $binary_remote_addr zone=ingest:10m rate=10r/s;
# location /ingest/ { limit_req zone=ingest burst=20 nodelay; }

# 3. Truncate logs (careful - this is destructive)
docker compose exec postgres psql -U iot -d iotcloud -c "TRUNCATE activity_log CASCADE;"
```

## Success Criteria

- [ ] No zombie simulator processes running
- [ ] Log tables under 100,000 rows
- [ ] Rate limiting active on ingest endpoint
- [ ] Unknown device rejections logged at 1% sample rate
- [ ] Fresh tenant with 12 devices provisioned
- [ ] Ingest endpoint handles 10,000 req/sec without issues
