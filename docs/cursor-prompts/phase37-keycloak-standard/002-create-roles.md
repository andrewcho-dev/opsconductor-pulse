# 002: Create Proper Realm Roles

## Task

Create the standard realm roles for the application.

## Roles to Create

| Role | Description | Scope |
|------|-------------|-------|
| `operator` | System monitoring and management | System-wide |
| `operator-admin` | Full system access, can create operators | System-wide |
| `tenant-admin` | Manage users within their organization | Per-org |
| `customer` | Standard user access | Per-org |

## Commands

```bash
# Login to Keycloak admin CLI
docker compose exec keycloak /opt/keycloak/bin/kcadm.sh config credentials \
  --server http://localhost:8080 --realm master --user admin --password admin_dev

# Create operator role
docker compose exec keycloak /opt/keycloak/bin/kcadm.sh create roles -r pulse \
  -s name=operator \
  -s description="System operator - monitoring and management across all tenants"

# Create operator-admin role
docker compose exec keycloak /opt/keycloak/bin/kcadm.sh create roles -r pulse \
  -s name=operator-admin \
  -s description="System administrator - full access, can manage operators"

# Create tenant-admin role
docker compose exec keycloak /opt/keycloak/bin/kcadm.sh create roles -r pulse \
  -s name=tenant-admin \
  -s description="Tenant administrator - manage users within organization"

# Note: 'customer' role already exists from earlier troubleshooting
# Update its description
docker compose exec keycloak /opt/keycloak/bin/kcadm.sh update roles/customer -r pulse \
  -s description="Standard tenant user - regular access within organization"

# Verify all roles exist
docker compose exec keycloak /opt/keycloak/bin/kcadm.sh get roles -r pulse --fields name,description
```

## Expected Output

```json
[
  { "name": "customer", "description": "Standard tenant user..." },
  { "name": "default-roles-pulse", "description": "..." },
  { "name": "offline_access", "description": "..." },
  { "name": "operator", "description": "System operator..." },
  { "name": "operator-admin", "description": "System administrator..." },
  { "name": "tenant-admin", "description": "Tenant administrator..." },
  { "name": "uma_authorization", "description": "..." }
]
```

## Role Hierarchy (Informational)

```
operator-admin
    └── operator

tenant-admin (within org)
    └── customer (within org)
```

Note: Keycloak role composites could be set up, but for simplicity we'll handle hierarchy in the application.
