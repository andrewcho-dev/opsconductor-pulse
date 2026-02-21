# Phase 45: AWS Infrastructure as Code (Terraform)

## DB Hosting Decision: Timescale Cloud

Timescale Cloud is the confirmed choice. It is a fully managed TimescaleDB service, fully compatible with the existing hypertables, compression policies, and continuous aggregates. No migration required. The Terraform code connects to Timescale Cloud as an external service via a connection string stored in AWS Secrets Manager.

## Architecture: What Goes Where

| Component | AWS Service | Notes |
|-----------|-------------|-------|
| All Python services | ECS Fargate | ui_iot, ingest_iot, evaluator_iot, dispatcher, delivery_worker, ops_worker, provision_api, webhook_receiver, subscription_worker |
| React SPA | S3 + CloudFront | Static files, versioned deploys |
| MQTT broker | ECS Fargate (Mosquitto) | Single task; clustering deferred |
| Keycloak | ECS Fargate + RDS PostgreSQL (standard) | Keycloak needs its own DB — use standard RDS PostgreSQL (NOT Timescale) |
| Main application DB | Timescale Cloud (external) | Connection string injected via Secrets Manager |
| HTTP routing | ALB (Application Load Balancer) | Routes to ECS services by path prefix |
| Secrets | AWS Secrets Manager | DB URLs, Keycloak credentials, MQTT creds |
| Logs | CloudWatch Logs | All ECS tasks log to CloudWatch |
| Container registry | ECR | One repo per service |

## Scope: Minimal Landing Zone

This phase produces a **dev environment** only. The goal is: one `terraform apply` that brings up the full stack in AWS. Production hardening (multi-AZ, auto-scaling, backup policies, WAF) is Phase 46.

**In scope:**
- VPC with public + private subnets (2 AZs)
- ECS cluster + task definitions for all services
- ALB with listener rules
- RDS PostgreSQL (standard) for Keycloak only
- Timescale Cloud connection (external — no Terraform resource, just a secret)
- S3 + CloudFront for SPA
- ECR repos for all service images
- Secrets Manager for all credentials
- CloudWatch log groups
- Security groups (least-privilege)
- GitHub Actions CI deploy pipeline update

**Out of scope (Phase 46):**
- Multi-AZ RDS, read replicas
- ECS auto-scaling
- WAF, Shield
- Backup policies
- Cost alarms
- Staging/prod environment separation

## Keycloak on ECS: Important Constraints

Keycloak on ECS is non-trivial. Key constraints:
- Keycloak requires its own relational DB (we use standard RDS PostgreSQL for this — not Timescale)
- Keycloak session management: for a single-task deployment (dev), this is fine
- Keycloak admin password and DB credentials must be in Secrets Manager, not env vars in task definition

## Execution Order

| Prompt | Description | Priority |
|--------|-------------|----------|
| 001 | Terraform project structure + providers | HIGH |
| 002 | VPC, subnets, security groups | HIGH |
| 003 | ECR repos for all service images | HIGH |
| 004 | Secrets Manager — all credentials | HIGH |
| 005 | RDS PostgreSQL for Keycloak | HIGH |
| 006 | ECS cluster + task definitions (all services) | CRITICAL |
| 007 | ALB + listener rules | HIGH |
| 008 | S3 + CloudFront for SPA | HIGH |
| 009 | CloudWatch log groups | MEDIUM |
| 010 | GitHub Actions: build + push to ECR + ECS deploy | HIGH |
| 011 | End-to-end deploy smoke test | CRITICAL |

## Key Files

- `compose/docker-compose.yml` — source of truth for service definitions (replicate env vars from here)
- `services/*/Dockerfile` — one per service (ECR will host built images)
- `.github/workflows/test.yml` — extend with deploy job
- New directory: `infra/terraform/` — all Terraform code lives here

## Terraform File Layout

```
infra/
└── terraform/
    ├── main.tf           ← provider, backend, locals
    ├── variables.tf      ← all input variables
    ├── outputs.tf        ← ALB URL, CloudFront URL, ECR URLs
    ├── vpc.tf            ← VPC, subnets, IGW, NAT, route tables
    ├── security_groups.tf
    ├── ecr.tf            ← one aws_ecr_repository per service
    ├── secrets.tf        ← aws_secretsmanager_secret for each credential
    ├── rds.tf            ← RDS PostgreSQL for Keycloak only
    ├── ecs.tf            ← cluster, task definitions, services
    ├── alb.tf            ← ALB, target groups, listener rules
    ├── cloudfront.tf     ← S3 bucket + CloudFront distribution
    ├── cloudwatch.tf     ← log groups
    └── iam.tf            ← ECS task execution role, task roles
```
