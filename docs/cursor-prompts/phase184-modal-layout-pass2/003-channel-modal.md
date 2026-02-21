# Task 3: ChannelModal Restructure

## File

`frontend/src/features/notifications/ChannelModal.tsx`

## Current Problems

1. `max-w-2xl` (672px) — adequate width but wasted on single-column layout
2. Name, Channel Type, and Enabled toggle each take a full row — 3 rows for 3 simple fields
3. SMTP config has 6 fields (Host, Port, Username, Password, Use TLS, Recipients) — the `md:grid-cols-2` is fine but Host wastes a full-width row via `md:col-span-2`

## Changes

### A. Pack Name + Type + Enabled in one row

Replace the first 3 fields (lines 109-148) with a single 3-column grid:

```tsx
<div className="grid gap-4 sm:grid-cols-3">
  <div className="space-y-1">
    <label className="text-sm font-medium">Name</label>
    <Input
      value={draft.name}
      onChange={(e) => setDraft((prev) => ({ ...prev, name: e.target.value }))}
      placeholder="Channel name"
    />
  </div>
  <div className="space-y-1">
    <label className="text-sm font-medium">Channel Type</label>
    <Select
      value={draft.channel_type}
      onValueChange={(v) =>
        setDraft((prev) => ({ ...prev, channel_type: v as ChannelType, config: {} }))
      }
    >
      <SelectTrigger className="w-full">
        <SelectValue placeholder="Select type" />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="slack">Slack</SelectItem>
        <SelectItem value="pagerduty">PagerDuty</SelectItem>
        <SelectItem value="teams">Teams</SelectItem>
        <SelectItem value="webhook">Webhook</SelectItem>
        <SelectItem value="email">Email (SMTP)</SelectItem>
        <SelectItem value="snmp">SNMP Trap</SelectItem>
        <SelectItem value="mqtt">MQTT</SelectItem>
      </SelectContent>
    </Select>
  </div>
  <div className="flex items-end gap-2 pb-2">
    <Switch
      id="channel-enabled"
      checked={draft.is_enabled}
      onCheckedChange={(next) => setDraft((prev) => ({ ...prev, is_enabled: next }))}
    />
    <Label htmlFor="channel-enabled" className="text-sm">Enabled</Label>
  </div>
</div>
```

### B. SMTP section: pack Host + Port on one row

For the email config section (lines 208-326), change the SMTP Host from `md:col-span-2` (full width) to sharing a row with Port:

```tsx
{draft.channel_type === "email" && (
  <fieldset className="space-y-3 rounded-md border p-4">
    <legend className="px-1 text-sm font-medium">SMTP Configuration</legend>
    <div className="grid gap-3 sm:grid-cols-4">
      <div className="sm:col-span-3 space-y-1">
        <label className="text-xs font-medium text-muted-foreground">SMTP Host</label>
        <Input placeholder="smtp.example.com" value={...} onChange={...} />
      </div>
      <div className="space-y-1">
        <label className="text-xs font-medium text-muted-foreground">Port</label>
        <Input type="number" placeholder="587" value={...} onChange={...} />
      </div>
    </div>
    <div className="grid gap-3 sm:grid-cols-3">
      <div className="space-y-1">
        <label className="text-xs font-medium text-muted-foreground">Username</label>
        <Input placeholder="noreply@example.com" value={...} onChange={...} />
      </div>
      <div className="space-y-1">
        <label className="text-xs font-medium text-muted-foreground">Password</label>
        <Input type="password" placeholder="••••••••" value={...} onChange={...} />
      </div>
      <div className="flex items-end gap-2 pb-2">
        <Switch id="smtp-use-tls" checked={...} onCheckedChange={...} />
        <Label htmlFor="smtp-use-tls" className="text-sm">Use TLS</Label>
      </div>
    </div>
    <div className="space-y-1">
      <label className="text-xs font-medium text-muted-foreground">Recipients (comma separated)</label>
      <Input placeholder="ops@example.com, noc@example.com" value={...} onChange={...} />
    </div>
  </fieldset>
)}
```

### C. Wrap other channel configs in fieldsets too

For consistency, wrap each channel-type-specific config in a light fieldset:

```tsx
{draft.channel_type === "slack" && (
  <fieldset className="space-y-3 rounded-md border p-4">
    <legend className="px-1 text-sm font-medium">Slack Configuration</legend>
    <div className="space-y-1">
      <label className="text-xs font-medium text-muted-foreground">Webhook URL</label>
      <Input ... />
    </div>
  </fieldset>
)}
```

Apply the same fieldset pattern to: pagerduty, teams, webhook, snmp, mqtt sections. Keep the existing field layout within each — just wrap in the fieldset border.

For webhook config specifically, pack URL + Method + Secret in a better layout:

```tsx
{draft.channel_type === "webhook" && (
  <fieldset className="space-y-3 rounded-md border p-4">
    <legend className="px-1 text-sm font-medium">Webhook Configuration</legend>
    <div className="grid gap-3 sm:grid-cols-4">
      <div className="sm:col-span-2 space-y-1">
        <label className="text-xs font-medium text-muted-foreground">URL</label>
        <Input value={cfgValue("url")} onChange={(e) => setCfg("url", e.target.value)} />
      </div>
      <div className="space-y-1">
        <label className="text-xs font-medium text-muted-foreground">Method</label>
        <Select ...>...</Select>
      </div>
      <div className="space-y-1">
        <label className="text-xs font-medium text-muted-foreground">Signing Secret</label>
        <Input type="password" ... />
      </div>
    </div>
    {/* Headers textarea below if needed */}
  </fieldset>
)}
```

### D. No width change needed

`max-w-2xl` (672px) is fine for this dialog. At 672px, `sm:grid-cols-3` gives ~200px per column — sufficient for Name + Type + Enabled.

## Verification

```bash
cd frontend && npx tsc --noEmit
```

- Name + Type + Enabled on one row
- SMTP config in a labeled fieldset with compact layout
- All channel types wrapped in fieldsets
- All form submission still works
- All config values preserved correctly
