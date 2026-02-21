# Phase 91 — Frontend: Notification Channels + Routing Rules UI

## New files
- `frontend/src/features/notifications/NotificationChannelsPage.tsx`
- `frontend/src/features/notifications/ChannelModal.tsx`
- `frontend/src/features/notifications/RoutingRulesPanel.tsx`
- `frontend/src/services/api/notifications.ts`

## API service: notifications.ts

```typescript
export type ChannelType = 'slack' | 'pagerduty' | 'teams' | 'webhook';

export interface NotificationChannel {
  channel_id: number;
  name: string;
  channel_type: ChannelType;
  config: Record<string, string>;
  is_enabled: boolean;
  created_at: string;
}

export interface RoutingRule {
  rule_id: number;
  channel_id: number;
  min_severity?: number;
  alert_type?: string;
  device_tag_key?: string;
  device_tag_val?: string;
  throttle_minutes: number;
  is_enabled: boolean;
}

export async function listChannels(): Promise<{ channels: NotificationChannel[] }>
export async function createChannel(body: Omit<NotificationChannel, 'channel_id' | 'created_at'>): Promise<NotificationChannel>
export async function updateChannel(id: number, body: Partial<NotificationChannel>): Promise<NotificationChannel>
export async function deleteChannel(id: number): Promise<void>
export async function testChannel(id: number): Promise<{ ok: boolean; error?: string }>

export async function listRoutingRules(): Promise<{ rules: RoutingRule[] }>
export async function createRoutingRule(body: Omit<RoutingRule, 'rule_id'>): Promise<RoutingRule>
export async function updateRoutingRule(id: number, body: Partial<RoutingRule>): Promise<RoutingRule>
export async function deleteRoutingRule(id: number): Promise<void>
```

## NotificationChannelsPage layout

```
PageHeader: "Notification Channels"   [Add Channel button]

┌─────────────────────────────────────────────────────────┐
│ Name        │ Type       │ Status  │ Actions            │
│─────────────┼────────────┼─────────┼────────────────────│
│ Ops Slack   │ 🟢 Slack   │ Enabled │ Test  Edit  Delete │
│ PD Primary  │ 🔴 PagerDuty│ Enabled │ Test  Edit  Delete │
└─────────────────────────────────────────────────────────┘

── Routing Rules ─────────────────────────────────────────
[+ Add Rule]

┌──────────────┬──────────────┬──────────┬────────────────┐
│ Channel      │ Min Severity │ Type     │ Throttle       │
│──────────────┼──────────────┼──────────┼────────────────│
│ Ops Slack    │ HIGH (4)     │ any      │ 15m            │
│ PD Primary   │ CRITICAL (5) │ any      │ 5m             │
└──────────────┴──────────────┴──────────┴────────────────┘
```

"Test" button: calls `testChannel(id)`, shows toast "✓ Test sent" or "✗ Error: ..."

## ChannelModal (create / edit)

shadcn Dialog with:

**Common fields:**
- Name (text, required)
- Channel Type (select: Slack / PagerDuty / Teams / Webhook)
- Is Enabled (toggle)

**Type-specific config fields** (shown conditionally):

Slack:
- Webhook URL (text, required, placeholder "https://hooks.slack.com/services/...")

PagerDuty:
- Integration Key (text, required, placeholder "32-char key from PD service")

Teams:
- Webhook URL (text, required, placeholder "https://outlook.office.com/webhook/...")

Webhook:
- URL (text, required)
- Method (select: POST / PUT, default POST)
- Headers (dynamic key/value rows, optional)
- HMAC Secret (password input, optional — label "Signing secret")

**Security note** below config fields:
> "Credentials are stored encrypted. Existing secrets are masked in this form."

## RoutingRuleModal (inline or small dialog)

Fields:
- Channel (select from existing channels)
- Min Severity (select: Any / LOW(1) / MEDIUM(3) / HIGH(4) / CRITICAL(5))
- Alert Type (text, optional, placeholder "e.g. high_cpu — leave blank for all")
- Device Tag Key (text, optional)
- Device Tag Value (text, optional)
- Throttle (number input + "minutes" label, default 0)
- Enabled (toggle)

## Route + Sidebar

- Route `/notifications` in `router.tsx`
- Add "Notifications" link under Monitoring group in `AppSidebar.tsx`
  (below Escalation link added in Phase 88)
