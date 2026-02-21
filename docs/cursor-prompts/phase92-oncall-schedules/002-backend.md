# Phase 92 — Backend: On-Call Schedules CRUD + Resolver

## 1. New router: `services/ui_iot/routes/oncall.py`

All endpoints require valid JWT and tenant context.

### Schedule endpoints
```
GET    /customer/oncall-schedules
POST   /customer/oncall-schedules
GET    /customer/oncall-schedules/{schedule_id}
PUT    /customer/oncall-schedules/{schedule_id}
DELETE /customer/oncall-schedules/{schedule_id}

GET    /customer/oncall-schedules/{schedule_id}/current
    → Returns {"responder": "alice@co.com", "layer": "Primary", "until": "2026-02-17T09:00:00Z"}

GET    /customer/oncall-schedules/{schedule_id}/timeline?days=14
    → Returns list of {start, end, responder, layer_name} shifts for the next N days
```

### Layer endpoints
```
POST   /customer/oncall-schedules/{schedule_id}/layers
PUT    /customer/oncall-schedules/{schedule_id}/layers/{layer_id}
DELETE /customer/oncall-schedules/{schedule_id}/layers/{layer_id}
```

### Override endpoints
```
GET    /customer/oncall-schedules/{schedule_id}/overrides
POST   /customer/oncall-schedules/{schedule_id}/overrides
DELETE /customer/oncall-schedules/{schedule_id}/overrides/{override_id}
```

### Pydantic models

```python
class OncallLayerIn(BaseModel):
    name: str = "Layer 1"
    rotation_type: Literal["daily", "weekly", "custom"] = "weekly"
    shift_duration_hours: int = 168
    handoff_day: int = Field(default=1, ge=0, le=6)
    handoff_hour: int = Field(default=9, ge=0, le=23)
    responders: List[str] = []  # email or name list in rotation order
    layer_order: int = 0

class OncallScheduleIn(BaseModel):
    name: str
    description: Optional[str] = None
    timezone: str = "UTC"
    layers: List[OncallLayerIn] = []

class OncallOverrideIn(BaseModel):
    layer_id: Optional[int] = None
    responder: str
    start_at: datetime
    end_at: datetime
    reason: Optional[str] = None
```

## 2. Current on-call resolver

In `services/ui_iot/oncall/resolver.py`:

```python
def get_current_responder(layer: dict, now: datetime) -> str:
    """
    Given a layer dict with responders list and rotation config,
    calculate who is currently on-call based on:
    1. How many full shifts have elapsed since the epoch (first handoff)
    2. responder = responders[shifts_elapsed % len(responders)]
    """
```

For `GET /customer/oncall-schedules/{id}/current`:
1. Load all layers for the schedule ordered by `layer_order`
2. Check overrides first — if NOW() falls within an override, return override responder
3. Otherwise use `get_current_responder(layer, now)` for the top layer

For `GET .../timeline?days=14`:
- Generate shift slots for each layer from NOW() to NOW()+days
- Merge with overrides (overrides take priority within their time window)
- Return sorted list of `{start, end, responder, layer_name, is_override}`

## 3. Link to escalation worker

In `services/ui_iot/workers/escalation_worker.py`, when firing a notification
for an escalation level that has `oncall_schedule_id` set:
- Call `get_current_responder` to resolve the current on-call person
- Use their email/name as the `notify_email` for that escalation fire
  (override the static `notify_email` on the level row)

## 4. Register router

In `services/ui_iot/app.py`:
```python
from services.ui_iot.routes.oncall import router as oncall_router
app.include_router(oncall_router)
```
