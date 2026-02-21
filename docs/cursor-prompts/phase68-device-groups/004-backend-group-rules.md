# Prompt 004 — Backend: group_ids on Alert Rules

Read `services/ui_iot/routes/customer.py` — find `AlertRuleCreate`, `AlertRuleUpdate`, and the create/update endpoints.

## Update Models and Endpoints

Add `group_ids: Optional[list[str]] = None` to both `AlertRuleCreate` and `AlertRuleUpdate`.

In the INSERT/UPDATE SQL for alert rules, include `group_ids`:
```python
# In create_alert_rule INSERT:
# Add group_ids to the column list and $N parameter
```

Ensure `group_ids` is returned in GET /alert-rules responses (add to SELECT).

## Update Evaluator

In `services/evaluator_iot/evaluator.py`, when fetching rules (`fetch_tenant_rules()`), also select `group_ids`.

In the rule evaluation loop, if a rule has `group_ids` set, only evaluate it for devices that are members of one of those groups:

```python
if rule.get("group_ids"):
    # Check if device_id is in any of the rule's groups
    is_member = await conn.fetchval(
        """
        SELECT 1 FROM device_group_members
        WHERE tenant_id=$1 AND device_id=$2 AND group_id = ANY($3::text[])
        LIMIT 1
        """,
        tenant_id, device_id, rule["group_ids"]
    )
    if not is_member:
        continue  # skip rule for this device
```

## Acceptance Criteria

- [ ] `group_ids` field in AlertRuleCreate and AlertRuleUpdate
- [ ] `group_ids` stored in alert_rules table
- [ ] `group_ids` returned in GET /alert-rules
- [ ] Evaluator skips rules for devices not in specified groups
- [ ] `pytest -m unit -v` passes
