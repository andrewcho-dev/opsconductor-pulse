# Prompt 004 — AWS Secrets Manager

## Your Task

Create `infra/terraform/secrets.tf`. All credentials are stored in Secrets Manager — never in ECS task definition environment variables as plaintext.

```hcl
# Timescale Cloud connection string
resource "aws_secretsmanager_secret" "timescale_url" {
  name                    = "${local.name_prefix}/timescale-url"
  description             = "Timescale Cloud PostgreSQL connection string"
  recovery_window_in_days = 0  # Immediate deletion (dev only; use 7+ for prod)
}

resource "aws_secretsmanager_secret_version" "timescale_url" {
  secret_id     = aws_secretsmanager_secret.timescale_url.id
  secret_string = var.timescale_connection_string
}

# Keycloak admin credentials
resource "aws_secretsmanager_secret" "keycloak_admin" {
  name                    = "${local.name_prefix}/keycloak-admin"
  description             = "Keycloak admin credentials"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "keycloak_admin" {
  secret_id = aws_secretsmanager_secret.keycloak_admin.id
  secret_string = jsonencode({
    username = "admin"
    password = var.keycloak_admin_password
  })
}

# Keycloak DB password (generated)
resource "random_password" "keycloak_db" {
  length  = 32
  special = false
}

resource "aws_secretsmanager_secret" "keycloak_db" {
  name                    = "${local.name_prefix}/keycloak-db"
  description             = "Keycloak RDS PostgreSQL credentials"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "keycloak_db" {
  secret_id = aws_secretsmanager_secret.keycloak_db.id
  secret_string = jsonencode({
    username = "keycloak"
    password = random_password.keycloak_db.result
  })
}

# MQTT credentials (if required by ingest service)
resource "aws_secretsmanager_secret" "mqtt_creds" {
  name                    = "${local.name_prefix}/mqtt-creds"
  description             = "MQTT broker credentials"
  recovery_window_in_days = 0
}
```

Add `random` provider to `main.tf` required_providers:
```hcl
random = {
  source  = "hashicorp/random"
  version = "~> 3.0"
}
```

## Important

Secrets Manager secrets are created empty by Terraform except for the ones with known values. The MQTT secret needs a value — check `compose/docker-compose.yml` for the MQTT password env var name and add a corresponding `variable` in `variables.tf` and populate the secret version.

## Acceptance Criteria

- [ ] `secrets.tf` exists with secrets for: timescale URL, keycloak admin, keycloak DB password, MQTT creds
- [ ] No plaintext credentials in any `.tf` file (all from `var.*` or `random_password`)
- [ ] `terraform validate` passes
- [ ] `random` provider added to `main.tf`
