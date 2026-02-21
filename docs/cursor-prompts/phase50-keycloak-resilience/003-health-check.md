# Prompt 003 — Health Check Keycloak Status

Read the existing `/healthz` endpoint in `services/ui_iot/app.py` or `routes/`.

## Update `/healthz`

Add a Keycloak reachability check that is **non-fatal** — a Keycloak timeout returns a warning, not a 500:

```python
@app.get("/healthz")
async def healthz():
    checks = {}

    # DB check (existing)
    ...

    # Keycloak check (new, non-fatal)
    try:
        from shared.jwks_cache import get_jwks_cache
        cache = get_jwks_cache()
        if cache is None or cache.is_stale():
            # attempt refresh with 2s timeout
            async with httpx.AsyncClient(timeout=2.0) as client:
                r = await client.get(os.environ.get("KEYCLOAK_JWKS_URI", ""))
            checks["keycloak"] = "ok" if r.status_code == 200 else f"http_{r.status_code}"
        else:
            checks["keycloak"] = "cached"
    except Exception as e:
        checks["keycloak"] = f"unreachable: {e}"
        # Do NOT set overall status to "error" — Keycloak is non-fatal

    overall = "ok" if checks.get("db") == "ok" else "degraded"
    return {"status": overall, "checks": checks}
```

## Acceptance Criteria

- [ ] `/healthz` includes `keycloak` key in checks
- [ ] Keycloak failure does not set overall status to "error"
- [ ] Cache hit returns `"cached"` without hitting Keycloak
- [ ] `pytest -m unit -v` passes
