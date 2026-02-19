---
last-verified: 2026-02-19
sources:
  - services/ui_iot/notifications/senders.py
  - services/ui_iot/routes/notifications.py
  - services/ui_iot/routes/message_routing.py
  - services/ingest_iot/ingest.py
phases: [1, 2, 91, 130, 138, 142, 160, 162]
---

# Integrations

> Outbound notifications and message routing integrations.

## Overview

Integrations cover two related capabilities:

1. Alert notifications: deliver alerts to external endpoints (Slack/PD/Teams/HTTP).
2. Message routing: route telemetry/events to destinations with dead-letter support.

## How It Works

### Notification channels (alerts)

Current supported channel types:

- Slack (incoming webhook)
- PagerDuty (Events API v2)
- Microsoft Teams (webhook)
- Generic HTTP webhook (HMAC signed)

Routing rules determine which channels receive which alerts using filters such as severity and alert type, with throttling behavior.

Historical note:

- The legacy webhook/SNMP/email/MQTT delivery pipeline (implemented as separate routing + delivery services) was removed in Phase 138.
- Legacy delivery tables may still exist for data retention and historical visibility.

### Message routing (telemetry/events)

Message routes match topics and forward to destinations (webhook, MQTT republish, PostgreSQL) with:

- Payload filters
- Enable/disable toggles
- Dead-letter queue for failed deliveries
- Replay and purge operations for recovery

Route delivery is processed asynchronously via NATS JetStream (subject `routes.{tenant_id}`) by the dedicated `route-delivery` service.

Retry behavior:

- JetStream consumer `max_deliver=3` retries failed deliveries up to 3 times
- On the final failure, the message is written to DLQ (`dead_letter_messages`) and terminated

## Database Schema

Key tables (high-level):

- `notification_channels`, `notification_routing_rules`, `notification_log`
- Message routing tables (routes + DLQ records, depending on migration set)
- Legacy retention: `integrations`, `integration_routes`, `delivery_jobs`, `delivery_attempts` (retained but not used for new delivery)

## API Endpoints

Notification channels and routing:

- `GET/POST/PUT/DELETE /api/v1/customer/notification-channels*`
- `GET/POST/PUT/DELETE /api/v1/customer/notification-routing-rules*`
- `GET /api/v1/customer/notification-jobs`

Message routing + DLQ:

- `GET/POST/PUT/DELETE /api/v1/customer/message-routes*`
- `GET/POST/DELETE /api/v1/customer/dead-letter*`

See: [Customer Endpoints](../api/customer-endpoints.md).

## Frontend

Primary pages:

- Notifications: channels + routing rules UI
- Message routing UI (feature module under `frontend/src/features/` depending on deployment)

## Configuration

Relevant knobs:

- Outbound webhook SSRF protections and URL validation behaviors (prod hardening)
- Rate limiting and throttling for delivery

## See Also

- [Alerting](alerting.md)
- [Security](../operations/security.md)
- [Service: ui-iot](../services/ui-iot.md)

