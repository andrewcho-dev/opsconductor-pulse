# 004 — Remove Dangerous Fallback Defaults in Scripts

## Goal

Two scripts have hardcoded fallback passwords that could cause them to
silently use dev credentials if environment variables are missing. Remove
these fallbacks so the scripts fail loudly instead.

## File 1: scripts/provision_simulator_devices.py

### Find (around line 13):
```python
PROVISION_ADMIN_KEY = os.getenv("PROVISION_ADMIN_KEY", "change-me-now")
```

### Replace with:
```python
PROVISION_ADMIN_KEY = os.environ["PROVISION_ADMIN_KEY"]
```

This will raise `KeyError` if the variable is not set, which is the
correct behavior — the script should refuse to run without proper config.

## File 2: scripts/seed_demo_data.py

### Find (around line 18):
```python
PG_PASS = os.getenv("PG_PASS", "iot_dev")
```

### Replace with:
```python
PG_PASS = os.environ["PG_PASS"]
```

Same rationale — fail loudly instead of silently using a dev password.

## Verification

```bash
# Both should fail with KeyError when run without env vars:
cd ~/simcloud
python3 -c "import scripts.provision_simulator_devices" 2>&1 | head -3
# Expected: KeyError: 'PROVISION_ADMIN_KEY'

python3 -c "import scripts.seed_demo_data" 2>&1 | head -3
# Expected: KeyError: 'PG_PASS'
```

## Notes

- These scripts are utilities, not production services. They run
  manually or via Docker Compose profiles (seed, simulator).
- The docker-compose.yml already passes the correct env vars to these
  containers, so they will continue to work in that context.
- Only direct invocation without env vars will break (which is desired).
