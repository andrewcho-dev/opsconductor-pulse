# Phase 89 — Guided Setup Wizard

## File
`frontend/src/features/devices/wizard/SetupWizard.tsx`

The route `/devices/wizard` already exists but points to a placeholder.
Replace it with this multi-step wizard.

## Step structure

```
[Step 1] → [Step 2] → [Step 3] → [Step 4]
Identity    Tags        Rules      Credentials
```

Step indicator: 4 dots at the top of the modal, filled up to current step.

## Step 1 — Device Identity

Fields:
- Device ID (text, required, pattern `/^[a-z0-9][a-z0-9-_]*$/`, error if invalid)
- Display Name (text, optional)
- Model / Device Type (text, optional)
- Site (select, populated from `GET /api/v2/sites` or `fetchSites`)

## Step 2 — Tags & Metadata

- Dynamic tag rows: `[key input]` `[value input]` `[× remove]`
- [+ Add Tag] button
- Notes (textarea, optional)

## Step 3 — Alert Rules

- Fetch `GET /customer/alert-rules` — show as checkbox list
- Columns: Rule Name | Metric | Threshold
- User selects which rules to apply to this device post-provisioning
- "Skip" button advances without applying rules

## Step 4 — Credentials (final)

Shown after successful `POST /provision/device`.

Display:
- Device ID (read-only)
- API Token (masked, reveal/copy button)
- MQTT Topic (read-only)
- "Download device-{id}.env" button

Generates `.env` file content:
```
DEVICE_ID=xxx
API_TOKEN=xxx
MQTT_TOPIC=xxx
```

Warning banner: "These credentials are shown once. Store them securely."

## Navigation

- Back / Next buttons; Next disabled while async calls are in-flight
- Cancel: confirm dialog if step > 1 ("Abandon setup? Your device won't be provisioned.")
- On Step 3 "Finish": call POST /provision/device, then advance to Step 4
- After applying selected alert rules (POST per rule), show Step 4

## State

Hold all form data in a single `wizardState` object with `useReducer`.
The POST /provision/device call happens on Step 3 "Finish" click.

## Route
The existing `/devices/wizard` route already imports a placeholder —
replace that import with `SetupWizard`.
