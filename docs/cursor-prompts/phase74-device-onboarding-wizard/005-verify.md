# Prompt 005 — Verify Phase 74

## Step 1: Unit Tests

```bash
pytest -m unit -v 2>&1 | tail -40
```

## Step 2: TypeScript Build

```bash
cd frontend && npm run build 2>&1 | tail -10
```

## Step 3: Checklist

### Components
- [ ] `frontend/src/components/ui/stepper.tsx` exists
- [ ] Step1DeviceDetails.tsx through Step5AlertRules.tsx in `features/devices/wizard/`
- [ ] DeviceOnboardingWizard.tsx orchestrates all steps

### Routing
- [ ] `/devices/wizard` route registered
- [ ] "Guided Setup" link in DeviceListPage

### Functionality
- [ ] Stepper shows current/completed steps
- [ ] Step3 auto-provisions on mount
- [ ] Step4 shows credentials with copy/download
- [ ] Step5 offers template-based quick rule creation

### Unit Tests
- [ ] test_device_wizard.py with 4 tests

## Report

Output PASS / FAIL per criterion.
