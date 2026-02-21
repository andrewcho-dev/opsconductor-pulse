# Phase 35: User Management via Keycloak

## Overview

Build user management UI and API that integrates with Keycloak Admin API for:
- **System-wide (Operator)**: Create/manage users across all tenants, assign operator roles
- **Tenant-level (Customer Admin)**: Create/manage users within their own tenant

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    OpsConductor UI                          │
│  ┌─────────────────────┐    ┌─────────────────────────────┐ │
│  │   Operator Portal   │    │     Customer Portal         │ │
│  │   /operator/users   │    │   /app/settings/users       │ │
│  └──────────┬──────────┘    └──────────────┬──────────────┘ │
└─────────────┼───────────────────────────────┼───────────────┘
              │                               │
              ▼                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    UI API (FastAPI)                         │
│  /operator/users/*        /customer/users/*                 │
│  (system-wide access)     (tenant-scoped access)            │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 Keycloak Admin API                          │
│  - Create/update/delete users                               │
│  - Assign roles (operator, customer, tenant-admin)          │
│  - Set user attributes (tenant_id)                          │
│  - Manage groups (optional)                                 │
└─────────────────────────────────────────────────────────────┘
```

## Roles

| Role | Scope | Capabilities |
|------|-------|--------------|
| `operator` | System-wide | Manage all tenants, all users, system config |
| `operator-admin` | System-wide | Create other operators |
| `tenant-admin` | Per-tenant | Manage users within their tenant |
| `customer` | Per-tenant | Standard user access |

## Execution Order

| # | File | Description |
|---|------|-------------|
| 1 | 001-keycloak-admin-service.md | Backend service to call Keycloak Admin API |
| 2 | 002-operator-user-api.md | Operator endpoints for system-wide user management |
| 3 | 003-customer-user-api.md | Customer endpoints for tenant-level user management |
| 4 | 004-operator-user-ui.md | Operator UI for user management |
| 5 | 005-customer-user-ui.md | Customer UI for tenant user management |
| 6 | 006-keycloak-setup.md | Keycloak realm configuration for roles |

## Prerequisites

- Keycloak running with admin credentials available
- Environment variables for Keycloak Admin API access
- Existing tenant structure
