# 005 — Fix pytest.ini

## Context

`pytest.ini` line 35 hardcodes `/home/opsconductor/simcloud/services/ui_iot` in the `[coverage:paths]` section. This breaks on any other machine or CI runner. The relative paths `services/ui_iot` and `*/services/ui_iot` already cover the same mapping.

## Change

**File**: `pytest.ini`

Remove line 35 (`/home/opsconductor/simcloud/services/ui_iot`).

### Before (lines 31-41):
```ini
[coverage:paths]
source =
    services/ui_iot
    */services/ui_iot
    /home/opsconductor/simcloud/services/ui_iot
    middleware
    db
    routes
    services
    utils
    schemas
```

### After:
```ini
[coverage:paths]
source =
    services/ui_iot
    */services/ui_iot
    middleware
    db
    routes
    services
    utils
    schemas
```

## Commit

```bash
git add pytest.ini
git commit -m "fix: remove hardcoded absolute path from pytest.ini coverage config"
```

## Verification

```bash
grep -r "opsconductor" pytest.ini
# Should return nothing
```
