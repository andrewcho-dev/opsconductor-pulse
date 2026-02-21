# Prompt 006 — ECS Cluster + Task Definitions + IAM

## Your Task

Create `infra/terraform/ecs.tf` and `infra/terraform/iam.tf`.

### `iam.tf` — ECS Execution Role

All ECS tasks need an execution role to pull from ECR and write to CloudWatch. They also need a task role to read from Secrets Manager.

```hcl
# ECS task execution role (pull images, write logs)
resource "aws_iam_role" "ecs_execution" {
  name = "${local.name_prefix}-ecs-execution-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_execution" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# ECS task role (read secrets)
resource "aws_iam_role" "ecs_task" {
  name = "${local.name_prefix}-ecs-task-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "ecs_task_secrets" {
  name = "${local.name_prefix}-ecs-task-secrets"
  role = aws_iam_role.ecs_task.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = ["arn:aws:secretsmanager:${var.aws_region}:*:secret:${local.name_prefix}/*"]
    }]
  })
}
```

### `ecs.tf` — Cluster and Services

```hcl
resource "aws_ecs_cluster" "main" {
  name = "${local.name_prefix}-cluster"
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}
```

For each service, create an `aws_ecs_task_definition` and `aws_ecs_service`. Follow this pattern for every service:

**Services to define** (cross-reference with `compose/docker-compose.yml` for env vars):

| Service | Port | SG | Subnets | CPU/Mem (dev) |
|---------|------|----|---------|----------------|
| `ui_iot` | 8080 | ecs_api | private | 512/1024 |
| `provision_api` | 8080 | ecs_api | private | 256/512 |
| `ingest_iot` | none | ecs_worker | private | 256/512 |
| `evaluator_iot` | 8080 (health) | ecs_worker | private | 256/512 |
| `dispatcher` | none | ecs_worker | private | 256/512 |
| `delivery_worker` | none | ecs_worker | private | 256/512 |
| `ops_worker` | none | ecs_worker | private | 256/512 |
| `subscription_worker` | none | ecs_worker | private | 256/512 |
| `webhook_receiver` | 8080 | ecs_api | private | 256/512 |
| `mqtt` (Mosquitto) | 1883, 8883 | mqtt | public | 256/512 |
| `keycloak` | 8080 | ecs_api | private | 1024/2048 |

**Pattern for a task definition (use for all services):**

```hcl
resource "aws_ecs_task_definition" "ui_iot" {
  family                   = "${local.name_prefix}-ui-iot"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name  = "ui-iot"
    image = "${aws_ecr_repository.services["ui-iot"].repository_url}:latest"
    portMappings = [{ containerPort = 8080, protocol = "tcp" }]
    environment = [
      # Non-secret env vars only
      { name = "PG_HOST", value = "" },  # Unused — DB URL from secret
      { name = "ENVIRONMENT", value = var.environment },
    ]
    secrets = [
      { name = "DATABASE_URL", valueFrom = aws_secretsmanager_secret.timescale_url.arn },
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = "/ecs/${local.name_prefix}/ui-iot"
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = "ecs"
      }
    }
  }])
}

resource "aws_ecs_service" "ui_iot" {
  name            = "${local.name_prefix}-ui-iot"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.ui_iot.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs_api.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.ui_iot.arn  # defined in alb.tf
    container_name   = "ui-iot"
    container_port   = 8080
  }

  depends_on = [aws_lb_listener.https]
}
```

Repeat this pattern for all services. For worker services (no load balancer): omit the `load_balancer` block.

**For Keycloak specifically:** Pass the RDS endpoint and credentials as secrets:
```hcl
secrets = [
  { name = "KC_DB_URL",      valueFrom = "${aws_secretsmanager_secret.keycloak_db.arn}:username::" },
  { name = "KC_DB_PASSWORD", valueFrom = "${aws_secretsmanager_secret.keycloak_db.arn}:password::" },
]
environment = [
  { name = "KC_DB",       value = "postgres" },
  { name = "KC_DB_URL",   value = "jdbc:postgresql://${aws_db_instance.keycloak.endpoint}/keycloak" },
  { name = "KC_HOSTNAME", value = var.domain_name },
]
```

**For MQTT (Mosquitto):** Use the public image `eclipse-mosquitto:2.0`. Place in public subnet with `assign_public_ip = true` so devices can connect.

## Important: Env Var Mapping

Read `compose/docker-compose.yml` carefully. For each service, map every env var to either:
- A plaintext `environment` entry (non-sensitive: service URLs, feature flags, poll intervals)
- A `secrets` entry pointing to Secrets Manager (sensitive: DB URLs, passwords, tokens)

The DATABASE_URL for all Python services points to the Timescale Cloud secret. For Keycloak it points to RDS.

## Acceptance Criteria

- [ ] `iam.tf` exists with execution role + task role + secrets policy
- [ ] `ecs.tf` exists with cluster + task definitions + services for all 11 services
- [ ] All sensitive env vars use `secrets` (Secrets Manager ARN), not plaintext `environment`
- [ ] Worker services have no load_balancer block
- [ ] `terraform validate` passes
