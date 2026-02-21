# Phase 88 — Backend: Escalation Policy CRUD + Worker

## 1. New router file
`services/ui_iot/routes/escalation.py`

Implement the following endpoints (all require valid JWT, operate within tenant context
via `tenant_connection(pool, tenant_id)`):

```
GET    /customer/escalation-policies
POST   /customer/escalation-policies
GET    /customer/escalation-policies/{policy_id}
PUT    /customer/escalation-policies/{policy_id}
DELETE /customer/escalation-policies/{policy_id}
```

### Pydantic models

```python
class EscalationLevelIn(BaseModel):
    level_number: int = Field(..., ge=1, le=5)
    delay_minutes: int = 15
    notify_email: Optional[str] = None
    notify_webhook: Optional[str] = None

class EscalationPolicyIn(BaseModel):
    name: str
    description: Optional[str] = None
    is_default: bool = False
    levels: List[EscalationLevelIn] = []

class EscalationLevelOut(EscalationLevelIn):
    level_id: int

class EscalationPolicyOut(BaseModel):
    policy_id: int
    tenant_id: str
    name: str
    description: Optional[str]
    is_default: bool
    levels: List[EscalationLevelOut]
    created_at: datetime
    updated_at: datetime
```

### POST /customer/escalation-policies logic
1. Insert into `escalation_policies`, get `policy_id` via `RETURNING policy_id`
2. Insert each level into `escalation_levels` (bulk insert)
3. If `is_default=True`, set all other policies for tenant to `is_default=FALSE` first
4. Return full policy with levels

### GET /customer/escalation-policies
- SELECT all policies for tenant
- For each, SELECT levels ORDER BY level_number
- Return list

### PUT /customer/escalation-policies/{policy_id}
- Verify policy belongs to tenant (404 if not)
- Update `escalation_policies` row
- DELETE all existing levels, re-insert from request body
- Return updated policy

### DELETE /customer/escalation-policies/{policy_id}
- Verify ownership (404 if not found)
- DELETE policy (levels cascade)
- Return 204

## 2. Worker: escalation tick
`services/ui_iot/workers/escalation_worker.py`

```python
async def run_escalation_tick(pool):
    """
    Called every 60s. For each OPEN alert where next_escalation_at <= NOW():
    1. Fetch the alert + its alert_rule.escalation_policy_id
    2. Look up the next escalation level (escalation_level + 1)
    3. If level exists:
       - Fire webhook via httpx.AsyncClient (fire-and-forget, log errors)
       - Send email if notify_email set (use send_email() helper or log placeholder)
       - Increment alert.escalation_level
       - Set next_escalation_at = NOW() + next_level.delay_minutes * interval
    4. If no more levels: set next_escalation_at = NULL
    """
```

Use `async with pool.acquire() as conn:` directly (not tenant_connection — this runs
as a system worker across all tenants).

## 3. Register
- `from services.ui_iot.routes.escalation import router as escalation_router`
  `app.include_router(escalation_router)` in `services/ui_iot/main.py`
- Add escalation worker loop in main startup:
  ```python
  asyncio.create_task(worker_loop(run_escalation_tick, pool, interval=60))
  ```
  (use the same `worker_loop` pattern as existing workers)
