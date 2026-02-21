# Prompt 003 — Backend API: telemetry_gap Rule Type

Read `services/ui_iot/routes/customer.py` — find `AlertRuleCreate`, `AnomalyConditions`, and the Phase 67 pattern.

## Add Gap Rule Config

```python
class TelemetryGapConditions(BaseModel):
    metric_name: str
    gap_minutes: int = Field(10, ge=1, le=1440)
    min_expected_per_hour: Optional[int] = Field(None, ge=1)
```

Add `gap_conditions: Optional[TelemetryGapConditions] = None` to `AlertRuleCreate` and `AlertRuleUpdate`.

When `rule_type='telemetry_gap'`, require `gap_conditions` and store in `conditions` JSONB.

Also update `ALERT_TYPES` constant (if present) to include `'NO_TELEMETRY'`.

## Acceptance Criteria

- [ ] `TelemetryGapConditions` Pydantic model
- [ ] `gap_conditions` in AlertRuleCreate/Update
- [ ] `rule_type='telemetry_gap'` requires `gap_conditions`
- [ ] conditions stored as JSONB
- [ ] `pytest -m unit -v` passes
