# Prompt 004 — Frontend: Anomaly Rule Form

Read `frontend/src/features/alerts/AlertRuleDialog.tsx` fully.
The Phase 65 prompt added Simple/Multi-Condition toggle — this adds a third mode: "Anomaly Detection".

## Add Anomaly Mode

In `AlertRuleDialog.tsx`, add a third rule type option:

```
[ Simple Threshold ] [ Multi-Condition ] [ Anomaly Detection ]
```

When **Anomaly Detection** selected, show:
- **Metric Name** (text input) — the metric to monitor
- **Window** (select: 15 min / 30 min / 1 hour / 6 hours / 24 hours) → maps to window_minutes
- **Z-Score Threshold** (number input, default 3.0, range 1.0–10.0) — how many stddevs = anomaly
- **Min Samples** (number input, default 10) — minimum readings required before firing

Hide the normal operator/threshold fields when Anomaly mode is selected.

On submit: set `rule_type='anomaly'` and `anomaly_conditions: { metric_name, window_minutes, z_threshold, min_samples }`.

## Update AlertRule Type

In `frontend/src/services/api/types.ts`:

```typescript
export interface AnomalyConditions {
  metric_name: string;
  window_minutes: number;
  z_threshold: number;
  min_samples: number;
}

// Add to AlertRule:
anomaly_conditions?: AnomalyConditions | null;
```

## Acceptance Criteria

- [ ] Third rule type "Anomaly Detection" in AlertRuleDialog
- [ ] Shows metric/window/z_threshold/min_samples fields
- [ ] Submits with `rule_type='anomaly'` and `anomaly_conditions`
- [ ] `AnomalyConditions` type in types.ts
- [ ] `npm run build` passes
