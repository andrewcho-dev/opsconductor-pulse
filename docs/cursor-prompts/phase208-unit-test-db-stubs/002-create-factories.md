# Task 2: Create tests/factories.py

## File to create
- `tests/factories.py`

## What to do

Create `tests/factories.py` with factory functions that return dict-like objects
matching the real DB column shapes used in this project.

Read the following files to understand the exact column names before writing factories:
- `services/ui_iot/routes/billing.py` — to see what columns are fetched from `tenants`
  and billing-related tables
- `services/ui_iot/routes/customer.py` — to see device/site columns
- `services/ui_iot/routes/operator.py` — to see tenant/user columns
- `db/migrations/` — scan for CREATE TABLE statements for `tenants`, `device_state`,
  `device_plans`, `subscriptions`

Then create factory functions. Each function must return a plain `dict` (NOT an
asyncpg Record — plain dicts work fine with `record["col"]` access in most route code,
and you can also make them support attribute access if needed via a simple wrapper).

Required factories (match actual column names from your file reads):

### `fake_tenant(overrides=None)`
Returns a dict representing one row from the `tenants` table.
Common fields seen in billing.py: `tenant_id`, `stripe_customer_id`,
`subscription_status`, `plan_id`, `subscription_id`, `trial_end`, `created_at`.
Use sensible defaults: `tenant_id="tenant-a"`, `subscription_status="active"`, etc.

### `fake_device(overrides=None)`
Returns a dict representing one row from `device_state`.
Common fields: `tenant_id`, `device_id`, `site_id`, `status`, `last_seen_at`.

### `fake_device_plan(overrides=None)`
Returns a dict representing one row from `device_plans`.
Common fields: `plan_id`, `name`, `max_devices`, `price_monthly`, `stripe_price_id`.

### `fake_site(overrides=None)`
Returns a dict representing one row from the sites table (check the schema).

### `fake_alert(overrides=None)`
Returns a dict representing one row from `fleet_alert`.

Each factory must accept an optional `overrides` dict and merge it into the default:
```python
def fake_tenant(overrides=None):
    record = {
        "tenant_id": "tenant-a",
        "stripe_customer_id": "cus_test123",
        "subscription_status": "active",
        # ... all other columns with sensible defaults
    }
    if overrides:
        record.update(overrides)
    return record
```

## Attribute-access wrapper

Many asyncpg query results are accessed as `row["col"]` but some code may use
`row.col`. Add a thin wrapper to support both:

```python
class FakeRecord(dict):
    """Dict subclass that also supports attribute-style access (row.col)."""
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)
```

Wrap all factory return values with `FakeRecord(...)`.

## After writing factories

Run a quick import check:
```bash
cd /home/opsconductor/simcloud && python -c "from tests.factories import fake_tenant, fake_device, fake_device_plan; print('OK')"
```
