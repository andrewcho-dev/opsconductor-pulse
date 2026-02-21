# Prompt 001 — Backend: GET /customer/alert-rule-templates

Read `services/ui_iot/routes/customer.py` — find the alert rule endpoints.

## Add Template Catalog

Define the preset catalog as a module-level constant (not in DB — static definitions):

```python
ALERT_RULE_TEMPLATES = [
    {"template_id": "temp_high", "device_type": "temperature", "name": "High Temperature",
     "metric_name": "temperature", "operator": "GT", "threshold": 85.0, "severity": 1,
     "duration_seconds": 60, "description": "Temperature exceeds 85°C for 60s"},
    {"template_id": "temp_low", "device_type": "temperature", "name": "Low Temperature",
     "metric_name": "temperature", "operator": "LT", "threshold": -10.0, "severity": 1,
     "duration_seconds": 60, "description": "Temperature below -10°C for 60s"},
    {"template_id": "humidity_high", "device_type": "humidity", "name": "High Humidity",
     "metric_name": "humidity", "operator": "GT", "threshold": 90.0, "severity": 2,
     "duration_seconds": 120, "description": "Humidity exceeds 90% for 120s"},
    {"template_id": "humidity_low", "device_type": "humidity", "name": "Low Humidity",
     "metric_name": "humidity", "operator": "LT", "threshold": 10.0, "severity": 2,
     "duration_seconds": 120, "description": "Humidity below 10% for 120s"},
    {"template_id": "pressure_high", "device_type": "pressure", "name": "High Pressure",
     "metric_name": "pressure", "operator": "GT", "threshold": 1100.0, "severity": 2,
     "duration_seconds": 0, "description": "Pressure exceeds 1100 hPa"},
    {"template_id": "pressure_low", "device_type": "pressure", "name": "Low Pressure",
     "metric_name": "pressure", "operator": "LT", "threshold": 900.0, "severity": 2,
     "duration_seconds": 0, "description": "Pressure below 900 hPa"},
    {"template_id": "vibration_high", "device_type": "vibration", "name": "High Vibration",
     "metric_name": "vibration", "operator": "GT", "threshold": 5.0, "severity": 1,
     "duration_seconds": 30, "description": "Vibration exceeds 5 m/s² for 30s"},
    {"template_id": "power_high", "device_type": "power", "name": "High Power Usage",
     "metric_name": "power", "operator": "GT", "threshold": 95.0, "severity": 2,
     "duration_seconds": 300, "description": "Power usage >95% for 5 minutes"},
    {"template_id": "power_loss", "device_type": "power", "name": "Power Loss",
     "metric_name": "power", "operator": "LT", "threshold": 5.0, "severity": 3,
     "duration_seconds": 300, "description": "Power below 5% for 5 minutes"},
    {"template_id": "flow_low", "device_type": "flow", "name": "Low Flow Rate",
     "metric_name": "flow", "operator": "LT", "threshold": 1.0, "severity": 2,
     "duration_seconds": 120, "description": "Flow rate below 1 unit for 120s"},
    {"template_id": "level_high", "device_type": "level", "name": "High Level",
     "metric_name": "level", "operator": "GT", "threshold": 90.0, "severity": 1,
     "duration_seconds": 60, "description": "Level exceeds 90% for 60s"},
    {"template_id": "level_low", "device_type": "level", "name": "Low Level",
     "metric_name": "level", "operator": "LT", "threshold": 10.0, "severity": 1,
     "duration_seconds": 60, "description": "Level below 10% for 60s"},
]
```

## Add Endpoint

```python
@router.get("/alert-rule-templates", dependencies=[Depends(require_customer)])
async def list_alert_rule_templates(device_type: Optional[str] = Query(None)):
    templates = ALERT_RULE_TEMPLATES
    if device_type:
        templates = [t for t in templates if t["device_type"] == device_type]
    return {"templates": templates, "total": len(templates)}
```

## Acceptance Criteria

- [ ] `ALERT_RULE_TEMPLATES` constant defined in customer.py
- [ ] GET /customer/alert-rule-templates returns all 12 templates
- [ ] `?device_type=temperature` filters to 2 templates
- [ ] No DB write — purely static
- [ ] `pytest -m unit -v` passes
