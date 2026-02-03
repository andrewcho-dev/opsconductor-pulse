# OpsConductor-Pulse

![Tests](https://github.com/OWNER/REPO/workflows/Tests/badge.svg)
![Coverage](https://codecov.io/gh/OWNER/REPO/branch/main/graph/badge.svg)

OpsConductor-Pulse is an edge telemetry, health, and signaling platform for managed IoT devices. Provides secure multi-tenant device ingestion, real-time state evaluation, alert generation, and operational dashboards.

## Features

- **Multi-tenant isolation** - Strict tenant separation via JWT claims and database RLS
- **Real-time device monitoring** - Heartbeat tracking, telemetry ingestion, stale device detection
- **Alert generation** - Automatic alerts for device health issues
- **Customer self-service** - Customers manage their own integrations and alert routing
- **Webhook delivery** - HTTP POST to customer endpoints with retry logic
- **SNMP trap delivery** - SNMPv2c and SNMPv3 trap support for network management systems
- **Email delivery** - SMTP email alerts with HTML/text templates
- **Operator dashboards** - Cross-tenant visibility with full audit trail

## Quick Start

```bash
# Start all services
cd compose/
docker compose up -d --build

# View logs
docker compose logs -f

# Access services
# Customer/Operator UI: http://localhost:8080
# Keycloak Admin: http://localhost:8180 (admin/admin_dev)
# Provisioning API: http://localhost:8081
# MQTT Broker: localhost:1883
# PostgreSQL: localhost:5432
```

## Authentication

OpsConductor-Pulse uses **Keycloak** for authentication. Users must login via Keycloak to access the UI.

### Default Users (Development)

| Username | Password | Role | Tenant |
|----------|----------|------|--------|
| customer1 | test123 | customer_admin | tenant-a |
| operator1 | test123 | operator | (all tenants) |

### User Roles

| Role | Access |
|------|--------|
| `customer_viewer` | Read-only access to own tenant's devices and alerts |
| `customer_admin` | Above + manage integrations and alert routes |
| `operator` | Cross-tenant read access with audit logging |
| `operator_admin` | Above + system settings |

## Documentation

- [Architecture Overview](docs/ARCHITECTURE.md) - System design, services, and data flows
- [Customer Plane Architecture](docs/CUSTOMER_PLANE_ARCHITECTURE.md) - Multi-tenant authentication design
- [Integrations & Delivery](docs/INTEGRATIONS_AND_DELIVERY.md) - Alert delivery design

## Alert Delivery

Customers can configure three types of integrations to receive alerts:

### Webhooks
- HTTP POST with JSON payload
- Automatic retry with exponential backoff
- SSRF protection (blocks internal IPs)

### SNMP Traps
- SNMPv2c (community string) and SNMPv3 (auth/priv)
- Custom OID prefix support
- Address validation (blocks internal networks)

### Email
- SMTP delivery with TLS support
- HTML and plain text templates
- Multiple recipients (to, cc, bcc)
- Customizable subject and body templates

## Security Notes

- **Do not commit secrets** - Update passwords and admin keys before production deployment
- **PROD vs DEV behavior** - In PROD mode, rejected events are not stored for security
- **Tenant isolation** - All customer data is strictly separated by tenant_id
- **RLS enforcement** - Database-level row security as defense-in-depth
- **Admin protection** - Administrative endpoints require X-Admin-Key header
- **SSRF prevention** - Customer webhook URLs are validated to prevent internal network access

## Repository Structure

```
compose/                 # Docker Compose configuration
  keycloak/             # Keycloak realm configuration
docs/                    # Documentation
db/
  migrations/           # Database migrations
services/
  ingest_iot/           # Device ingestion and validation
  evaluator_iot/        # State evaluation and alert generation
  ui_iot/               # Customer and operator dashboards
  provision_api/        # Device provisioning and admin APIs
  dispatcher/           # Alert-to-job dispatcher
  delivery_worker/      # Webhook and SNMP delivery
simulator/
  device_sim_iot/       # Device simulation (testing only)
tests/                   # Integration and unit tests
```

## Services Overview

| Service | Purpose |
|---------|---------|
| **ingest_iot** | MQTT/HTTP device ingress with authentication and quarantine |
| **evaluator_iot** | Real-time device state tracking and alert generation |
| **ui_iot** | Customer and operator dashboards |
| **provision_api** | Device registration and administrative functions |
| **dispatcher** | Matches alerts to integration routes, creates delivery jobs |
| **delivery_worker** | Delivers alerts via webhook or SNMP with retry |
| **device_sim_iot** | Device simulation for development and testing |

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=services

# Run specific test file
pytest tests/integration/test_customer_routes.py -v
```

### Database Migrations

Migrations are in `db/migrations/`. Run them manually:

```bash
PGPASSWORD=iot_dev psql -h localhost -U iot -d iotcloud -f db/migrations/001_webhook_delivery_v1.sql
```

## API Endpoints

### Customer Endpoints (JWT required)

| Method | Path | Description |
|--------|------|-------------|
| GET | /customer/dashboard | Customer dashboard |
| GET | /customer/devices | List tenant devices |
| GET | /customer/alerts | List tenant alerts |
| GET | /customer/integrations | List webhook integrations |
| POST | /customer/integrations | Create webhook integration |
| GET | /customer/integrations/snmp | List SNMP integrations |
| POST | /customer/integrations/snmp | Create SNMP integration |
| GET | /customer/integrations/email | List email integrations |
| POST | /customer/integrations/email | Create email integration |
| POST | /customer/integrations/email/{id}/test | Test email delivery |
| POST | /customer/integrations/{id}/test | Test delivery |

### Operator Endpoints (Operator role required)

| Method | Path | Description |
|--------|------|-------------|
| GET | /operator/dashboard | Cross-tenant dashboard |
| GET | /operator/devices | All devices |
| GET | /operator/alerts | All alerts |

### Admin Endpoints (X-Admin-Key required)

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/admin/devices | Provision device |
| POST | /api/admin/devices/{id}/activate-code | Generate activation code |
```
