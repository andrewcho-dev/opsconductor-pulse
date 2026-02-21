# 136-001: Alert & Monitoring Forms

## Task
Convert AlertRuleDialog from raw `useState` (20+ state variables) to react-hook-form + zod.

## File
`frontend/src/features/alerts/AlertRuleDialog.tsx`

## Current State
This is the most complex form in the codebase with 20+ individual `useState` calls:
- `name, nameError, metricName, operator, threshold, severity, ruleMode, multiConditions, anomalyMetricName, ...`
- Manual validation scattered in `handleSubmit` (checking `name.trim()`, `metricName.trim()`, `Number.isNaN(threshold)`)
- Complex `useEffect` for initialization when `rule` prop changes (edit mode)
- Three rule modes: `simple`, `multi`, `anomaly`

## Migration Steps

### 1. Define Zod Schema
```typescript
const ruleOperators = ["GT", "GTE", "LT", "LTE", "EQ", "NEQ"] as const;
const ruleModes = ["simple", "multi", "anomaly"] as const;

const conditionSchema = z.object({
  metric_name: z.string().min(1, "Metric is required"),
  operator: z.enum(ruleOperators),
  threshold: z.coerce.number({ invalid_type_error: "Must be a number" }),
});

const alertRuleSchema = z.discriminatedUnion("ruleMode", [
  z.object({
    ruleMode: z.literal("simple"),
    name: z.string().min(3, "Name must be at least 3 characters").max(100),
    metric_name: z.string().min(1, "Metric name is required"),
    operator: z.enum(ruleOperators),
    threshold: z.coerce.number({ invalid_type_error: "Must be a number" }),
    severity: z.coerce.number().int().min(1).max(5),
    duration_seconds: z.coerce.number().int().min(0).optional(),
    device_group_id: z.string().optional(),
    enabled: z.boolean().default(true),
    // Add other simple-mode fields as found in current form
  }),
  z.object({
    ruleMode: z.literal("multi"),
    name: z.string().min(3, "Name must be at least 3 characters").max(100),
    conditions: z.array(conditionSchema).min(1, "At least one condition required"),
    match_mode: z.enum(["all", "any"]).default("all"),
    severity: z.coerce.number().int().min(1).max(5),
    duration_seconds: z.coerce.number().int().min(0).optional(),
    device_group_id: z.string().optional(),
    enabled: z.boolean().default(true),
  }),
  z.object({
    ruleMode: z.literal("anomaly"),
    name: z.string().min(3, "Name must be at least 3 characters").max(100),
    anomaly_metric_name: z.string().min(1, "Metric name is required"),
    anomaly_sensitivity: z.coerce.number().min(0).max(1).default(0.8),
    severity: z.coerce.number().int().min(1).max(5),
    device_group_id: z.string().optional(),
    enabled: z.boolean().default(true),
  }),
]);

type AlertRuleFormValues = z.infer<typeof alertRuleSchema>;
```

**Note**: Inspect the current form carefully. Adjust the schema above to match ALL fields currently tracked by useState variables. The discriminatedUnion on `ruleMode` ensures only mode-relevant fields are validated.

### 2. Initialize Form
```typescript
const form = useForm<AlertRuleFormValues>({
  resolver: zodResolver(alertRuleSchema),
  defaultValues: rule
    ? mapRuleToFormValues(rule)  // helper to convert API rule to form values
    : { ruleMode: "simple", name: "", metric_name: "", operator: "GT", threshold: 0, severity: 3, enabled: true },
});
```

### 3. Handle Edit Mode
Replace the large `useEffect` that manually sets 20+ state variables with:
```typescript
useEffect(() => {
  if (open && rule) {
    form.reset(mapRuleToFormValues(rule));
  } else if (open) {
    form.reset(defaultValues);
  }
}, [open, rule]);
```

### 4. Replace Manual Validation
Remove all manual checks in `handleSubmit`:
- Remove `if (!name.trim()) { setNameError(...) }`
- Remove `if (!metricName.trim()) return`
- Remove `if (Number.isNaN(thresholdValue)) return`
- These are now handled by the zod schema

### 5. Convert JSX to FormField
Replace each raw `<Input value={name} onChange={e => setName(e.target.value)} />` with:
```typescript
<FormField control={form.control} name="name" render={({ field }) => (
  <FormItem>
    <FormLabel>Rule Name *</FormLabel>
    <FormControl><Input {...field} placeholder="e.g., High Temperature Alert" /></FormControl>
    <FormMessage />
  </FormItem>
)} />
```

### 6. Handle Rule Mode Switching
Use `form.watch("ruleMode")` to conditionally render mode-specific fields:
```typescript
const ruleMode = form.watch("ruleMode");
// Then conditionally render simple/multi/anomaly fields
```

### 7. Submit Handler
```typescript
const onSubmit = async (values: AlertRuleFormValues) => {
  const payload = mapFormValuesToPayload(values);
  if (rule) {
    await updateMutation.mutateAsync({ rule_id: rule.rule_id, ...payload });
  } else {
    await createMutation.mutateAsync(payload);
  }
  form.reset();
  onOpenChange(false);
};
```

### 8. Remove All Individual useState Calls
Delete all 20+ `useState` calls that tracked form fields. Keep only non-form state like `saving` (but prefer `mutation.isPending` instead).

## Verification
```bash
cd frontend && npm run build
npx tsc --noEmit
```
- Open create alert rule dialog → leave name empty → submit → see "Name must be at least 3 characters"
- Switch to anomaly mode → metric required → see validation error
- Edit an existing rule → form pre-populated → change and save → works
- Submit valid data → rule created/updated successfully
