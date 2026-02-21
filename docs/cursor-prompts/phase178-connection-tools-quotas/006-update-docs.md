# Task 6: Update Documentation

## Objective

Update project documentation to reflect Phase 178's connection tools and quota visualization.

## Files to Update

1. `docs/development/frontend.md`
2. `docs/index.md`
3. `docs/services/ui-iot.md`

---

## 1. `docs/development/frontend.md`

### Frontmatter

- Set `last-verified: 2026-02-19`
- Add `178` to the `phases` array
- Add to `sources`:
  - `frontend/src/features/fleet/ToolsHubPage.tsx`
  - `frontend/src/features/fleet/ConnectionGuidePage.tsx`
  - `frontend/src/features/fleet/MqttTestClientPage.tsx`

### Content Changes

#### Update "Hub page inventory" table

Add a row for the Tools hub:

```markdown
| Tools | `/fleet/tools` | Connection Guide, MQTT Test Client |
```

#### Update "Navigation Structure" section

Update the Fleet line to include Tools:

```markdown
- **Fleet** — Getting Started*, Devices, Sites, Templates, Fleet Map, Device Groups, Updates (hub), Tools (hub)
```

#### Add "MQTT Test Client" section (after the Hub Pages section)

```markdown
## MQTT Test Client (Phase 178)

The MQTT Test Client (`/fleet/tools?tab=mqtt`) is a browser-based MQTT client using the `mqtt` npm package (mqtt.js). It connects via WebSocket to the EMQX broker.

Key implementation details:
- Connects to `ws://localhost:9001/mqtt` by default (EMQX WebSocket port)
- Manual credential entry: broker URL, client ID, password
- No auto-reconnect (`reconnectPeriod: 0`) — intentional for a debugging tool
- Message buffer capped at 200 messages
- Import: `import mqtt from "mqtt"` (Vite handles CJS → ESM)
```

#### Update "Feature Modules" list

Update the `fleet/` entry:

```markdown
- `fleet/` — fleet-level pages (Getting Started onboarding guide, Tools hub with Connection Guide + MQTT Test Client)
```

---

## 2. `docs/index.md`

### Frontmatter

- Set `last-verified: 2026-02-19`
- Add `178` to the `phases` array

### Content Changes

Add to the Features list (after the "Settings page with subcategory navigation" entry):

```markdown
- Connection tools: Connection Guide (code snippets for Python/Node.js/curl/Arduino) and MQTT Test Client
- Resource usage/quota KPI visualization on Home page
```

---

## 3. `docs/services/ui-iot.md`

### Frontmatter

- Set `last-verified: 2026-02-19`
- Add `178` to the `phases` array

### Content Changes

Add a new section after "Settings Route Structure (Phase 177)":

```markdown
## Connection Tools (Phase 178)

Phase 178 adds a Tools hub page at `/app/fleet/tools` with two tabs:

- **Connection Guide** (`?tab=guide`) — Language-specific code snippets (Python, Node.js, curl, Arduino) showing how to connect devices and send telemetry
- **MQTT Test Client** (`?tab=mqtt`) — Browser-based MQTT client using mqtt.js over WebSocket for publishing/subscribing to topics

The Home page (`/app/home`) also gains a "Resource Usage" section displaying quota KPI cards from the entitlements API (`GET /api/v1/customer/billing/entitlements`). The Billing page (`/app/settings/billing`) is refactored to use `KpiCard` components instead of custom progress bars for usage display.
```

---

## Verification

- All three docs have `last-verified: 2026-02-19` and `178` in their `phases` array
- `docs/development/frontend.md` documents the MQTT test client, Tools hub, and updated navigation
- `docs/index.md` lists connection tools and quota visualization as features
- `docs/services/ui-iot.md` documents the new `/fleet/tools` route and its tabs
- No stale information in updated sections
