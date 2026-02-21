# Prompt 008 — S3 + CloudFront for React SPA

## Your Task

Create `infra/terraform/cloudfront.tf`.

The React SPA (`frontend/dist/`) is served from S3 via CloudFront. This is separate from the ALB — the SPA is static files, the API goes through the ALB.

```hcl
resource "aws_s3_bucket" "spa" {
  bucket = "${local.name_prefix}-spa-${data.aws_caller_identity.current.account_id}"
  tags   = { Name = "${local.name_prefix}-spa" }
}

resource "aws_s3_bucket_public_access_block" "spa" {
  bucket = aws_s3_bucket.spa.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# CloudFront Origin Access Control (OAC) — allows CloudFront to read from private S3
resource "aws_cloudfront_origin_access_control" "spa" {
  name                              = "${local.name_prefix}-spa-oac"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_distribution" "spa" {
  enabled             = true
  default_root_object = "index.html"
  comment             = "${local.name_prefix} SPA"

  origin {
    domain_name              = aws_s3_bucket.spa.bucket_regional_domain_name
    origin_id                = "spa-s3"
    origin_access_control_id = aws_cloudfront_origin_access_control.spa.id
  }

  default_cache_behavior {
    target_origin_id       = "spa-s3"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]

    forwarded_values {
      query_string = false
      cookies { forward = "none" }
    }

    # Short TTL for dev (easier to iterate)
    min_ttl     = 0
    default_ttl = 60
    max_ttl     = 300
  }

  # SPA routing: all 404s return index.html (React Router handles the route)
  custom_error_response {
    error_code         = 404
    response_code      = 200
    response_page_path = "/index.html"
  }

  custom_error_response {
    error_code         = 403
    response_code      = 200
    response_page_path = "/index.html"
  }

  restrictions {
    geo_restriction { restriction_type = "none" }
  }

  viewer_certificate {
    cloudfront_default_certificate = true  # Use custom cert for prod
  }

  tags = { Name = "${local.name_prefix}-cloudfront" }
}

# S3 bucket policy: allow CloudFront OAC only
resource "aws_s3_bucket_policy" "spa" {
  bucket = aws_s3_bucket.spa.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "cloudfront.amazonaws.com" }
      Action    = "s3:GetObject"
      Resource  = "${aws_s3_bucket.spa.arn}/*"
      Condition = {
        StringEquals = {
          "AWS:SourceArn" = aws_cloudfront_distribution.spa.arn
        }
      }
    }]
  })
}

output "cloudfront_url" {
  description = "CloudFront URL for the React SPA"
  value       = "https://${aws_cloudfront_distribution.spa.domain_name}"
}

output "spa_bucket_name" {
  description = "S3 bucket name for SPA deployment"
  value       = aws_s3_bucket.spa.bucket
}
```

## Acceptance Criteria

- [ ] `cloudfront.tf` exists
- [ ] S3 bucket has public access blocked (CloudFront OAC only)
- [ ] SPA 404 → index.html (React Router compatibility)
- [ ] `terraform validate` passes
- [ ] Outputs `cloudfront_url` and `spa_bucket_name` defined
