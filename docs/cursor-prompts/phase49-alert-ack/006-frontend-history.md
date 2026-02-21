# Prompt 006 — Frontend: Alert History View (Status Filter Tabs)

Read `frontend/src/features/alerts/AlertListPage.tsx` fully.

## Add Status Filter Tabs

At the top of AlertListPage, add tab-style filter buttons:

- **Open** (default) — fetches `?status=OPEN`
- **Acknowledged** — fetches `?status=ACKNOWLEDGED`
- **Closed** — fetches `?status=CLOSED`
- **All** — fetches `?status=ALL`

The selected tab should be tracked in component state. When tab changes, reset `offset` to 0 and refetch.

## Update useAlerts Hook (or inline fetch)

Pass `status` param to the alerts fetch. The API already supports `GET /customer/alerts?status=X&limit=N&offset=N`.

Update the hook signature:
```typescript
function useAlerts(status: string, limit: number, offset: number)
```

The response now includes `total` and `status_filter` fields — use `total` for pagination display.

## Display Enhancements

- Show `acknowledged_by` and `acknowledged_at` columns when viewing ACKNOWLEDGED or ALL tabs
- Show `closed_at` column when viewing CLOSED or ALL tabs
- Show `silenced_until` as a badge on the row if it is set and in the future
- Total count display: "Showing X of Y alerts"

## Acceptance Criteria

- [ ] Four status tabs: Open / Acknowledged / Closed / All
- [ ] Switching tabs refetches with correct `?status=` param
- [ ] Pagination resets to page 1 on tab switch
- [ ] Total count shown from API response
- [ ] `acknowledged_by` / `acknowledged_at` shown in Acknowledged/All views
- [ ] `npm run build` passes
