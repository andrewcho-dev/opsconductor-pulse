# Commit and Push All Work

Run the following commands in order:

## Step 1: Check status
```bash
git status
git diff --stat
```

## Step 2: Stage all changes
```bash
git add -A
```

## Step 3: Commit
```bash
git commit -m "Add phases 71–74: maintenance windows, telemetry gap detection, operator metrics dashboard, device onboarding wizard

- Phase 71: migration 062, maintenance window CRUD endpoints, is_in_maintenance() evaluator check, MaintenanceWindowsPage, 9 unit tests
- Phase 72: migration 063, NO_TELEMETRY alert type, check_telemetry_gap() evaluator, TelemetryGapConditions, AlertRuleDialog Data Gap mode, 7 unit tests
- Phase 73: SystemMetricsPage with 4 ECharts panels, fetchSystemMetricsLatest/History API client, /operator/system-metrics route, 3 unit tests
- Phase 74: Stepper component, 5-step DeviceOnboardingWizard, /devices/wizard route, Guided Setup entry point, 4 unit tests

681 unit tests passing, frontend build clean."
```

## Step 4: Push
```bash
git push origin main
```

## Step 5: Confirm
```bash
git log --oneline -5
```

Report the output of the final `git log` command.
