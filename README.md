# OpsConductor-Pulse

![Tests](https://github.com/OWNER/REPO/workflows/Tests/badge.svg)
![Coverage](https://codecov.io/gh/OWNER/REPO/branch/main/graph/badge.svg)

OpsConductor-Pulse is an edge telemetry, health, and signaling platform for managed IoT devices. Provides secure multi-tenant device ingestion, real-time state evaluation, alert generation, and operational dashboards.

## Quick Start

```bash
# Start all services
cd compose/
docker compose up -d --build

# View logs
docker compose logs -f

# Access services
# UI Dashboard: http://localhost:8080
# Provisioning API: http://localhost:8081
# MQTT Broker: localhost:1883
# PostgreSQL: localhost:5432
```

## Documentation

- [Architecture Overview](docs/ARCHITECTURE.md) - System design, services, and data flows
- [Integrations & Delivery](docs/INTEGRATIONS_AND_DELIVERY.md) - Alert delivery design and roadmap

## Security Notes

- **Do not commit secrets** - Update passwords and admin keys before production deployment
- **PROD vs DEV behavior** - In PROD mode, rejected events are not stored for security
- **Tenant isolation** - All customer data is strictly separated by tenant_id
- **Admin protection** - Administrative endpoints require X-Admin-Key header

## Repository Structure

```
compose/                 # Docker Compose configuration
docs/                    # Documentation
services/
  ingest_iot/           # Device ingestion and validation
  evaluator_iot/        # State evaluation and alert generation  
  ui_iot/               # Operator dashboard (read-only)
  provision_api/        # Device provisioning and admin APIs
simulator/
  device_sim_iot/       # Device simulation (testing only)
data/                   # Runtime data (gitignored)
logs/                   # Application logs (gitignored)
```

## Services Overview

- **ingest_iot**: MQTT/HTTP device ingress with authentication and quarantine
- **evaluator_iot**: Real-time device state tracking and alert generation
- **ui_iot**: Operational dashboard for fleet monitoring
- **provision_api**: Device registration and administrative functions
- **device_sim_iot**: Device simulation for development and testing

## Development

The system is designed for multi-tenant SaaS deployment with strong isolation guarantees between customers. See the Architecture documentation for detailed design information and security boundaries.
