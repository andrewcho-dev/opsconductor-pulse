Remove the legacy ?token= WebSocket fallback from `services/ui_iot/routes/api_v2.py`.

Read the file. Find the WebSocket upgrade handler — it currently accepts either `?ticket=` (new) or `?token=` (legacy fallback, added in phase 194 with a deprecation comment). Remove the entire `?token=` branch.

After removal the handler should:
- Accept `?ticket=` → call `consume_ws_ticket(ticket)` → get user context → proceed
- If no ticket or invalid ticket → reject with 4008

Nothing else. The `?token=` path is gone.

Run a quick grep to confirm:

```bash
grep -n 'token' services/ui_iot/routes/api_v2.py
```

Should show zero references to `?token=` query param handling. References to `access_token` or similar internal variable names are fine — just the URL query param fallback must be gone.

Also check the frontend isn't still sending `?token=` anywhere:

```bash
grep -rn 'token=' frontend/src/services/websocket/
```

Should be clean from phase 194 work. If not, fix it now.
