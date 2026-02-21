# 003: Create Acme Industrial Organization

## Task

Create the first Organization in Keycloak for Acme Industrial tenant.

## Prerequisites

- Organizations feature enabled (001)
- Keycloak restarted with `--features=organization`

## About Keycloak Organizations

Organizations in Keycloak 24+ provide:
- Tenant isolation within a single realm
- Organization-specific membership
- Organization appears in user tokens
- Users can belong to multiple organizations (if needed)

## Commands

```bash
# Login to Keycloak admin CLI
docker compose exec keycloak /opt/keycloak/bin/kcadm.sh config credentials \
  --server http://localhost:8080 --realm master --user admin --password admin_dev

# Create the Acme Industrial organization
docker compose exec keycloak /opt/keycloak/bin/kcadm.sh create organizations -r pulse \
  -s name="Acme Industrial" \
  -s alias=acme-industrial \
  -s enabled=true \
  -s description="Acme Industrial - Chicago manufacturing facility"

# Verify organization was created
docker compose exec keycloak /opt/keycloak/bin/kcadm.sh get organizations -r pulse

# Get the organization ID for later use
ORG_ID=$(docker compose exec keycloak /opt/keycloak/bin/kcadm.sh get organizations -r pulse \
  -q alias=acme-industrial --fields id --format csv 2>/dev/null | tail -1 | tr -d '"')
echo "Organization ID: $ORG_ID"
```

## Expected Output

```json
[
  {
    "id": "uuid-here",
    "name": "Acme Industrial",
    "alias": "acme-industrial",
    "enabled": true,
    "description": "Acme Industrial - Chicago manufacturing facility"
  }
]
```

## Mapping to Database

The organization `alias` (`acme-industrial`) matches the `tenant_id` in your database:
- `tenants.tenant_id = 'acme-industrial'`
- `device_registry.tenant_id = 'acme-industrial'`

This alignment is intentional - the Keycloak org alias IS the tenant ID.

## Creating Additional Organizations (Future)

When onboarding new tenants:

```bash
# Example: Create "Beta Corp" organization
docker compose exec keycloak /opt/keycloak/bin/kcadm.sh create organizations -r pulse \
  -s name="Beta Corp" \
  -s alias=beta-corp \
  -s enabled=true

# Then create matching tenant in database
INSERT INTO tenants (tenant_id, name, status) VALUES ('beta-corp', 'Beta Corp', 'ACTIVE');
```
