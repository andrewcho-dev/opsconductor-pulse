# Prompt 005 — RDS PostgreSQL for Keycloak

## Context

Keycloak requires its own relational database. This is standard PostgreSQL (NOT TimescaleDB/Timescale Cloud). We use AWS RDS PostgreSQL for this.

This is the ONLY thing RDS is used for. The main application DB is Timescale Cloud (external).

## Your Task

Create `infra/terraform/rds.tf`:

```hcl
resource "aws_db_subnet_group" "keycloak" {
  name       = "${local.name_prefix}-keycloak-db-subnet-group"
  subnet_ids = aws_subnet.private[*].id
  tags       = { Name = "${local.name_prefix}-keycloak-db-subnet" }
}

resource "aws_db_instance" "keycloak" {
  identifier              = "${local.name_prefix}-keycloak-db"
  engine                  = "postgres"
  engine_version          = "16"
  instance_class          = "db.t3.micro"  # Dev sizing — upgrade for prod
  allocated_storage       = 20
  max_allocated_storage   = 100
  storage_encrypted       = true

  db_name  = "keycloak"
  username = "keycloak"
  password = random_password.keycloak_db.result

  db_subnet_group_name   = aws_db_subnet_group.keycloak.name
  vpc_security_group_ids = [aws_security_group.rds_keycloak.id]

  backup_retention_period = 1   # 1 day for dev
  skip_final_snapshot     = true  # Dev only — set false for prod

  tags = { Name = "${local.name_prefix}-keycloak-db" }
}

output "keycloak_db_endpoint" {
  description = "Keycloak RDS endpoint"
  value       = aws_db_instance.keycloak.endpoint
  sensitive   = true
}
```

## Important Notes

- `skip_final_snapshot = true` is dev-only. A comment must note this.
- `db.t3.micro` is the smallest RDS instance — fine for Keycloak in dev.
- The password comes from `random_password.keycloak_db` defined in `secrets.tf` (prompt 004). Ensure `secrets.tf` is applied before `rds.tf` or use `depends_on`.

## Acceptance Criteria

- [ ] `rds.tf` exists
- [ ] RDS instance uses standard PostgreSQL 16 (NOT timescaledb image)
- [ ] Instance is in private subnets
- [ ] Security group restricts access to ECS tasks only
- [ ] `terraform validate` passes
- [ ] Comments note: "dev only" for `skip_final_snapshot` and instance class
