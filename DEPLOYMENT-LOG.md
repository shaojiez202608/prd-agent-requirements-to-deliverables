# Deployment log

Account: `<ACCOUNT_ID>` (sandbox, not recorded). Region: us-east-1 (from the environment; S3 is available there).

## Run 1 (2026-10-20)

| Item | Value |
|---|---|
| Stack | `proto-prd-artifacts` (config `infra/config/sandbox.json`) |
| Tool | `npx -y aws-cdk@2`, aws-cdk-lib 2.273.0, cdk-nag 2.38.2 |
| Synth with cdk-nag | 0 AwsSolutions errors and 0 warnings. The NagReport lists S1, S2, S5 and S10 as Compliant for both buckets and S10 as Compliant for both bucket policies |
| Deploy start / end (UTC) | 11:19:46 / 11:21:24, deploy time 45 s |
| Bootstrap | Existing `CDKToolkit` stack used as is (not changed) |

### Resources created

| Logical ID | Type | Notes |
|---|---|---|
| ArtifactBucket | AWS::S3::Bucket | name `proto-prd-artifacts-artifactbucket…` (generated) |
| ArtifactBucketPolicy | AWS::S3::BucketPolicy | Denies non-TLS and TLS < 1.2 |
| AccessLogBucket | AWS::S3::Bucket | name `proto-prd-artifacts-accesslogbucket…` (generated) |
| AccessLogBucketPolicy | AWS::S3::BucketPolicy | Denies non-TLS and TLS < 1.2; allows the S3 logging service principal to write `artifact-bucket/*`, limited to the source bucket ARN and the source account |
| CDKMetadata | AWS::CDK::Metadata | - |

No Lambda function, IAM role, IAM user, KMS key, log group, ECR repository, API or AgentCore resource was created.

### Verification steps and results

| # | Step | Result |
|---|---|---|
| 1 | `get-public-access-block` on both buckets | All four settings `true` |
| 2 | `get-bucket-encryption` | `AES256` (SSE-S3) on both |
| 3 | `get-bucket-versioning` | Artifact bucket `Enabled`; log bucket not versioned (as designed) |
| 4 | `get-bucket-ownership-controls` | `BucketOwnerEnforced` on both (ACLs disabled) |
| 5 | `get-bucket-logging` on the artifact bucket | Target prefix `artifact-bucket/` |
| 6 | `get-bucket-tagging` | `Project=prd-agent`, `Purpose=prototype`, `Teardown=after-test` on both |
| 7 | `prd-agent publish examples/smart-plug --dest s3://<bucket>/bundles --name demo-smart-plug-v1` | 13 files published (12 deliverable files and PROGRESS.md), plus MANIFEST.json: 14 objects |
| 8 | `head-object` on a published file | `ServerSideEncryption: AES256` |
| 9 | `prd-agent fetch …` then `prd-agent validate` and `check-progress` on the fetched copy | All checksums verified; Consistency check PASS; Progress log PASS |
| 10 | The same `list-objects-v2` call over plain HTTP (`--endpoint-url http://…`) | `AccessDenied … with an explicit deny in a resource-based policy` (TLS-only policy works) |
| 11 | Unauthenticated HTTPS GET of a published object | HTTP 403 |

### Destroy

| Step | Command | Result |
|---|---|---|
| 1 | `uv run python scripts/empty_stack_buckets.py proto-prd-artifacts --region us-east-1` (dry run, then `--yes`) | Artifact bucket: 14 object versions deleted. Log bucket: 0 (no logs delivered yet) |
| 1a | Prefix guard: the same script with a stack name without `proto-prd-` | Refused, exit 3 |
| 2 | `npx -y aws-cdk@2 destroy -c config=config/sandbox.json --force` (11:23:26 UTC) | `proto-prd-artifacts: destroyed` on first attempt |

### Residue check (11:25 UTC, `scripts/residue_check.sh proto-prd- us-east-1`)

| Category | Count |
|---|---|
| CloudFormation stacks `proto-prd-*` not DELETE_COMPLETE | 0 |
| S3 buckets `proto-prd-*` (head-bucket on both names: 404) | 0 |
| Resources tagged `Project=prd-agent` | 0 |
| Resources tagged `Project=prd-agent` + `Teardown=after-test` | 0 |
| Log groups `/aws/lambda/proto-prd-*` | 0 |
| Lambda functions | 0 |
| IAM roles / customer policies | 0 / 0 |
| ECR repositories | 0 |
| API Gateway REST / HTTP APIs | 0 / 0 |
| KMS aliases (no key was created, so no key in pending deletion) | 0 |
| AgentCore runtimes | 0 |

Result: **cleaned up, no residue**. Only resources created by this project were touched. The synth/deploy output
directory was written outside the repository and is not committed.
