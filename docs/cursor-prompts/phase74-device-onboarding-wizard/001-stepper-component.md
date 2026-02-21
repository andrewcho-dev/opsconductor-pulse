# Prompt 001 — Stepper UI Component + Step Components

Read `frontend/src/components/ui/` to understand existing component patterns (button, badge, card styles).

## Create `frontend/src/components/ui/stepper.tsx`

A simple step indicator component:

```typescript
interface Step {
  id: number;
  label: string;
  description?: string;
}

interface StepperProps {
  steps: Step[];
  currentStep: number;   // 1-indexed
  completedSteps: number[];
}

export function Stepper({ steps, currentStep, completedSteps }: StepperProps) {
  // Renders horizontal step bar:
  // [1 Details] → [2 Tags & Groups] → [3 Provision] → [4 Credentials] → [5 Alert Rules]
  // Current step: highlighted/filled
  // Completed steps: checkmark
  // Future steps: greyed out
}
```

Use simple HTML/CSS — no external stepper library needed. Style consistent with the existing UI (check button/badge colors in existing components).

## Create Wizard Step Components

Create directory: `frontend/src/features/devices/wizard/`

### `Step1DeviceDetails.tsx`

Props: `{ onNext: (data: DeviceDetailsData) => void; initialData?: DeviceDetailsData }`

Form fields:
- Device Name (required, text)
- Device Type (required, select from known types: temperature/humidity/pressure/vibration/power/flow/level/gateway)
- Site (optional, select from `fetchSites()`)

"Next" button → calls `onNext(data)`

### `Step2TagsGroups.tsx`

Props: `{ onNext: (data: TagsGroupsData) => void; onBack: () => void; initialData?: TagsGroupsData }`

Fields:
- Tags (comma-separated text input)
- Device Groups (multi-select from `fetchDeviceGroups()`)

"Next" and "Back" buttons.

### `Step3Provision.tsx`

Props: `{ deviceData: CombinedWizardData; onSuccess: (creds: ProvisionResult) => void; onBack: () => void }`

On mount: automatically calls `provisionDevice(deviceData)`.
Shows spinner while provisioning.
On success: calls `onSuccess(credentials)`.
On error: shows error with "Retry" button.

### `Step4Credentials.tsx`

Props: `{ credentials: ProvisionResult; deviceName: string; onNext: () => void }`

Same content as `CredentialModal` but rendered inline (not modal).
Warning banner, copy buttons, Download .env button.
"Continue" button → `onNext()`.

### `Step5AlertRules.tsx`

Props: `{ deviceId: string; deviceType: string; onDone: () => void }`

Shows: "Would you like to add an alert rule for this device?"
- "Skip" → `onDone()`
- "Add Rule" → shows simplified rule form:
  - Metric name (pre-filled from device_type if known from ALERT_RULE_TEMPLATES)
  - Operator (select: GT/LT/GTE/LTE)
  - Threshold (number)
  - Severity (select: 1=Critical/2=Warning/3=Info)
  - Pre-fill button: "Load Defaults for {device_type}" — loads first matching template

On submit: calls `applyAlertRuleTemplates([templateId])` OR creates rule via `POST /customer/alert-rules`.
After save: shows "Rule created" confirmation, then "Done" → `onDone()`.

## Acceptance Criteria

- [ ] `Stepper` component in `components/ui/stepper.tsx`
- [ ] Step1–Step5 components in `features/devices/wizard/`
- [ ] Each step has `onNext`/`onBack`/`onDone` prop pattern
- [ ] `npm run build` passes
