# Task 3: Update Certificate Worker for EMQX

## File to Modify

- `services/ops_worker/workers/certificate_worker.py`

## Problem

The current `regenerate_crl()` function writes a CRL file to `/mosquitto/certs/device-crl.pem` and requires a manual `SIGHUP` to Mosquitto to reload it. EMQX handles CRL differently — it can reload via API call or config reload.

## What to Do

### Step 1: Update the CRL file path

Change the CRL output path from the Mosquitto-specific path to a more generic cert directory:

```python
CRL_OUTPUT_PATH = os.getenv("CRL_OUTPUT_PATH", "/certs/device-crl.pem")
```

This aligns with the EMQX volume mount (`./mosquitto/certs:/certs:ro`).

### Step 2: Add EMQX CRL reload notification

After writing the CRL file, notify EMQX to reload its TLS config. EMQX 5.x supports config reload via its management API:

```python
async def _notify_broker_crl_update():
    """Notify EMQX to reload TLS configuration after CRL update."""
    emqx_api_url = os.getenv("EMQX_API_URL", "http://iot-mqtt:18083")
    emqx_api_user = os.getenv("EMQX_API_USER", "admin")
    emqx_api_pass = os.getenv("EMQX_DASHBOARD_PASSWORD", "admin123")

    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            # EMQX 5.x: reload listeners to pick up new CRL
            resp = await client.put(
                f"{emqx_api_url}/api/v5/listeners/ssl:external/restart",
                auth=(emqx_api_user, emqx_api_pass),
            )
            if resp.status_code < 300:
                logger.info("emqx_crl_reload_success")
            else:
                logger.warning("emqx_crl_reload_failed", extra={
                    "status": resp.status_code,
                    "body": resp.text[:200],
                })
    except Exception as e:
        logger.warning("emqx_crl_reload_error", extra={"error": str(e)})
```

**Note:** The exact EMQX API endpoint for listener restart may differ by version. Check EMQX 5.x docs. Alternatives:
- `PUT /api/v5/listeners/ssl:external` with the full listener config
- `POST /api/v5/listeners/ssl:external/restart`
- Or EMQX may auto-reload CRL files if `ssl_options.crl_check` is enabled

### Step 3: Call the notification after CRL regeneration

In the `regenerate_crl()` function, after the CRL file is written successfully, add:

```python
await _notify_broker_crl_update()
```

Remove the old comment about SIGHUP:

```python
# OLD (remove):
# NOTE: Mosquitto does not auto-reload CRL files.
# In production, send SIGHUP to Mosquitto after CRL update:
#   docker kill --signal=SIGHUP iot-mqtt
```

### Step 4: Add env vars to docker-compose.yml

In the `ops_worker` service environment:

```yaml
      EMQX_API_URL: "http://iot-mqtt:18083"
      EMQX_API_USER: "admin"
      EMQX_DASHBOARD_PASSWORD: "${EMQX_DASHBOARD_PASSWORD}"
```

### Step 5: Add httpx dependency

Check if `httpx` is already in the ops_worker's `requirements.txt`. If not, add it. Alternatively, use `aiohttp` if that's already a dependency.

## Important Notes

- The CRL file is still written to disk — EMQX reads it from the volume mount. The API call just triggers a reload.
- If EMQX supports automatic CRL file watching (inotify), the API call may not be needed. Check EMQX docs.
- The cert volume is mounted read-only in EMQX (`:ro`), but the ops_worker has write access to the same directory. Make sure the volume mount allows both.
- Fallback: if the EMQX API call fails, the CRL file is still updated. EMQX will pick it up on next restart.

## Verification

```bash
# Revoke a test device cert, then check CRL reload
docker compose exec ops_worker python -c "
import asyncio
from workers.certificate_worker import regenerate_crl, _notify_broker_crl_update
# ... trigger CRL regen
"

# Check EMQX picked up the new CRL
docker compose logs --tail 10 mqtt | grep -i crl
```
