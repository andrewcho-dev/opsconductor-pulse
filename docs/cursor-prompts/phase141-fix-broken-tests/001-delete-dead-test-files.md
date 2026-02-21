# Task 1: Delete Test Files for Removed Services

## Context

Phase 138 removed the `delivery_worker` service entirely. Three test files still import from the deleted modules (`email_sender`, `mqtt_sender`, `snmp_sender` from `services/delivery_worker/`). These files cause `ModuleNotFoundError` during pytest collection.

## Action

Delete these 3 files:

```
tests/unit/test_delivery_email_sender.py
tests/unit/test_delivery_mqtt_sender.py
tests/unit/test_delivery_snmp_sender.py
```

## Commands

```bash
rm tests/unit/test_delivery_email_sender.py
rm tests/unit/test_delivery_mqtt_sender.py
rm tests/unit/test_delivery_snmp_sender.py
```

## Why

- `test_delivery_email_sender.py` imports `email_sender` (deleted)
- `test_delivery_mqtt_sender.py` imports `mqtt_sender` (deleted)
- `test_delivery_snmp_sender.py` imports `snmp_sender` (deleted)

There is no code left to test — the service was fully removed.
