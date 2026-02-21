# Prompt 011 — Deploy and Smoke Test

## Context

All Terraform files are written and validated. This prompt does the first real `terraform apply` and confirms the stack is running.

## Prerequisites Before Running This Prompt

1. You have an AWS account with programmatic access configured
2. You have a Timescale Cloud account and a connection string ready
3. You have run `terraform init` in `infra/terraform/`
4. You have created `infra/terraform/terraform.tfvars` (gitignored) with real values

## Step 1: Create the S3 backend bucket (one-time, manual)

Before first apply, create the state bucket manually:

```bash
aws s3 mb s3://opsconductor-pulse-tfstate --region us-west-2
aws s3api put-bucket-versioning \
  --bucket opsconductor-pulse-tfstate \
  --versioning-configuration Status=Enabled
```

Then uncomment the `backend "s3"` block in `main.tf` and run `terraform init` again to migrate state.

## Step 2: Plan

```bash
cd infra/terraform
terraform plan -out=tfplan 2>&1 | tee /tmp/phase45-plan.txt
```

Review the plan. Expected resource count: ~60-80 resources. If any errors, fix them before applying.

## Step 3: Apply (in stages — safest approach)

Apply in dependency order to catch errors early:

```bash
# Stage 1: Foundation
terraform apply -target=aws_vpc.main \
  -target=aws_subnet.public \
  -target=aws_subnet.private \
  -target=aws_internet_gateway.main \
  -target=aws_nat_gateway.main

# Stage 2: Security + Secrets
terraform apply -target=aws_security_group.alb \
  -target=aws_security_group.ecs_api \
  -target=aws_security_group.ecs_worker \
  -target=aws_security_group.mqtt \
  -target=aws_security_group.rds_keycloak \
  -target=aws_secretsmanager_secret.timescale_url \
  -target=aws_secretsmanager_secret_version.timescale_url

# Stage 3: ECR + RDS + CloudWatch
terraform apply -target=aws_ecr_repository.services \
  -target=aws_db_instance.keycloak \
  -target=aws_cloudwatch_log_group.ecs

# Stage 4: Build and push images (outside Terraform)
# See Step 4 below

# Stage 5: ECS + ALB + CloudFront
terraform apply
```

## Step 4: Build and Push Images to ECR

Before ECS services can start, images must be in ECR:

```bash
ECR_URL=$(terraform output -raw ecr_registry_url)
aws ecr get-login-password --region us-west-2 | \
  docker login --username AWS --password-stdin $ECR_URL

# Build and push each service
for svc in ui_iot ingest_iot evaluator_iot dispatcher delivery_worker ops_worker provision_api webhook_receiver subscription_worker; do
  svc_ecr=$(echo $svc | tr _ -)
  docker build -t $ECR_URL/pulse-dev/$svc_ecr:latest services/$svc/
  docker push $ECR_URL/pulse-dev/$svc_ecr:latest
done
```

## Step 5: Smoke Tests

```bash
ALB_URL=$(terraform output -raw alb_dns_name)

# API health
curl http://$ALB_URL/api/v2/health
# Expected: {"status":"ok","service":"pulse-ui","api_version":"v2"}

# Provision API health
curl http://$ALB_URL/provision/health
# Expected: 200

# Keycloak
curl http://$ALB_URL/auth/health/ready
# Expected: 200

# SPA
CLOUDFRONT_URL=$(terraform output -raw cloudfront_url)
curl -I $CLOUDFRONT_URL
# Expected: 200 with HTML content-type
```

## Step 6: Check ECS service status

```bash
aws ecs describe-services \
  --cluster pulse-dev-cluster \
  --services pulse-dev-ui-iot pulse-dev-ingest-iot pulse-dev-evaluator-iot \
  --query "services[].{name:serviceName,running:runningCount,desired:desiredCount,status:status}"
```

Expected: all services show `running == desired`.

## Acceptance Criteria

- [ ] `terraform apply` completes with 0 errors
- [ ] All ECS services show `runningCount == desiredCount`
- [ ] `curl http://$ALB_URL/api/v2/health` returns 200
- [ ] `curl $CLOUDFRONT_URL` returns the SPA HTML
- [ ] `curl http://$ALB_URL/auth/health/ready` returns 200 (Keycloak)
- [ ] CloudWatch log groups have entries from running services

## Gate for Phase 46

Phase 46 is production hardening:
- Multi-AZ RDS and ECS
- Auto-scaling policies
- HTTPS/ACM certificate on ALB
- WAF rules
- Backup policies
- Cost alarms
- Staging environment separation
