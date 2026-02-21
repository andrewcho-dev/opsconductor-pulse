# Phase 109 — Frontend: Condition Builder UI

## Context

Find the Alert Rule create/edit modal. Search:

```bash
grep -rn "AlertRule\|alert.rule\|alert_rule" frontend/src \
  --include="*.tsx" --include="*.jsx" -l | head -10
```

Read the file. Note the existing form fields (name, metric_name, operator,
threshold, severity, duration_minutes). The condition builder replaces the
single metric_name/operator/threshold row with a repeatable conditions list.

---

## Step 1: Add condition types

In `frontend/src/services/api/types.ts` (or wherever alert rule types live):

```typescript
export type RuleOperator = "GT" | "GTE" | "LT" | "LTE";
export type MatchMode = "all" | "any";

export interface RuleCondition {
  metric_name: string;
  operator: RuleOperator;
  threshold: number;
  duration_minutes?: number | null;
}

export interface AlertRule {
  // ... existing fields ...
  conditions: RuleCondition[];
  match_mode: MatchMode;
}

export interface AlertRuleCreate {
  name: string;
  severity: number;
  conditions: RuleCondition[];
  match_mode: MatchMode;
  // legacy fields kept for read-only display of old rules
  metric_name?: string;
  operator?: string;
  threshold?: number;
}
```

---

## Step 2: Create ConditionRow component

Create `frontend/src/features/alerts/ConditionRow.tsx`:

```tsx
import React from "react";
import { RuleCondition, RuleOperator } from "../../services/api/types";

const OPERATORS: { value: RuleOperator; label: string }[] = [
  { value: "GT",  label: "> greater than" },
  { value: "GTE", label: "≥ greater than or equal" },
  { value: "LT",  label: "< less than" },
  { value: "LTE", label: "≤ less than or equal" },
];

interface Props {
  condition: RuleCondition;
  index: number;
  onChange: (index: number, condition: RuleCondition) => void;
  onRemove: (index: number) => void;
  canRemove: boolean;
}

export function ConditionRow({ condition, index, onChange, onRemove, canRemove }: Props) {
  const update = (patch: Partial<RuleCondition>) =>
    onChange(index, { ...condition, ...patch });

  return (
    <div style={{ display: "flex", gap: "0.5rem", alignItems: "flex-start",
                  marginBottom: "0.5rem", padding: "0.5rem",
                  background: "#f8f9fa", borderRadius: "4px" }}>
      {/* Metric name */}
      <input
        type="text"
        placeholder="metric_name"
        value={condition.metric_name}
        onChange={e => update({ metric_name: e.target.value })}
        style={{ flex: 2, minWidth: 0 }}
      />

      {/* Operator */}
      <select
        value={condition.operator}
        onChange={e => update({ operator: e.target.value as RuleOperator })}
        style={{ flex: 2 }}
      >
        {OPERATORS.map(op => (
          <option key={op.value} value={op.value}>{op.label}</option>
        ))}
      </select>

      {/* Threshold */}
      <input
        type="number"
        placeholder="threshold"
        value={condition.threshold}
        onChange={e => update({ threshold: parseFloat(e.target.value) || 0 })}
        style={{ flex: 1, minWidth: 0 }}
      />

      {/* Duration (optional) */}
      <input
        type="number"
        placeholder="min (optional)"
        value={condition.duration_minutes ?? ""}
        min={1}
        onChange={e => update({
          duration_minutes: e.target.value === "" ? null : parseInt(e.target.value)
        })}
        style={{ flex: 1, minWidth: 0 }}
        title="Duration in minutes (leave blank for instant)"
      />

      {/* Remove button */}
      {canRemove && (
        <button
          type="button"
          onClick={() => onRemove(index)}
          style={{ flexShrink: 0, color: "red", background: "none",
                   border: "none", cursor: "pointer", fontSize: "1.1rem" }}
          title="Remove condition"
        >
          ×
        </button>
      )}
    </div>
  );
}
```

---

## Step 3: Update the alert rule modal

In the existing alert rule create/edit modal:

### Replace single-condition fields with condition builder

Remove (or hide) the existing individual `metric_name`, `operator`,
`threshold` inputs. Replace with:

```tsx
import { ConditionRow } from "./ConditionRow";
import { RuleCondition, MatchMode } from "../../services/api/types";

// In component state:
const [conditions, setConditions] = React.useState<RuleCondition[]>(
  rule?.conditions?.length
    ? rule.conditions
    : [{ metric_name: "", operator: "GT", threshold: 0, duration_minutes: null }]
);
const [matchMode, setMatchMode] = React.useState<MatchMode>(rule?.match_mode ?? "all");

// Handlers:
const updateCondition = (index: number, updated: RuleCondition) => {
  setConditions(prev => prev.map((c, i) => i === index ? updated : c));
};
const removeCondition = (index: number) => {
  setConditions(prev => prev.filter((_, i) => i !== index));
};
const addCondition = () => {
  setConditions(prev => [
    ...prev,
    { metric_name: "", operator: "GT", threshold: 0, duration_minutes: null }
  ]);
};
```

### JSX for the condition builder section

```tsx
{/* Match mode toggle — only show when 2+ conditions */}
{conditions.length > 1 && (
  <div style={{ marginBottom: "0.75rem" }}>
    <label style={{ marginRight: "0.5rem" }}>Match:</label>
    <label style={{ marginRight: "1rem" }}>
      <input type="radio" value="all" checked={matchMode === "all"}
             onChange={() => setMatchMode("all")} /> ALL (AND)
    </label>
    <label>
      <input type="radio" value="any" checked={matchMode === "any"}
             onChange={() => setMatchMode("any")} /> ANY (OR)
    </label>
  </div>
)}

{/* Column headers */}
<div style={{ display: "flex", gap: "0.5rem", fontSize: "0.75rem",
              color: "#666", marginBottom: "0.25rem" }}>
  <span style={{ flex: 2 }}>Metric</span>
  <span style={{ flex: 2 }}>Operator</span>
  <span style={{ flex: 1 }}>Threshold</span>
  <span style={{ flex: 1 }}>Duration (min)</span>
  <span style={{ width: "1.5rem" }}></span>
</div>

{/* Condition rows */}
{conditions.map((condition, index) => (
  <ConditionRow
    key={index}
    condition={condition}
    index={index}
    onChange={updateCondition}
    onRemove={removeCondition}
    canRemove={conditions.length > 1}
  />
))}

{/* Add condition button */}
<button type="button" onClick={addCondition}
        style={{ fontSize: "0.85rem", marginTop: "0.25rem" }}>
  + Add condition
</button>
```

### Include in submit payload

```typescript
const payload: AlertRuleCreate = {
  name: form.name,
  severity: form.severity,
  match_mode: matchMode,
  conditions: conditions.filter(c => c.metric_name.trim() !== ""),
};
```

---

## Step 4: Display match_mode and conditions in the rules table

In the alert rules list table, update the "Condition" column to show a
summary for multi-condition rules:

```tsx
const conditionSummary = (rule: AlertRule) => {
  if (!rule.conditions || rule.conditions.length === 0) {
    // Legacy display
    return `${rule.metric_name} ${rule.operator} ${rule.threshold}`;
  }
  if (rule.conditions.length === 1) {
    const c = rule.conditions[0];
    return `${c.metric_name} ${c.operator} ${c.threshold}`;
  }
  const joiner = rule.match_mode === "all" ? " AND " : " OR ";
  return rule.conditions
    .map(c => `${c.metric_name} ${c.operator} ${c.threshold}`)
    .join(joiner);
};

// In table cell:
<td>{conditionSummary(rule)}</td>
```

---

## Step 5: Build check

```bash
npm run build --prefix frontend 2>&1 | tail -10
```
