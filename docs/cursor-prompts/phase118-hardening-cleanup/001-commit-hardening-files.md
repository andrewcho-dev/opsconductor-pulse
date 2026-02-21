# 001 — Commit Uncommitted Hardening Files

## Context

6 files from Phases 110-113 are modified but uncommitted. They contain port binding hardening, Dockerfile fixes, logging renames, and secrets extraction. Stage and commit them as a single commit.

## Files to Stage

These files are already modified in the working tree:

| File | What Changed |
|------|-------------|
| `compose/docker-compose.yml` | Bind Postgres/PGBouncer/API/webhook to `127.0.0.1`; fix subscription-worker build context; add `KEYCLOAK_CLIENT_SECRET` env var |
| `services/subscription_worker/Dockerfile` | Remove duplicate `FROM` block; copy `shared/`; install from `requirements.txt` |
| `services/subscription_worker/worker.py` | `from shared.log` → `from shared.logging` |
| `services/maintenance/log_cleanup.py` | `from shared.log` → `from shared.logging` |
| `scripts/provision_simulator_devices.py` | `os.getenv("PROVISION_ADMIN_KEY", "change-me-now")` → `os.environ["PROVISION_ADMIN_KEY"]` |
| `scripts/seed_demo_data.py` | `os.getenv("PG_PASS", "iot_dev")` → `os.environ["PG_PASS"]` |

## Steps

1. Verify the changes look correct:
   ```bash
   git diff compose/docker-compose.yml services/subscription_worker/Dockerfile services/subscription_worker/worker.py services/maintenance/log_cleanup.py scripts/provision_simulator_devices.py scripts/seed_demo_data.py
   ```

2. Stage all 6 files:
   ```bash
   git add compose/docker-compose.yml services/subscription_worker/Dockerfile services/subscription_worker/worker.py services/maintenance/log_cleanup.py scripts/provision_simulator_devices.py scripts/seed_demo_data.py
   ```

3. Commit:
   ```bash
   git commit -m "fix: bind service ports to loopback, fix subscription worker build, harden secrets"
   ```

## Verification

- `git status` — the 6 files are no longer in the modified list
- `git log --oneline -1` — shows the new commit message
- The two `??` backup files (`compose/docker-compose.yml.bak-*` and `compose/docker-compose.yml.pre-rotation.*`) remain as untracked — they'll be cleaned up in step 004
