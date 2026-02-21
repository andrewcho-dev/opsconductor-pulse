# Phase 199 — Frontend Security and Type Safety

## Goal

Fix four frontend issues found in the code review: unvalidated WebSocket message parsing (runtime type bypass), hardcoded MQTT broker URL, `as any` casts in form handling, and duplicated authentication utilities across API client files.

## Current State (problem)

1. **Unvalidated WS messages** (`manager.ts:64`): `JSON.parse(event.data) as WsServerMessage` — no runtime validation. A malformed server message crashes the UI or silently corrupts state.
2. **Hardcoded broker URL** (`services/api/devices.ts`): `broker_url: "mqtt://localhost:1883"` — always wrong in production.
3. **`as any` casts** (`AlertRuleDialog.tsx:387, 448-450`): Resolver and error object type bypasses lose type safety on the form's most complex component.
4. **Duplicated auth utilities** (`client.ts` and `deadLetter.ts` both define `getCsrfToken()` and `getAuthHeaders()`): Two sources of truth for authentication logic.

## Target State

- WebSocket messages are validated at runtime with Zod before being processed.
- MQTT broker URL comes from `import.meta.env.VITE_MQTT_BROKER_URL`.
- AlertRuleDialog uses typed error access without `as any`.
- Auth utilities are defined once in `client.ts` and imported everywhere else.

## Execution Order

| Step | File | What | Depends On |
|------|------|------|------------|
| 1 | `001-websocket-message-validation.md` | Add Zod validation to WS message handler | — |
| 2 | `002-mqtt-broker-url-env.md` | Move MQTT broker URL to env var | — |
| 3 | `003-alert-rule-dialog-types.md` | Remove `as any` casts in AlertRuleDialog | — |
| 4 | `004-dedup-auth-utilities.md` | Consolidate auth utilities to single location | — |
| 5 | `005-update-documentation.md` | Update affected docs | Steps 1–4 |

## Verification

```bash
# No unvalidated WS message casts
grep -n 'as WsServerMessage' frontend/src/services/websocket/manager.ts
# Must return zero results

# No hardcoded localhost:1883
grep -rn 'localhost:1883\|mqtt://localhost' frontend/src/
# Must return zero results

# No as any in AlertRuleDialog resolver
grep -n 'as any' frontend/src/features/alerts/AlertRuleDialog.tsx
# Must return zero results or show only documented intentional casts

# No duplicate getCsrfToken
grep -rn 'function getCsrfToken\|const getCsrfToken' frontend/src/services/
# Must appear exactly once
```

## Documentation Impact

- No external-facing docs change. Frontend development conventions may be updated.
