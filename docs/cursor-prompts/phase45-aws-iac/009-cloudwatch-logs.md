# Prompt 009 — CloudWatch Log Groups

## Your Task

Create `infra/terraform/cloudwatch.tf`.

Every ECS task writes logs to CloudWatch. The log group must exist before the task starts.

```hcl
locals {
  log_services = [
    "ui-iot",
    "ingest-iot",
    "evaluator-iot",
    "dispatcher",
    "delivery-worker",
    "ops-worker",
    "provision-api",
    "webhook-receiver",
    "subscription-worker",
    "mqtt",
    "keycloak",
  ]
}

resource "aws_cloudwatch_log_group" "ecs" {
  for_each          = toset(local.log_services)
  name              = "/ecs/${local.name_prefix}/${each.key}"
  retention_in_days = 7  # Dev: 7 days. Increase for prod.
  tags              = { Name = "${local.name_prefix}-logs-${each.key}" }
}
```

## Acceptance Criteria

- [ ] `cloudwatch.tf` exists with log groups for all 11 services
- [ ] Retention set to 7 days with a comment noting prod should be higher
- [ ] Log group names match the `awslogs-group` values in `ecs.tf` task definitions
- [ ] `terraform validate` passes
