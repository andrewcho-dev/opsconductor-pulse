# Task 1: Fix NATS Client Race Condition

## Context

`services/ui_iot/app.py:533-539` lazily initializes the NATS client inside a helper function. Two concurrent requests can both see `_nats_client is None` and both attempt to create a connection. The second connection is then orphaned (leaked).

## Actions

1. Read `services/ui_iot/app.py` in full.

2. Find the `_nats_client` global and the function that lazily initializes it.

3. Move the NATS connection logic into the FastAPI application's **lifespan** startup event. The app already has a startup sequence — add NATS connection there.

   Pattern:
   ```python
   # In the lifespan context manager (or @app.on_event("startup")):
   nats_url = require_env("NATS_URL")  # or optional_env if truly optional
   app.state.nats_client = await nats.connect(nats_url)
   logger.info("NATS connected", extra={"url": nats_url})
   ```

   And in the lifespan shutdown:
   ```python
   await app.state.nats_client.close()
   ```

4. Replace every call site that accesses the global `_nats_client` with `request.app.state.nats_client` (or use a FastAPI dependency that retrieves it from app state).

5. Remove the global `_nats_client` variable and the lazy initialization function.

6. Do not change any NATS publish/subscribe logic.

## Verification

```bash
grep -n '_nats_client\s*=\s*None\|_nats_client is None' services/ui_iot/app.py
# Must return zero results (no lazy init)

grep -n 'app.state.nats_client\|nats.connect' services/ui_iot/app.py
# Must show initialization in startup context
```
