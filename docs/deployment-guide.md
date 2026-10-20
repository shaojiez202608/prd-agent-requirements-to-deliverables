# Deployment guide

The core of this project is local (forms, prompt compiler, generator, checkers) and needs no deployment.
The optional AWS part is one CDK stack with a private S3 bucket for published deliverable bundles.

## What gets deployed

| Resource | Settings |
|---|---|
| Artifact bucket | Block Public Access (all four settings), SSE-S3, bucket policy denies non-TLS requests, TLS < 1.2 and every principal outside the account (optionally also writes by principals not in `writer_principal_arns`), versioning, ACLs disabled (bucket owner enforced), server access logs to the log bucket, lifecycle: expire noncurrent versions, abort incomplete multipart uploads |
| Access log bucket | Block Public Access, SSE-S3 (required for a server access log destination), TLS-only policy, ACLs disabled, lifecycle expiry |

There is no compute, no public endpoint, no IAM user and no KMS key. Tags come from the config file
(`Project`, `Purpose`, and `Teardown` in the sandbox config).

## Prerequisites and commands

Prerequisites, the deploy commands and verification are in [README.md](../README.md#deploy); they are kept in one
place on purpose. This page describes the parameters and the deployed resources.

## Parameters (one file per environment)

Templates `infra/config/sandbox.example.json` and `infra/config/customer.example.json` are committed. `make init`
copies them to `infra/config/sandbox.json` and `customer.json` (ignored by git), which you may edit.
`infra/prd_infra/config.py` validates every value and makes `cdk synth` fail with a list of all problems.

| Key | Meaning | Rule | sandbox | customer |
|---|---|---|---|---|
| stack_name | CloudFormation stack name | `^[A-Za-z][A-Za-z0-9-]{0,127}$` | `proto-prd-artifacts` | `prd-agent-artifacts` |
| region | Target region | region code, or `<REGION>` = take it from `AWS_REGION` | us-east-1 | `<REGION>` |
| removal_policy | `destroy` or `retain` for both buckets | `destroy` only for stacks named `proto-*` and with a `Teardown` tag | destroy | retain |
| noncurrent_version_expiration_days | Lifecycle for old versions | 1 to 3650; at least 30 with `retain` | 30 | 90 |
| access_log_expiration_days | Lifecycle for access logs | 1 to 3650 | 90 | 365 |
| tags | Tags applied to every resource | must include `Project`; no `aws:` keys | Project, Purpose, Teardown | Project, Purpose |

Account IDs are not allowed in these files (a 12-digit number fails validation). The account comes from your
credentials. Optional context `writer_principal_arns=<ARN>[,<ARN>...]` (role or user ARNs) adds a bucket policy
statement that denies `s3:PutObject` to every other principal; pass it with `make deploy WRITERS=...`.

The bucket name is printed as the stack output `ArtifactBucketName`.

Publishers use their own role. Minimum permissions on the bucket (replace the placeholders):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {"Effect": "Allow", "Action": ["s3:PutObject", "s3:GetObject"],
     "Resource": "arn:aws:s3:::<ARTIFACT_BUCKET_NAME>/bundles/*"}
  ]
}
```

## Cost

Billing dimensions: S3 storage (including noncurrent versions and access logs), requests, and data transfer.
See https://aws.amazon.com/s3/pricing/ for current prices. No free tier is assumed.

## Removal

See [README.md](../README.md#cleanup) and [cleanup.md](cleanup.md).
