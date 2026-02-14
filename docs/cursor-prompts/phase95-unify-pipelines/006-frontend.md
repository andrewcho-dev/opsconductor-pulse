# Phase 95 — Frontend: Unify to Single "Notification Channels" Concept

## Goal

Remove the split between "Integrations" (old) and "Notification Channels" (new) from the UI.
Customers should see ONE place to configure notifications: **Notification Channels**.

The old Integrations pages are retired from the navigation. The data still exists (migration ran),
but customers manage everything through the new unified UI.

---

## Step 1: Remove "Integrations" from sidebar navigation

### File to modify
Find the sidebar navigation component. Likely one of:
- `src/components/layout/Sidebar.tsx`
- `src/components/layout/Navigation.tsx`
- `src/App.tsx` (router definition)

Search for any nav item with label "Integrations" or route `/customer/integrations` and **remove it**.

Replace with a single "Notification Channels" nav item pointing to `/customer/notification-channels`
if it doesn't already exist.

---

## Step 2: Update NotificationChannelsPage to support all channel types

### File to modify
Locate the notification channels page. Likely:
- `src/pages/NotificationChannelsPage.tsx`
- `src/components/notifications/NotificationChannelsPage.tsx`

### Changes

#### 2a. Channel type selector in the Create Channel modal

Extend the `channel_type` dropdown to include all types:

```tsx
const CHANNEL_TYPES = [
  { value: "slack",      label: "Slack",           icon: "💬" },
  { value: "pagerduty",  label: "PagerDuty",        icon: "🚨" },
  { value: "teams",      label: "Microsoft Teams",  icon: "🏢" },
  { value: "webhook",    label: "HTTP Webhook",      icon: "🔗" },
  { value: "email",      label: "Email (SMTP)",      icon: "📧" },
  { value: "snmp",       label: "SNMP Trap",         icon: "📡" },
  { value: "mqtt",       label: "MQTT",              icon: "📨" },
];
```

#### 2b. Dynamic config form per channel type

The config form should show different fields depending on `channel_type`:

```tsx
// Slack
{ webhook_url: string }  // single field: "Webhook URL"

// PagerDuty
{ integration_key: string }  // single field: "Integration Key"

// Teams
{ webhook_url: string }  // single field: "Incoming Webhook URL"

// Webhook / HTTP
{ url: string, method: "POST"|"GET"|"PUT", headers: Record<string,string>, secret?: string }

// Email
{
  smtp: { host: string, port: number, username: string, password: string, use_tls: boolean },
  recipients: { to: string[], cc?: string[], bcc?: string[] },
  template?: { subject: string, body: string }
}

// SNMP
{ host: string, port: number (default 162), community: string, oid_prefix?: string, snmp_config?: object }

// MQTT
{ broker_host: string, broker_port: number (default 1883), topic: string, qos: 0|1|2, retain: boolean, username?: string, password?: string }
```

Implement as a component-per-type approach:
- `SlackChannelForm.tsx`
- `PagerDutyChannelForm.tsx`
- `TeamsChannelForm.tsx`
- `WebhookChannelForm.tsx`
- `EmailChannelForm.tsx`
- `SnmpChannelForm.tsx`
- `MqttChannelForm.tsx`

Each form component receives `config` and `onChange(config)` props.
The parent `ChannelModal.tsx` renders the appropriate form based on selected `channel_type`.

#### 2c. Routing rules: show new fields

The routing rule creation form should include the new routing fields added in migration 070:
- **Sites**: multi-select of sites in the tenant (or free-text)
- **Device prefix**: text input (e.g., "gw-" to match all gateway devices)
- **Deliver on**: checkbox group: `[OPEN, CLOSED, ACKNOWLEDGED]` (default: OPEN)
- **Priority**: number input (default 100; lower = higher priority)

---

## Step 3: Add "Migrated from legacy" badge on migrated channels

Channels that were migrated from the old integrations system have
`config.migrated_from_integration_id` set in their config JSON.

In the channel list, show a small "Migrated" badge on these channels so customers know
their existing integrations are already present. The badge can be removed after a release cycle.

```tsx
{channel.config?.migrated_from_integration_id && (
  <Badge variant="outline" className="text-xs text-muted-foreground ml-2">
    Migrated
  </Badge>
)}
```

---

## Step 4: Add delivery job tracking to channel detail

Each channel should show recent delivery history (from `notification_jobs`).
Add a "Recent Deliveries" tab or section in the channel detail view:

```
GET /customer/notification-jobs?channel_id={id}&limit=20
```

You need to add this endpoint in `routes/notifications.py`:

```python
@router.get("/notification-jobs")
async def list_notification_jobs(
    channel_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = Query(default=20, le=100),
    pool=Depends(get_db_pool),
    claims=Depends(require_customer),
):
    tenant_id = claims["tenant_id"]
    conditions = ["tenant_id = $1"]
    params = [tenant_id]
    if channel_id:
        params.append(channel_id)
        conditions.append(f"channel_id = ${len(params)}")
    if status:
        params.append(status)
        conditions.append(f"status = ${len(params)}")
    params.append(limit)
    where = " AND ".join(conditions)
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"SELECT * FROM notification_jobs WHERE {where} ORDER BY created_at DESC LIMIT ${len(params)}",
            *params
        )
    return [dict(r) for r in rows]
```

---

## Step 5: Hide old Integrations pages (do not delete the components yet)

Instead of deleting the old `IntegrationsPage.tsx`, add a redirect:

```tsx
// In router definition, replace the old integrations route:
// OLD: <Route path="/customer/integrations" element={<IntegrationsPage />} />
// NEW:
<Route
  path="/customer/integrations"
  element={<Navigate to="/customer/notification-channels" replace />}
/>
```

This ensures any bookmarked or linked old URLs redirect to the new page.

---

## Verify

1. Navigate to the old `/customer/integrations` URL — should redirect to notification-channels
2. Create a new Slack channel — should appear in notification_channels table
3. Create a new Email channel — should validate SMTP config, save successfully
4. Create a new SNMP channel — should save successfully
5. Existing migrated channels should show "Migrated" badge
6. Test button on a channel should return success/failure inline (not queued)
7. Routing rule creation should show site_ids, device_prefixes, deliver_on, priority fields
