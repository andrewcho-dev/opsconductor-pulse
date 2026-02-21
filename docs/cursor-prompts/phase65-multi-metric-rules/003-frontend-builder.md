# Prompt 003 — Frontend: Multi-Condition Rule Builder

Read `frontend/src/features/alerts/AlertRuleDialog.tsx` (or the rule create/edit form) fully.
Read `frontend/src/services/api/types.ts` for existing AlertRule type.

## Update AlertRule Type

In `frontend/src/services/api/types.ts`:

```typescript
export interface RuleCondition {
  metric_name: string;
  operator: 'GT' | 'LT' | 'GTE' | 'LTE';
  threshold: number;
}

export interface RuleConditions {
  combinator: 'AND' | 'OR';
  conditions: RuleCondition[];
}

// Add to AlertRule interface:
conditions?: RuleConditions | null;
```

## Update AlertRuleDialog.tsx

Add a toggle: **"Simple Rule"** (single metric) vs **"Multi-Condition Rule"** (multiple metrics).

**Simple Rule** (default): existing form unchanged.

**Multi-Condition Rule**: Replace the single metric_name/operator/threshold fields with:

1. **Combinator selector**: AND | OR radio buttons
2. **Conditions list**: each condition is a row with:
   - metric_name (text input)
   - operator (select: GT / LT / GTE / LTE)
   - threshold (number input)
   - "Remove" button (if more than 1 condition)
3. **"Add Condition" button**: adds a new empty condition row
4. Maximum 10 conditions (disable "Add" button at 10)

On submit: if multi-condition mode, serialize to `RuleConditions` shape. If simple mode, use `metric_name`/`operator`/`threshold` fields.

## Acceptance Criteria

- [ ] Simple/Multi-Condition toggle in AlertRuleDialog
- [ ] Multi-condition mode shows condition list with add/remove
- [ ] AND/OR combinator selector
- [ ] Max 10 conditions enforced
- [ ] Form serializes to correct `conditions` shape on submit
- [ ] `npm run build` passes
