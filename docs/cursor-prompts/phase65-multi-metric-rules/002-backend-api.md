# Prompt 002 — Backend API: Accept conditions in Create/Update

Read `services/ui_iot/routes/customer.py` — find `AlertRuleCreate` and `AlertRuleUpdate` Pydantic models and the create/update endpoints.

## Update Pydantic Models

Add `conditions` field to both models:

```python
from typing import Optional, List, Literal

class RuleCondition(BaseModel):
    metric_name: str
    operator: Literal["GT", "LT", "GTE", "LTE"]
    threshold: float

class RuleConditions(BaseModel):
    combinator: Literal["AND", "OR"] = "AND"
    conditions: List[RuleCondition] = Field(..., min_items=1, max_items=10)

class AlertRuleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    metric_name: Optional[str] = None     # single-condition mode
    operator: Optional[str] = None
    threshold: Optional[float] = None
    severity: int = Field(3, ge=0, le=5)
    duration_seconds: int = Field(0, ge=0)
    device_type: Optional[str] = None
    site_ids: Optional[List[str]] = None
    escalation_minutes: Optional[int] = None
    conditions: Optional[RuleConditions] = None  # NEW: multi-condition mode
    enabled: bool = True

# Apply same change to AlertRuleUpdate
```

## Update Create/Update Endpoints

In the INSERT/UPDATE SQL, include `conditions`:

```python
# In create_alert_rule:
conditions_json = body.conditions.model_dump() if body.conditions else None

row = await conn.fetchrow(
    """
    INSERT INTO alert_rules (tenant_id, name, ..., conditions)
    VALUES ($1, $2, ..., $N)
    RETURNING id, ...
    """,
    ..., json.dumps(conditions_json) if conditions_json else None
)
```

## Update list/get endpoints

Ensure `conditions` column is included in SELECT for rule detail responses.

## Acceptance Criteria

- [ ] `RuleCondition`, `RuleConditions` Pydantic models defined
- [ ] `conditions` field in AlertRuleCreate and AlertRuleUpdate
- [ ] conditions saved to DB as JSONB
- [ ] conditions returned in GET /alert-rules responses
- [ ] `pytest -m unit -v` passes
