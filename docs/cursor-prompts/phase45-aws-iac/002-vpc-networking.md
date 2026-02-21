# Prompt 002 — VPC, Subnets, Security Groups

## Your Task

Create `infra/terraform/vpc.tf` and `infra/terraform/security_groups.tf`.

### `vpc.tf` — VPC and Subnets

```hcl
# VPC
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags = { Name = "${local.name_prefix}-vpc" }
}

# Internet Gateway
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  tags = { Name = "${local.name_prefix}-igw" }
}

# Public subnets (2 AZs) — ALB, NAT gateways
resource "aws_subnet" "public" {
  count                   = 2
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, count.index)
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true
  tags = { Name = "${local.name_prefix}-public-${count.index}" }
}

# Private subnets (2 AZs) — ECS tasks, RDS
resource "aws_subnet" "private" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index + 10)
  availability_zone = data.aws_availability_zones.available.names[count.index]
  tags = { Name = "${local.name_prefix}-private-${count.index}" }
}

data "aws_availability_zones" "available" { state = "available" }

# NAT Gateway (single, for dev — use one per AZ for prod)
resource "aws_eip" "nat" {
  domain = "vpc"
  tags   = { Name = "${local.name_prefix}-nat-eip" }
}

resource "aws_nat_gateway" "main" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public[0].id
  tags          = { Name = "${local.name_prefix}-nat" }
  depends_on    = [aws_internet_gateway.main]
}

# Route tables
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
  tags = { Name = "${local.name_prefix}-rt-public" }
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main.id
  }
  tags = { Name = "${local.name_prefix}-rt-private" }
}

resource "aws_route_table_association" "public" {
  count          = 2
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "private" {
  count          = 2
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}
```

### `security_groups.tf` — Security Groups

Create security groups for:

1. **ALB** — accepts 80/443 from internet
2. **ECS tasks (API/UI)** — accepts traffic from ALB only
3. **ECS tasks (internal workers)** — no inbound, outbound to DB + other services
4. **MQTT** — accepts 1883/8883 from internet (devices connect here)
5. **RDS (Keycloak DB)** — accepts 5432 from ECS tasks only
6. **Keycloak** — accepts 8080 from ALB only

```hcl
# ALB
resource "aws_security_group" "alb" {
  name   = "${local.name_prefix}-alb"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = { Name = "${local.name_prefix}-sg-alb" }
}

# ECS services (HTTP-facing)
resource "aws_security_group" "ecs_api" {
  name   = "${local.name_prefix}-ecs-api"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port       = 8080
    to_port         = 8080
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = { Name = "${local.name_prefix}-sg-ecs-api" }
}

# ECS workers (no inbound)
resource "aws_security_group" "ecs_worker" {
  name   = "${local.name_prefix}-ecs-worker"
  vpc_id = aws_vpc.main.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = { Name = "${local.name_prefix}-sg-ecs-worker" }
}

# MQTT broker
resource "aws_security_group" "mqtt" {
  name   = "${local.name_prefix}-mqtt"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port   = 1883
    to_port     = 1883
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port   = 8883
    to_port     = 8883
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = { Name = "${local.name_prefix}-sg-mqtt" }
}

# Keycloak RDS
resource "aws_security_group" "rds_keycloak" {
  name   = "${local.name_prefix}-rds-keycloak"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_api.id]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = { Name = "${local.name_prefix}-sg-rds-keycloak" }
}
```

## Acceptance Criteria

- [ ] `vpc.tf` and `security_groups.tf` exist
- [ ] `terraform validate` passes
- [ ] `terraform plan` shows VPC, subnets, IGW, NAT, route tables, and security groups with no errors
- [ ] No actual AWS resources created yet (`terraform apply` not run until prompt 011)
