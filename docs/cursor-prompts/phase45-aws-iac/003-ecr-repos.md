# Prompt 003 — ECR Repos for All Service Images

## Your Task

Create `infra/terraform/ecr.tf` with one ECR repository per service image.

Services to create repos for (derived from `compose/docker-compose.yml`):
- `ui_iot` (the main API + SPA server)
- `ingest_iot` (MQTT ingest service)
- `evaluator_iot` (threshold evaluator)
- `dispatcher` (alert dispatcher)
- `delivery_worker` (delivery pipeline worker)
- `ops_worker` (health monitor + metrics collector — Phase 43)
- `provision_api` (device provisioning API)
- `webhook_receiver` (webhook receiver service)
- `subscription_worker` (subscription management worker)

Do NOT create a repo for: `postgres` (Timescale Cloud), `mqtt` (Mosquitto uses public image), `keycloak` (uses public image), `caddy` (uses public image), `seed`/`simulator`/`device_sim` (not deployed to AWS).

```hcl
locals {
  ecr_services = [
    "ui-iot",
    "ingest-iot",
    "evaluator-iot",
    "dispatcher",
    "delivery-worker",
    "ops-worker",
    "provision-api",
    "webhook-receiver",
    "subscription-worker",
  ]
}

resource "aws_ecr_repository" "services" {
  for_each = toset(local.ecr_services)

  name                 = "${local.name_prefix}/${each.key}"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = { Name = "${local.name_prefix}-ecr-${each.key}" }
}

# Lifecycle policy: keep last 10 images per repo (saves storage costs)
resource "aws_ecr_lifecycle_policy" "services" {
  for_each   = aws_ecr_repository.services
  repository = each.value.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 10 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 10
      }
      action = { type = "expire" }
    }]
  })
}

output "ecr_registry_url" {
  description = "ECR registry URL for pushing images"
  value       = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.aws_region}.amazonaws.com"
}

data "aws_caller_identity" "current" {}
```

## Acceptance Criteria

- [ ] `ecr.tf` exists with repos for all 9 services
- [ ] Each repo has a lifecycle policy (keep last 10)
- [ ] `terraform validate` passes
- [ ] `terraform plan` shows 9 ECR repos + 9 lifecycle policies
