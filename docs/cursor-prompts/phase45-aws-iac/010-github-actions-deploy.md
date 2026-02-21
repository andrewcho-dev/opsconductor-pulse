# Prompt 010 — GitHub Actions: Build + Push to ECR + Deploy to ECS

## Your Task

Create `.github/workflows/deploy.yml`. This is a new workflow — do NOT modify `test.yml`.

The deploy workflow:
1. Triggers on push to `main` branch (after tests pass)
2. Builds each Docker image
3. Pushes to ECR
4. Updates the ECS service to use the new image

```yaml
name: Deploy to AWS

on:
  push:
    branches: [main]
  workflow_dispatch:  # Allow manual trigger

jobs:
  deploy:
    name: Build, Push, Deploy
    runs-on: ubuntu-latest
    environment: dev  # GitHub Environment with secrets

    permissions:
      id-token: write  # Required for OIDC auth to AWS
      contents: read

    env:
      AWS_REGION: us-west-2
      ECR_REGISTRY: ${{ secrets.ECR_REGISTRY_URL }}
      ENVIRONMENT: dev

    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials (OIDC)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_DEPLOY_ROLE_ARN }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build and push service images
        run: |
          IMAGE_TAG=${{ github.sha }}

          # Build and push each service
          services=(
            "ui-iot:services/ui_iot"
            "ingest-iot:services/ingest_iot"
            "evaluator-iot:services/evaluator_iot"
            "dispatcher:services/dispatcher"
            "delivery-worker:services/delivery_worker"
            "ops-worker:services/ops_worker"
            "provision-api:services/provision_api"
            "webhook-receiver:services/webhook_receiver"
            "subscription-worker:services/subscription_worker"
          )

          for svc in "${services[@]}"; do
            name="${svc%%:*}"
            path="${svc##*:}"
            full_image="$ECR_REGISTRY/pulse-dev/$name"

            docker build -t "$full_image:$IMAGE_TAG" -t "$full_image:latest" "$path"
            docker push "$full_image:$IMAGE_TAG"
            docker push "$full_image:latest"
          done

      - name: Deploy to ECS (force new deployment)
        run: |
          # Force new deployment for each service — ECS will pull the new :latest image
          cluster="pulse-dev-cluster"
          services=(
            "pulse-dev-ui-iot"
            "pulse-dev-ingest-iot"
            "pulse-dev-evaluator-iot"
            "pulse-dev-dispatcher"
            "pulse-dev-delivery-worker"
            "pulse-dev-ops-worker"
            "pulse-dev-provision-api"
            "pulse-dev-webhook-receiver"
            "pulse-dev-subscription-worker"
          )

          for svc in "${services[@]}"; do
            aws ecs update-service \
              --cluster "$cluster" \
              --service "$svc" \
              --force-new-deployment \
              --region ${{ env.AWS_REGION }}
          done

      - name: Build and deploy frontend to S3/CloudFront
        run: |
          cd frontend
          npm ci
          npm run build

          # Sync to S3
          aws s3 sync dist/ s3://${{ secrets.SPA_BUCKET_NAME }}/ \
            --delete \
            --cache-control "public, max-age=31536000, immutable" \
            --exclude "index.html"

          # index.html with no-cache
          aws s3 cp dist/index.html s3://${{ secrets.SPA_BUCKET_NAME }}/index.html \
            --cache-control "no-cache, no-store, must-revalidate"

          # Invalidate CloudFront
          aws cloudfront create-invalidation \
            --distribution-id ${{ secrets.CLOUDFRONT_DISTRIBUTION_ID }} \
            --paths "/*"
```

## GitHub Secrets Required

Add these to the GitHub repo's `dev` environment secrets:
- `AWS_DEPLOY_ROLE_ARN` — IAM role ARN for OIDC deploy (create this in AWS)
- `ECR_REGISTRY_URL` — from `terraform output ecr_registry_url`
- `SPA_BUCKET_NAME` — from `terraform output spa_bucket_name`
- `CLOUDFRONT_DISTRIBUTION_ID` — from `terraform output` after apply

## IAM Role for GitHub Actions OIDC

Add to `iam.tf`:

```hcl
# GitHub Actions OIDC provider
resource "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
}

resource "aws_iam_role" "github_deploy" {
  name = "${local.name_prefix}-github-deploy"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Federated = aws_iam_openid_connect_provider.github.arn }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringLike = {
          "token.actions.githubusercontent.com:sub" = "repo:YOUR_ORG/YOUR_REPO:*"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "github_deploy" {
  name = "${local.name_prefix}-github-deploy-policy"
  role = aws_iam_role.github_deploy.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["ecr:GetAuthorizationToken", "ecr:BatchCheckLayerAvailability",
                    "ecr:PutImage", "ecr:InitiateLayerUpload", "ecr:UploadLayerPart",
                    "ecr:CompleteLayerUpload"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["ecs:UpdateService", "ecs:DescribeServices"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["s3:PutObject", "s3:DeleteObject", "s3:ListBucket"]
        Resource = ["${aws_s3_bucket.spa.arn}", "${aws_s3_bucket.spa.arn}/*"]
      },
      {
        Effect   = "Allow"
        Action   = ["cloudfront:CreateInvalidation"]
        Resource = "*"
      }
    ]
  })
}
```

Replace `YOUR_ORG/YOUR_REPO` with the actual GitHub org/repo name.

## Acceptance Criteria

- [ ] `.github/workflows/deploy.yml` exists
- [ ] GitHub OIDC IAM role added to `iam.tf`
- [ ] `terraform validate` passes
- [ ] Workflow triggers on push to `main`
- [ ] Frontend build + S3 deploy + CloudFront invalidation in same job
