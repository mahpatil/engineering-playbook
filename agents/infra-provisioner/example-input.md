# Example Input: Payments API — Production AWS Environment

## Request

Provision a production-tier AWS environment for the `payments-api` service.

## Parameters

| Field | Value |
|-------|-------|
| `app_name` | `payments-api` |
| `cloud_target` | `aws` |
| `environment` | `prod` |
| `dr_tier` | `1` |
| `region` | `us-east-1` |
| `secondary_region` | `us-west-2` |
| `team` | `payments-platform` |
| `cost_centre` | `CC-PAY-001` |

## Context

The `payments-api` is a Spring Boot service handling card authorisation and settlement flows. It must meet PCI-DSS scope requirements, so:

- All data at rest must be encrypted with customer-managed KMS keys.
- Network access to the service must be restricted to internal ingress only — no public IPs on compute.
- The RDS PostgreSQL database must sit in a private subnet with no internet-facing endpoints.
- DR tier 1 means: active-passive across `us-east-1` and `us-west-2`, RDS Multi-AZ, hourly automated snapshots, and Route 53 health-check failover.
- An Application Load Balancer (HTTPS only, HTTP→HTTPS redirect) in the public subnet terminates TLS using an ACM certificate.
- ECS Fargate tasks run in the private subnet; the task execution role may only read from SSM Parameter Store paths under `/payments-api/prod/`.
- Security groups: ALB SG allows 443 inbound from `0.0.0.0/0`; ECS task SG allows 8080 inbound from ALB SG only; RDS SG allows 5432 inbound from ECS task SG only.

## Expected Output

- `infra/payments-api/prod/main.tf` — VPC data sources, ALB, ECS cluster, RDS, KMS key, IAM role, security groups.
- `infra/payments-api/prod/variables.tf` — All variables typed and described; no hard-coded values.
- `infra/payments-api/prod/outputs.tf` — ALB DNS name, ECS cluster ARN, RDS endpoint (sensitive), KMS key ARN.
- `infra/payments-api/prod/backend.tf` — S3 backend in `acme-tfstate-aws-prod` bucket with DynamoDB locking.
- `infra/payments-api/prod/terraform.tfvars.example` — Placeholder values only, no real data.
- Provisioning Checklist.

## What This Should NOT Contain

- Real AWS account IDs or ARNs.
- Real KMS key IDs.
- Credentials, passwords, or tokens in any form.
- `0.0.0.0/0` ingress on the ECS task or RDS security groups.
