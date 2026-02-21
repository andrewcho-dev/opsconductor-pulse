# Phase 203 Findings: Unit Tests Hitting Real DB

Root cause identified from `pytest -m unit -q` error scan: test modules indirectly hit a real `asyncpg` pool via shared test bootstrap (`tests/conftest.py`), which triggers `InvalidPasswordError` when local DB credentials do not match.

| Test file | Category | Why |
|---|---|---|
| `tests/unit/test_alert_actions.py` | Needs mock fix | DB access flows through shared `conftest` pool/bootstrap path |
| `tests/unit/test_alert_digest.py` | Needs mock fix | DB access flows through shared `conftest` pool/bootstrap path |
| `tests/unit/test_alert_dispatcher.py` | Needs mock fix | DB access flows through shared `conftest` pool/bootstrap path |
| `tests/unit/test_alert_dispatcher_service.py` | Needs mock fix | DB access flows through shared `conftest` pool/bootstrap path |
| `tests/unit/test_alert_escalation.py` | Needs mock fix | DB access flows through shared `conftest` pool/bootstrap path |
| `tests/unit/test_alert_rule_templates.py` | Needs mock fix | DB access flows through shared `conftest` pool/bootstrap path |
| `tests/unit/test_alert_rules.py` | Needs mock fix | DB access flows through shared `conftest` pool/bootstrap path |
| `tests/unit/test_anomaly_detection.py` | Needs mock fix | DB access flows through shared `conftest` pool/bootstrap path |
| `tests/unit/test_api_v2.py` | Needs mock fix | DB access flows through shared `conftest` pool/bootstrap path |
| `tests/unit/test_bulk_device_import.py` | Needs mock fix | DB access flows through shared `conftest` pool/bootstrap path |
| `tests/unit/test_device_api_tokens.py` | Needs mock fix | DB access flows through shared `conftest` pool/bootstrap path |
| `tests/unit/test_device_filters.py` | Needs mock fix | DB access flows through shared `conftest` pool/bootstrap path |
| `tests/unit/test_device_groups.py` | Needs mock fix | DB access flows through shared `conftest` pool/bootstrap path |
| `tests/unit/test_device_management.py` | Needs mock fix | DB access flows through shared `conftest` pool/bootstrap path |
| `tests/unit/test_device_uptime.py` | Needs mock fix | DB access flows through shared `conftest` pool/bootstrap path |
| `tests/unit/test_device_wizard.py` | Needs mock fix | DB access flows through shared `conftest` pool/bootstrap path |
| `tests/unit/test_email_sender.py` | Needs mock fix | DB access flows through shared `conftest` pool/bootstrap path |
| `tests/unit/test_email_validator.py` | Needs mock fix | DB access flows through shared `conftest` pool/bootstrap path |
| `tests/unit/test_evaluator.py` | Needs mock fix | DB access flows through shared `conftest` pool/bootstrap path |
| `tests/unit/test_evaluator_ack_silence.py` | Needs mock fix | DB access flows through shared `conftest` pool/bootstrap path |
| `tests/unit/test_fleet_ws.py` | Needs mock fix | DB access flows through shared `conftest` pool/bootstrap path |
| `tests/unit/test_ingest_core.py` | Needs mock fix | DB access flows through shared `conftest` pool/bootstrap path |
| `tests/unit/test_ingest_pipeline.py` | Needs mock fix | DB access flows through shared `conftest` pool/bootstrap path |
| `tests/unit/test_ingest_routes.py` | Needs mock fix | DB access flows through shared `conftest` pool/bootstrap path |
| `tests/unit/test_jwks_cache.py` | Needs mock fix | DB access flows through shared `conftest` pool/bootstrap path |
| `tests/unit/test_keycloak_admin.py` | Needs mock fix | DB access flows through shared `conftest` pool/bootstrap path |
| `tests/unit/test_keycloak_user_mgmt.py` | Needs mock fix | DB access flows through shared `conftest` pool/bootstrap path |
| `tests/unit/test_listen_notify.py` | Needs mock fix | DB access flows through shared `conftest` pool/bootstrap path |
| `tests/unit/test_maintenance_windows.py` | Needs mock fix | DB access flows through shared `conftest` pool/bootstrap path |
| `tests/unit/test_mqtt_sender.py` | Needs mock fix | DB access flows through shared `conftest` pool/bootstrap path |
| `tests/unit/test_mqtt_validator.py` | Needs mock fix | DB access flows through shared `conftest` pool/bootstrap path |
| `tests/unit/test_multi_metric_rules.py` | Needs mock fix | DB access flows through shared `conftest` pool/bootstrap path |
| `tests/unit/test_operator_frontend.py` | Needs mock fix | DB access flows through shared `conftest` pool/bootstrap path |
| `tests/unit/test_ops_worker.py` | Needs mock fix | DB access flows through shared `conftest` pool/bootstrap path |
| `tests/unit/test_pgbouncer_bypass.py` | Needs mock fix | DB access flows through shared `conftest` pool/bootstrap path |
| `tests/unit/test_prometheus_metrics.py` | Needs mock fix | DB access flows through shared `conftest` pool/bootstrap path |
| `tests/unit/test_rate_limiter_unit.py` | Needs mock fix | DB access flows through shared `conftest` pool/bootstrap path |
| `tests/unit/test_rate_limiting.py` | Needs mock fix | DB access flows through shared `conftest` pool/bootstrap path |
| `tests/unit/test_sites_endpoints.py` | Needs mock fix | DB access flows through shared `conftest` pool/bootstrap path |
| `tests/unit/test_snmp_sender.py` | Needs mock fix | DB access flows through shared `conftest` pool/bootstrap path |
| `tests/unit/test_snmp_sender_service.py` | Needs mock fix | DB access flows through shared `conftest` pool/bootstrap path |
| `tests/unit/test_snmp_validator.py` | Needs mock fix | DB access flows through shared `conftest` pool/bootstrap path |
| `tests/unit/test_structured_logging.py` | Needs mock fix | DB access flows through shared `conftest` pool/bootstrap path |
| `tests/unit/test_subscription_expiry.py` | Needs mock fix | DB access flows through shared `conftest` pool/bootstrap path |
| `tests/unit/test_subscription_service.py` | Needs mock fix | DB access flows through shared `conftest` pool/bootstrap path |
| `tests/unit/test_system_metrics_endpoints.py` | Needs mock fix | DB access flows through shared `conftest` pool/bootstrap path |
| `tests/unit/test_system_routes.py` | Needs mock fix | DB access flows through shared `conftest` pool/bootstrap path |
| `tests/unit/test_telemetry_export.py` | Needs mock fix | DB access flows through shared `conftest` pool/bootstrap path |
| `tests/unit/test_telemetry_gap.py` | Needs mock fix | DB access flows through shared `conftest` pool/bootstrap path |
| `tests/unit/test_telemetry_history.py` | Needs mock fix | DB access flows through shared `conftest` pool/bootstrap path |
| `tests/unit/test_tenant_isolation.py` | Needs mock fix | DB access flows through shared `conftest` pool/bootstrap path |
| `tests/unit/test_user_routes.py` | Needs mock fix | DB access flows through shared `conftest` pool/bootstrap path |

Decision for task 2: fix at shared test bootstrap (`tests/conftest.py`) so unit tests do not require a live PostgreSQL connection.
