# Prompt 001 — Terraform Project Structure + Providers

## Your Task

Create the `infra/terraform/` directory and the foundational files. Do NOT write any actual resources yet — only the scaffolding.

### Step 1: Create `infra/terraform/main.tf`

```hcl
terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Remote state — use S3 backend (configure before first apply)
  # Uncomment and fill in after creating the S3 bucket manually:
  # backend "s3" {
  #   bucket = "opsconductor-pulse-tfstate"
  #   key    = "dev/terraform.tfstate"
  #   region = "us-west-2"
  #   encrypt = true
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "pulse"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

locals {
  name_prefix = "pulse-${var.environment}"
}
```

### Step 2: Create `infra/terraform/variables.tf`

Include these variables:

```hcl
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.0.0.0/16"
}

variable "timescale_connection_string" {
  description = "Timescale Cloud connection string (sensitive)"
  type        = string
  sensitive   = true
}

variable "keycloak_admin_password" {
  description = "Keycloak admin password (sensitive)"
  type        = string
  sensitive   = true
}

variable "domain_name" {
  description = "Primary domain name for the application (e.g. pulse.opsconductor.com)"
  type        = string
  default     = ""
}
```

### Step 3: Create `infra/terraform/outputs.tf`

```hcl
output "alb_dns_name" {
  description = "ALB DNS name — point your domain here"
  value       = "defined in alb.tf"
}

output "cloudfront_url" {
  description = "CloudFront URL for the React SPA"
  value       = "defined in cloudfront.tf"
}

output "ecr_registry_url" {
  description = "ECR registry URL for pushing images"
  value       = "defined in ecr.tf"
}
```

(These will be replaced with actual references in later prompts.)

### Step 4: Create `infra/terraform/terraform.tfvars.example`

```hcl
aws_region                  = "us-west-2"
environment                 = "dev"
timescale_connection_string = "postgres://user:pass@host.timescaledb.io:5432/tsdb?sslmode=require"
keycloak_admin_password     = "CHANGE_ME"
domain_name                 = "pulse.yourdomain.com"
```

### Step 5: Add `infra/terraform/` to `.gitignore`

Add these lines to the root `.gitignore`:
```
infra/terraform/.terraform/
infra/terraform/terraform.tfstate
infra/terraform/terraform.tfstate.backup
infra/terraform/terraform.tfvars
infra/terraform/.terraform.lock.hcl
```

Note: `terraform.tfvars` (real secrets) is gitignored. `terraform.tfvars.example` (no secrets) IS committed.

## Acceptance Criteria

- [ ] `infra/terraform/` directory exists with `main.tf`, `variables.tf`, `outputs.tf`, `terraform.tfvars.example`
- [ ] Root `.gitignore` updated to exclude tfstate and tfvars
- [ ] `terraform.tfvars.example` committed (no real secrets)
- [ ] `cd infra/terraform && terraform init` succeeds (downloads AWS provider)
- [ ] `terraform validate` passes
