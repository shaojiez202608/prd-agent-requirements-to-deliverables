# Deployment guide

The core of this project is local (forms, prompt compiler, generator, checkers) and needs no deployment.
The optional AWS part is one CDK stack with a private S3 bucket for published deliverable bundles.

## What gets deployed

| Resource | Settings |
|---|---|
| Artifact bucket | Block Public Access (all four settings), SSE-S3, bucket policy denies non-TLS requests and TLS < 1.2, versioning, ACLs disabled (bucket owner enforced), server access logs to the log bucket, lifecycle: expire noncurrent versions, abort incomplete multipart uploads |
| Access log bucket | Block Public Access, SSE-S3 (required for a server access log destination), TLS-only policy, ACLs disabled, lifecycle expiry |

There is no compute, no public endpoint, no IAM user and no KMS key. Tags come from the config file
(`Project`, `Purpose`, and `Teardown` in the sandbox config).

## Prerequisites

- AWS credentials for a **non-production** account in your shell (short-lived role credentials recommended).
- The account and region are bootstrapped for CDK (`cdk bootstrap`, done once by an account administrator).
- Node.js (for `npx`), Python 3.12+, uv.

## Parameters (one file per environment)

`infra/config/sandbox.json` (default) and `infra/config/customer.json`:

| Key | Meaning | sandbox | customer |
|---|---|---|---|
| stack_name | CloudFormation stack name | `proto-prd-artifacts` | `prd-agent-artifacts` |
| region | Target region (`<REGION>` = take it from the environment) | us-east-1 | `<REGION>` |
| removal_policy | `destroy` or `retain` for both buckets | destroy | retain |
| noncurrent_version_expiration_days | Lifecycle for old versions | 30 | 90 |
| access_log_expiration_days | Lifecycle for access logs | 90 | 365 |
| tags | Tags applied to every resource | Project, Purpose, Teardown | Project, Purpose |

## Deploy (one command)

```bash
uv sync
cd infra
npx -y aws-cdk@2 synth  -c config=config/sandbox.json      # runs cdk-nag AwsSolutions; fails on findings
npx -y aws-cdk@2 deploy -c config=config/sandbox.json
```

The bucket name is printed as the stack output `ArtifactBucketName`.

## Use

```bash
uv run prd-agent publish out/smart-plug --dest s3://<ArtifactBucketName>/bundles --name demo-smart-plug-v1
uv run prd-agent fetch s3://<ArtifactBucketName>/bundles --name demo-smart-plug-v1 --out out/fetched
uv run prd-agent validate out/fetched
```

Publishers use their own role. Minimum permissions on the bucket (replace the placeholders):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {"Effect": "Allow", "Action": ["s3:PutObject", "s3:GetObject"],
     "Resource": "arn:aws:s3:::<ArtifactBucketName>/bundles/*"}
  ]
}
```

## Cost

Billing dimensions: S3 storage (including noncurrent versions and access logs), requests, and data transfer.
See https://aws.amazon.com/s3/pricing/ for current prices.

## Removal

See [cleanup.md](cleanup.md).
