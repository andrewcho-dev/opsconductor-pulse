# Phase 153 — MVNO Carrier Integration: Backend

## Overview

Add backend support for integrating with MVNO/IoT connectivity platforms (Hologram, 1NCE, Jasper, Twilio IoT, etc.) to provide:

1. **Carrier API credentials storage** — Per-tenant carrier integration configuration
2. **Diagnostics proxy** — Query device connection status, signal info, network errors
3. **Usage monitoring** — Sync data usage from carrier API
4. **Remote commands** — SIM activate/suspend/deactivate, device reboot via carrier
5. **Background sync** — Periodic job to pull usage data and update `device_connections`

## Architecture

```
Frontend → /api/v1/customer/carrier/* → CarrierService → Carrier API (Hologram, 1NCE, etc.)
                                              ↕
                                    carrier_integrations table
                                    device_connections table (data_used_mb synced)
```

The `CarrierService` is an abstraction layer with a pluggable provider pattern. Each carrier (Hologram, 1NCE, etc.) implements a provider interface. The API endpoints proxy through the service.

## Execution Order

1. `001-carrier-integrations-table.md` — DB table for carrier API credentials
2. `002-carrier-service.md` — Pluggable carrier service abstraction
3. `003-carrier-routes.md` — API endpoints for diagnostics, usage, remote commands
4. `004-usage-sync-worker.md` — Background job to periodically sync usage data
