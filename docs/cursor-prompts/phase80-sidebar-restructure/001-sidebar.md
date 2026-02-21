# Prompt 001 — Restructure AppSidebar

Read `frontend/src/components/layout/AppSidebar.tsx` fully before making any changes.

## New nav group structure for customer role:

### Group 1: Overview (never collapsed, always visible)
- Dashboard → /dashboard (LayoutDashboard icon)

### Group 2: Fleet (collapsible, default open)
- Sites → /sites (Building2)
- Devices → /devices (Cpu)
- Device Groups → /device-groups (Layers)  ← change icon from Cpu to Layers
- Onboarding Wizard → /devices/wizard (Wand2)

### Group 3: Monitoring (collapsible, default open)
- Alerts → /alerts (Bell) [+ live badge showing open alert count]
- Alert Rules → /alert-rules (ShieldAlert)
- Maintenance → /maintenance-windows (CalendarOff)

### Group 4: Data & Integrations (collapsible, default collapsed)
- Telemetry / Metrics → /metrics (Gauge)
- Delivery Log → /delivery-log (Activity)
- Webhooks → /integrations/webhooks (Webhook)
- Email → /integrations/email (Mail)
- SNMP → /integrations/snmp (Network)
- MQTT → /integrations/mqtt (Radio)
- Export → /devices (link to devices with export action noted in label as "Export")

### Group 5: Settings (collapsible, default collapsed)
- Subscription → /subscription (CreditCard)
- Team → /users (Users) [only if canManageUsers]
- Notification Prefs → /alerts (scroll to digest section — same route)

## Implementation pattern

Use shadcn/ui `Collapsible` component (already available via @/components/ui/collapsible)
for each group. Each group header is clickable and toggles open/collapsed state.
Store collapsed state in localStorage keyed by group name so it persists across page loads.

Pattern:
```typescript
const [fleetOpen, setFleetOpen] = useState(() => {
  return localStorage.getItem('sidebar-fleet') !== 'false';
});
// on toggle: localStorage.setItem('sidebar-fleet', String(!fleetOpen))
```

Show a right-pointing chevron (ChevronRight) when collapsed, down-pointing (ChevronDown) when open.
Chevron appears on the right side of the group header label.

## Keep the Integrations section separate label

Remove the old separate `integrationNav` array — merge integrations into the
"Data & Integrations" group above.

## Operator nav

Keep operator nav groups as-is but also make them collapsible with the same pattern:
- Group: Overview (index, system-metrics)
- Group: Tenants (tenants, subscriptions)
- Group: Users & Audit (users, audit-log)
- Group: System (devices, system, settings)

## Acceptance Criteria
- [ ] 5 customer nav groups with correct items
- [ ] Each group is collapsible with chevron indicator
- [ ] Collapsed state persists in localStorage
- [ ] Integrations merged into Data & Integrations group
- [ ] Old flat single-group layout removed
- [ ] `npm run build` passes
