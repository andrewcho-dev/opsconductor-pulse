# Prompt 004 — Frontend: Telemetry Gap Rule Form

Read `frontend/src/features/alerts/AlertRuleDialog.tsx` — find the three existing rule type modes (Simple, Multi-Condition, Anomaly Detection from Phase 67).

## Add Fourth Mode: "Data Gap Detection"

Add a fourth rule type toggle option: **"Data Gap"**.

When selected, show:
- **Metric Name** (text input) — which metric to monitor for gaps
- **Gap Threshold** (number input, default 10) — minutes without data before alert fires
- Label: "Alert if no {metric} data for {gap_minutes} minutes"

Hide the normal operator/threshold and anomaly fields when Data Gap mode is selected.

On submit: set `rule_type='telemetry_gap'` and `gap_conditions: { metric_name, gap_minutes }`.

## Update Types

In `frontend/src/services/api/types.ts`:

```typescript
export interface TelemetryGapConditions {
  metric_name: string;
  gap_minutes: number;
  min_expected_per_hour?: number;
}

// Add to AlertRule:
gap_conditions?: TelemetryGapConditions | null;
```

## Acceptance Criteria

- [ ] "Data Gap" fourth mode in AlertRuleDialog
- [ ] metric_name + gap_minutes fields
- [ ] Submits with `rule_type='telemetry_gap'` and `gap_conditions`
- [ ] `TelemetryGapConditions` in types.ts
- [ ] `npm run build` passes
