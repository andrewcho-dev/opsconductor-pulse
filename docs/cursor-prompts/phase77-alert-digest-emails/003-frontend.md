# Prompt 003 — Frontend: Digest Settings UI

## Create `frontend/src/features/alerts/DigestSettingsCard.tsx`

A settings card that shows current alert digest preferences:
- Frequency selector: Daily / Weekly / Disabled (radio or select)
- Email address input (pre-filled from current user's email if available)
- "Save" button → PUT /customer/alert-digest-settings
- Success toast on save

## Add API client functions in `frontend/src/services/api/alerts.ts`

```typescript
export async function getAlertDigestSettings(): Promise<AlertDigestSettings>
export async function updateAlertDigestSettings(settings: AlertDigestSettings): Promise<void>

interface AlertDigestSettings {
  frequency: 'daily' | 'weekly' | 'disabled';
  email: string;
}
```

## Wire into existing alerts page or settings

Add `<DigestSettingsCard />` to a logical location — either:
- A new "Notification Preferences" section at the bottom of the Alerts page, OR
- The existing Settings page if one exists for customers

## Acceptance Criteria
- [ ] DigestSettingsCard.tsx exists
- [ ] Frequency selector + email input
- [ ] Save calls PUT endpoint
- [ ] `npm run build` passes
