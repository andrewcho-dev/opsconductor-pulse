# Prompt 001 — Split-Pane Layout

Read `frontend/src/features/devices/DeviceListPage.tsx` fully before making changes.

## Redesign DeviceListPage as a split-pane layout:

```
┌─────────────────────────────────────────────────────────────┐
│  Devices          [+ Add Device] [Import CSV] [Wizard]      │
├──────────────────────────┬──────────────────────────────────┤
│ Search: [__________]     │                                  │
│ Filter: [Status▾][Site▾] │     ← Select a device           │
├──────────────────────────│        to view details →         │
│ ● pump-alpha    ONLINE   │                                  │
│ ● sensor-b      OFFLINE  │                                  │
│ ● gateway-1     STALE    │                                  │
│                          │                                  │
│ [< Prev]   [Next >]      │                                  │
└──────────────────────────┴──────────────────────────────────┘
```

When a device is selected, right pane fills with DeviceDetailPane (Prompt 002).

### Implementation:

**State:**
```typescript
const [selectedDeviceId, setSelectedDeviceId] = useState<string | null>(null);
```

**Left pane** (fixed width ~380px, scrollable):
- Search input (filters by name/type client-side)
- Status filter dropdown (All / Online / Offline / Stale)
- Site filter dropdown (populated from /customer/sites)
- Device list: each row is a clickable card with:
  - Status dot (green=ONLINE, red=OFFLINE, yellow=STALE) — 10px filled circle
  - Device name (bold)
  - Device type (small text, muted)
  - Last seen (time ago, right-aligned)
  - Active alert count badge (red) if device has open alerts
  - Selected state: highlighted background (bg-primary/10, border-l-2 border-primary)
- Pagination: previous/next at bottom

**Right pane** (flex-1, fills remaining width):
- When no device selected: centered empty state "Select a device to view details"
- When device selected: `<DeviceDetailPane deviceId={selectedDeviceId} />`

**Responsive behavior:**
- On screens < lg: hide right pane, clicking device navigates to /devices/:id (existing behavior)
- On screens >= lg: show split pane

**Remove**: The existing "click row → navigate to DeviceDetailPage" behavior on lg+ screens.
Keep the navigate behavior only on mobile (< lg).

## Acceptance Criteria
- [ ] Split-pane layout on lg+ screens
- [ ] Left pane: search, status filter, site filter, device list with status dots
- [ ] Device rows show alert badge if open alerts exist
- [ ] Selected device highlighted with left border
- [ ] Right pane shows empty state or DeviceDetailPane
- [ ] Mobile: clicking navigates to DeviceDetailPage (unchanged)
- [ ] `npm run build` passes
