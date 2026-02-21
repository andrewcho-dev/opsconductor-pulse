# Prompt 003 — Backend API: Create Anomaly Rules

Read `services/ui_iot/routes/customer.py` — find `AlertRuleCreate` and the create endpoint.

## Add Anomaly Rule Support

Update `AlertRuleCreate` to accept anomaly config:

```python
class AnomalyConditions(BaseModel):
    metric_name: str
    window_minutes: int = Field(60, ge=5, le=1440)
    z_threshold: float = Field(3.0, ge=1.0, le=10.0)
    min_samples: int = Field(10, ge=3, le=1000)
```

Add `anomaly_conditions: Optional[AnomalyConditions] = None` to `AlertRuleCreate`.

When `rule_type='anomaly'` and `anomaly_conditions` is set, store `anomaly_conditions.model_dump()` in the `conditions` column.

Validation: if `rule_type='anomaly'`, `anomaly_conditions` is required.

Also update `ALERT_TYPES` constant (if used for validation) to include `'ANOMALY'`.

## Acceptance Criteria

- [ ] `AnomalyConditions` Pydantic model defined
- [ ] `anomaly_conditions` field in AlertRuleCreate
- [ ] `rule_type='anomaly'` requires `anomaly_conditions`
- [ ] conditions stored as JSONB
- [ ] GET /alert-rules returns conditions for anomaly rules
- [ ] `pytest -m unit -v` passes
